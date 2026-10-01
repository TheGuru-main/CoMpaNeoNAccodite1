import os
import json
import asyncio

# ACCD-TORCH-GUARD: torch is optional at import time.
# Real inference requires torch; everything else works without it.
try:
    import torch
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    F = None
    TORCH_AVAILABLE = False
    import warnings
    warnings.warn(
        "torch not installed — model inference is disabled. "
        "Install torch on the runtime to enable generation.",
        RuntimeWarning, stacklevel=2,
    )

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from database import engine, SessionLocal, Base
from db_models import User, Workspace, Message, APIKey
from ai_model import MiniCompanionAI
from auth import get_current_user, hash_password, verify_password, create_access_token, validate_phone, compute_user_cell, get_db
from api_auth import verify_api_key, rate_limiter
from tokenizer import tokenize, normalize_lang, grid_dims, supported_languages
from memory_grid import MemoryGrid
from grid_crawler import crawl as grid_crawl
from web_crawler import WebCrawler
from data_mixer import DataMixer
from prompts_manager import build_prompt
from intent_analyzer import detect_domain
from external import fetch_dictionary, fetch_news, fetch_books, fetch_elibrary, fetch_wikipedia
from symbols import recognize_symbols
from code_languages import CODE_TERMS
from search_cache import SearchCache
from memory_cache import MemoryCache
from background_training import start_background_training 
from rules import enforce_rules
# BUBBLE-REMOVED: module not present in Accodite fork
from word_understanding import WordUnderstanding
from summary import generate_summary as generate_ai_summary
from follow_up import generate_follow_ups
from message import send_message, get_conversations, get_messages_between, DirectMessage

# ACCD-INTEGRATION
from integration import (
    run_job as _run_job,
    bootstrap as accd_bootstrap,
    handle_message as accd_handle_message,
    verify_and_frame as accd_verify_and_frame,
)

app = FastAPI(title="CoMpaNeoN AI", version="1.0.0")

# WEIGHTS-RELAY
try:
    from weights_relay import router as _weights_router
    app.include_router(_weights_router)
    print("[ACCD] weights relay mounted at /weights/*")
except Exception as _e:
    print(f"[ACCD] weights relay not mounted: {_e}")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

device = (torch.device("cuda" if torch.cuda.is_available() else "cpu") if TORCH_AVAILABLE else "cpu")

# Global components
model: Optional[MiniCompanionAI] = None
tokenizer_vocab: Optional[Dict[str, int]] = None
reverse_vocab: Optional[Dict[int, str]] = None

memory = MemoryGrid()
mixer = DataMixer()
try:
    web_crawler = WebCrawler(memory, data_mixer=mixer)
except TypeError:
    # older signature; still works without mixer
    web_crawler = WebCrawler(memory)
search_cache = SearchCache(ttl_seconds=300)
memory_cache = MemoryCache()
word_understanding = WordUnderstanding(memory)

# Load model if exists
def load_model_if_exists():
    global model, tokenizer_vocab, reverse_vocab
    if os.path.exists('tokenizer_vocab.json'):
        with open('tokenizer_vocab.json', 'r') as f:
            data = json.load(f)
            tokenizer_vocab = data['vocab']
            reverse_vocab = {int(k): v for k, v in data['reverse'].items()}
    else:
        tokenizer_vocab = {"<pad>":0, "<unk>":1, "<start>":2, "<end>":3}
        reverse_vocab = {0:"<pad>",1:"<unk>",2:"<start>",3:"<end>"}
    if os.path.exists('companion_model.pth') and TORCH_AVAILABLE:
        model = MiniCompanionAI(len(tokenizer_vocab))
        model.load_state_dict(torch.load('companion_model.pth', map_location=device))
        model.to(device)
        model.eval()
    else:
        model = None

def reload_model_if_exists():
    """Reload the model from disk. Called by the weights relay."""
    global model, tokenizer_vocab, reverse_vocab
    try:
        load_model_if_exists()
        return {"ok": True, "model": type(model).__name__ if model else None}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


load_model_if_exists()

# ACCD-INTEGRATION: build pipeline singletons (idempotent)
try:
    accd_bootstrap(root=os.path.dirname(os.path.abspath(__file__)) + "/..")
except Exception as _accd_boot_err:
    print(f"[ACCD] bootstrap error: {type(_accd_boot_err).__name__}: {_accd_boot_err}")

# Helpers
def encode_text(text: str, lang: str = "en") -> List[int]:
    tokens = tokenize(text, lang)
    ids = [tokenizer_vocab.get("<start>", 2)]
    for t in tokens:
        word = t['stem'] if t['stem'] in tokenizer_vocab else (t['original'] if t['original'] in tokenizer_vocab else "<unk>")
        ids.append(tokenizer_vocab.get(word, 1))
    ids.append(tokenizer_vocab.get("<end>", 3))
    return ids

def decode_ids(ids: List[int]) -> str:
    return ' '.join([reverse_vocab.get(i, '<unk>') for i in ids if i not in {0,2,3}])

def get_context_from_memory(query: str) -> str:
    return word_understanding.get_context(query)

def generate_from_prompt(prompt: str, max_len: int, temperature: float) -> str:
    if not TORCH_AVAILABLE:
        return prompt
    if model is not None and tokenizer_vocab is not None:
        input_ids = torch.tensor([encode_text(prompt)], dtype=torch.long).to(device)
        output_ids = []
        with torch.no_grad():
            for _ in range(max_len):
                logits = model(input_ids)[0, -1, :] / temperature
                probs = F.softmax(logits, dim=-1)
                next_id = torch.multinomial(probs, 1).item()
                output_ids.append(next_id)
                input_ids = torch.cat([input_ids, torch.tensor([[next_id]], device=device)], dim=1)
                if next_id == tokenizer_vocab.get("<end>", 3):
                    break
        return decode_ids(output_ids)
    else:
        return prompt

# Pydantic models

class SignupRequest(BaseModel):
    # Matches your db_models.py max capacity of 255
    full_name: str = Field(..., min_length=2, max_length=255)
    
    # Enforces standard international telephone number constraints (7 to 20 characters)
    phone: str = Field(..., min_length=7, max_length=15)
    
    password: str = Field(..., min_length=6, max_length=100)
    language: str = Field("en", max_length=10)
    
    # Adjusted to max_length=100 to safely match the database field layout
    country: str = Field("Nigeria", max_length=100)
    temperament: str = Field("sanguine", max_length=20)

class LoginRequest(BaseModel):
    phone: str = Field(..., min_length=7, max_length=15)
    password: str = Field(..., min_length=6, max_length=100)


class WorkspaceCreate(BaseModel):
    first_message: str = Field(..., min_length=1)
    project_name: Optional[str] = Field(default=None, max_length=255)

class MessageRequest(BaseModel):
    content: str

class GenerateRequest(BaseModel):
    prompt: str
    max_len: int = 500
    temperature: float = 0.8
    workspace_name: Optional[str] = ""
    conversation_history: Optional[str] = ""
    temperament: str = "sanguine"

class ResearchRequest(BaseModel):
    query: str

class CrawlRequest(BaseModel):
    url: str

class TrainRequest(BaseModel):
    epochs: int = 1           # manual trigger default; pass more for a long run
    batch_size: int = 8
    max_texts: int = 500      # cap on grid documents pulled per run
    lr: float = 3e-4
    label: str = "manual"     # free-form tag for trace logging

class PredictRequest(BaseModel):
    text: str
    top_k: int = 5

class SummaryRequest(BaseModel):
    text: str

class FollowUpRequest(BaseModel):
    query: str
    answer: str

class DirectMessageRequest(BaseModel):
    recipient_phone: str
    content: str


# ==============================================================================
# AUTH ENDPOINTS
# ==============================================================================

@app.post("/auth/signup")
async def signup(req: SignupRequest):
    db = SessionLocal()
    try:
        # Maps full country name selections from your HTML form into 2-letter ISO codes for validation
        country_mapping = {
            "Nigeria": "NG", "Ghana": "GH", "Kenya": "KE", "South Africa": "ZA",
            "Egypt": "EG", "Ethiopia": "ET", "Morocco": "MA", "Cameroon": "CM",
            "Ivory Coast": "CI", "Uganda": "UG", "United States": "US", 
            "United Kingdom": "GB", "India": "IN", "Canada": "CA", "Australia": "AU",
            "Germany": "DE", "France": "FR", "China": "CN", "Brazil": "BR", 
            "United Arab Emirates": "AE"
        }
        
        # Check if it's already a 2-letter fallback code, otherwise map it
        if len(req.country) == 2:
            country_code = req.country.upper()
        else:
            country_code = country_mapping.get(req.country, "NG")

        if not validate_phone(req.phone, country_code):
            raise HTTPException(400, "Invalid phone number.")
            
        existing = db.query(User).filter(User.phone == req.phone).first()
        if existing:
            raise HTTPException(400, "Phone already registered")
            
        hashed = hash_password(req.password)
        start_row, start_col = compute_user_cell(req.full_name, req.phone)
        
        new_user = User(
            full_name=req.full_name,
            phone=req.phone,
            password_hash=hashed,
            language=req.language,
            country=req.country,  # Stores cleanly up to 200 characters
            temperament=req.temperament,
            start_row=start_row,
            start_col=start_col
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        token = create_access_token(str(new_user.id))
        return {"access_token": token, "user": {"id": str(new_user.id), "full_name": new_user.full_name, "start_row": start_row}}
    finally:
        db.close()

# ACCD-ORG: org create + join
class OrgCreateRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    phone: str = Field(..., min_length=5, max_length=32)
    password: str = Field(..., min_length=6, max_length=200)
    org_name: str = Field(..., min_length=2, max_length=255)
    org_slug: str = Field(..., min_length=2, max_length=255)
    org_email: Optional[str] = None
    org_country: str = "Nigeria"
    language: str = "en"


class OrgJoinRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    phone: str = Field(..., min_length=5, max_length=32)
    password: str = Field(..., min_length=6, max_length=200)
    worker_credential: str = Field(..., min_length=3, max_length=255)
    department: str = Field(..., min_length=1, max_length=100)
    role: str = "member"
    title: Optional[str] = None
    language: str = "en"


@app.post("/auth/org/create")
async def org_create(req: OrgCreateRequest):
    """Create an org, an admin user, and return a worker credential."""
    import uuid as _uuid
    import secrets as _secrets
    from db_models import User, Organization
    from org.roles import ROLE_CEO

    db = SessionLocal()
    try:
        if db.query(User).filter(User.phone == req.phone).first():
            raise HTTPException(400, "phone already registered")
        if db.query(Organization).filter(Organization.slug == req.org_slug).first():
            raise HTTPException(400, "org slug already taken")

        user = User(
            id=_uuid.uuid4(),
            full_name=req.full_name,
            phone=req.phone,
            password_hash=hash_password(req.password),
            country=req.org_country,
            language=req.language,
        )
        db.add(user)
        db.flush()

        org_uid = f"org-{req.org_slug}"
        org = Organization(
            id=_uuid.uuid4(),
            name=req.org_name,
            slug=req.org_slug,
            email=req.org_email,
            country=req.org_country,
            language=req.language,
            ai_uid=org_uid,
            start_row=1,
            start_col=0,
        )
        db.add(org)
        db.flush()

        # worker credential: orgslug:phonelast4:randomsuffix
        credential = f"{req.org_slug}:{req.phone[-4:]}:{_secrets.token_hex(4)}"

        try:
            from db.models_org import WorkspaceMember
            from org.departments import create_department_room
            create_department_room(
                session=db,
                organization_id=str(org.id),
                department_name="Administration",
                created_by=str(user.id),
            )
        except Exception as e:
            print(f"[ACCD-ORG] dept setup skipped: {e}")

        db.commit()
        token = create_access_token({"sub": str(user.id), "phone": user.phone})
        return {
            "access_token": token,
            "user": {"id": str(user.id), "phone": user.phone,
                     "full_name": user.full_name, "role": ROLE_CEO},
            "org": {"id": str(org.id), "name": org.name, "slug": org.slug,
                    "ai_uid": org.ai_uid},
            "worker_credential": credential,
        }
    finally:
        db.close()


@app.post("/auth/org/join")
async def org_join(req: OrgJoinRequest):
    """Worker signup: validate credential, create pending membership."""
    import uuid as _uuid
    from db_models import User, Organization, OrganizationMembership

    db = SessionLocal()
    try:
        parts = req.worker_credential.split(":")
        if len(parts) < 3:
            raise HTTPException(400, "invalid worker credential format")

        slug = parts[0]
        org = db.query(Organization).filter(Organization.slug == slug).first()
        if not org:
            raise HTTPException(404, "org not found for that credential")

        if db.query(User).filter(User.phone == req.phone).first():
            raise HTTPException(400, "phone already registered")

        user = User(
            id=_uuid.uuid4(),
            full_name=req.full_name,
            phone=req.phone,
            password_hash=hash_password(req.password),
            country=org.country,
            language=req.language,
        )
        db.add(user)
        db.flush()

        credential_hash = hashlib.sha256(
            req.worker_credential.encode("utf-8")
        ).hexdigest()

        membership = OrganizationMembership(
            id=_uuid.uuid4(),
            user_id=user.id,
            organization_id=org.id,
            role=req.role or "member",
            department=req.department,
            title=req.title,
            credential_hash=credential_hash,
            credential_active=False,  # pending admin approval
        )
        db.add(membership)
        db.commit()
        return {
            "pending": True,
            "user_id": str(user.id),
            "org_slug": org.slug,
            "message": "signup submitted; wait for admin approval",
        }
    finally:
        db.close()


@app.post("/auth/login")
async def login(req: LoginRequest):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.phone == req.phone).first()
        if not user or not verify_password(req.password, user.password_hash):
            raise HTTPException(401, "Invalid credentials")
        token = create_access_token(str(user.id))
        return {"access_token": token, "user": {"id": str(user.id), "full_name": user.full_name, "start_row": user.start_row}}
    finally:
        db.close()


# ==============================================================================
# WORKSPACE ENDPOINTS (Complete & Corrected)
# ==============================================================================

@app.post("/workspace")
async def create_workspace(
    req: WorkspaceCreate,
    user: User = Depends(get_current_user)
):
    db = SessionLocal()

    try:
        project_name = (
            req.project_name.strip()
            if req.project_name
            else req.first_message.strip()[:80]
        )

        initial_keywords = extract_keywords(req.first_message)

        project_grid_cv = build_project_grid_cv(initial_keywords)

        temporal_context = build_temporal_context()

        ws = Workspace(
            user_id=user.id,
            project_name=project_name,
            project_domain=detect_domain(req.first_message),
            project_keywords=initial_keywords,
            project_grid_cv=project_grid_cv,
            context_summary=req.first_message,
            temporal_context=temporal_context,
            context_version=1
        )

        db.add(ws)
        db.commit()
        db.refresh(ws)

        msg = Message(
            workspace_id=ws.id,
            user_id=user.id,
            role="user",
            content=req.first_message,
            detected_domain=detect_domain(req.first_message),
            keywords=initial_keywords,
            grid_cv=project_grid_cv,
            temporal_context=temporal_context
        )

        db.add(msg)
        db.commit()

        return {
            "workspace_id": str(ws.id),
            "project_name": ws.project_name,
            "project_domain": ws.project_domain,
            "keywords": initial_keywords,
            "grid_cv": project_grid_cv,
            "temporal_context": temporal_context
        }

    finally:
        db.close()


@app.post("/workspace/{ws_id}/message")
async def add_workspace_message(
    ws_id: str,
    req: MessageRequest,
    user: User = Depends(get_current_user)
):
    db = SessionLocal()

    try:
        ws = (
            db.query(Workspace)
            .filter(
                Workspace.id == ws_id,
                Workspace.user_id == user.id
            )
            .first()
        )

        if not ws:
            raise HTTPException(404, "Workspace not found")

        message_keywords = extract_keywords(req.content)

        all_keywords = merge_keywords(
            ws.project_keywords,
            message_keywords
        )

        project_grid_cv = build_project_grid_cv(all_keywords)

        temporal_context = build_temporal_context()

        message_domain = detect_domain(req.content)

        msg = Message(
            workspace_id=ws.id,
            user_id=user.id,
            role="user",
            content=req.content,
            detected_domain=message_domain,
            keywords=message_keywords,
            grid_cv=build_project_grid_cv(message_keywords),
            temporal_context=temporal_context
        )

        db.add(msg)

        ws.project_keywords = all_keywords
        ws.project_grid_cv = project_grid_cv
        ws.project_domain = message_domain
        ws.temporal_context = temporal_context
        ws.updated_at = datetime.utcnow()

        db.commit()

        # ACCD-INTEGRATION: decide whether the AI should respond
        try:
            from models_org import WorkspaceMember
            member_count = 1 + db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == ws.id
            ).count()
        except Exception:
            member_count = 1

        try:
            ai_state = accd_handle_message(
                workspace_id=str(ws.id),
                user_id=str(user.id),
                text=req.content,
                member_count=member_count,
            )
        except Exception as e:
            ai_state = {"invoked": False, "trigger": None,
                        "error": f"{type(e).__name__}: {e}"}

        return {
            "ok": True,
            "workspace_id": str(ws.id),
            "keywords": all_keywords,
            "grid_cv": project_grid_cv,
            "domain": message_domain,
            "temporal_context": temporal_context,
            "member_count": member_count,
            "ai_invoked": ai_state.get("invoked", False),
            "ai_trigger": ai_state.get("trigger"),
        }

    finally:
        db.close()


@app.post("/workspace/{ws_id}/generate")
async def generate_in_workspace(
    ws_id: str,
    req: GenerateRequest,
    user: User = Depends(get_current_user)
):
    db = SessionLocal()

    try:
        ws = (
            db.query(Workspace)
            .filter(
                Workspace.id == ws_id,
                Workspace.user_id == user.id
            )
            .first()
        )

        if not ws:
            raise HTTPException(404, "Workspace not found")

        msgs = (
            db.query(Message)
            .filter(Message.workspace_id == ws_id)
            .order_by(Message.created_at.desc())
            .limit(20)
            .all()
        )

        history = "\n".join(
            f"{m.role}: {m.content}"
            for m in reversed(msgs)
        )

        # Refresh temporal context when the room is used.
        temporal_context = build_temporal_context()

        ws.temporal_context = temporal_context

        memory_context = get_context_from_memory(req.prompt)

        project_context = {
            "project_name": ws.project_name,
            "project_domain": ws.project_domain,
            "project_keywords": ws.project_keywords or [],
            "project_grid_cv": ws.project_grid_cv or {},
            "context_summary": ws.context_summary or "",
            "temporal_context": temporal_context
        }

        room_context = json.dumps(
            project_context,
            ensure_ascii=False
        )

        combined_context = (
            f"PROJECT/ROOM CONTEXT:\n"
            f"{room_context}\n\n"
            f"GLOBAL MEMORY CONTEXT:\n"
            f"{memory_context}"
        )

        prompt = build_prompt(
            query=req.prompt,
            context=combined_context,
            workspace_name=ws.project_name,
            conversation_history=history,
            temperament=user.temperament
        )

        # MODE-WIRE: classify request before generation
        _accd_mode = None
        _accd_policy = None
        try:
            from cognition.control import CognitionControl
            from agent.mode_classifier import classify as _classify_mode, policy_for as _policy_for
            _decision = _classify_mode(text=req.prompt)
            _policy = _policy_for(_decision.mode)
            _accd_mode = _decision.mode.value
            _accd_policy = {
                "code_mode": _policy.code_mode,
                "verification_level": _policy.verification_level,
                "max_iterations": _policy.max_iterations,
                "allow_mutations": _policy.allow_mutations,
                "read_only": _policy.read_only,
                "emit_planning_status": _policy.emit_planning_status,
            }
            print(f"[ACCD-MODE] {_accd_mode} conf={_decision.confidence:.2f}")
        except Exception as e:
            print(f"[ACCD-MODE] classify skipped: {type(e).__name__}: {e}")

        # JOB-BRANCH: end-to-end pipeline (plan -> per-step generate+verify+retry)
        # tools available to each step via registry from integration state
        if _accd_mode == "job":
            try:
                from integration import get_state as _accd_state
                _reg = _accd_state().get("registry")

                def _gen(p: str) -> str:
                    return generate_from_prompt(p, req.max_len, req.temperature)

                accd_frames = list(_run_job(
                    workspace_id=str(ws.id),
                    user_id=str(user.id),
                    prompt=req.prompt,
                    generate_fn=_gen,
                    max_steps=8,
                    max_iterations=(_accd_policy or {}).get("max_iterations", 5),
                    code_mode=True,
                    verify_each_step=True,
                    registry=_reg,
                    enable_tools=True,
                    max_tool_rounds=5,
                ))
                accd_summary = {
                    "mode": "job",
                    "frames": len(accd_frames),
                    "tools_available": len(_reg._tools) if _reg is not None else 0,
                }
            except Exception as e:
                accd_frames = [f"#error#run_job: {type(e).__name__}: {e}"]
                accd_summary = {"error": str(e)}

            _job_msg = Message(
                workspace_id=ws.id,
                user_id=user.id,
                role="assistant",
                content="[job streamed]",
                detected_domain="code",
                keywords=extract_keywords(req.prompt),
                grid_cv=build_project_grid_cv(extract_keywords(req.prompt)),
                temporal_context=temporal_context,
            )
            db.add(_job_msg)
            db.commit()

            return {
                "generated": "[job streamed]",
                "mode": _accd_mode,
                "mode_policy": _accd_policy,
                "frames": accd_frames,
                "verification": accd_summary,
                "workspace": {
                    "id": str(ws.id),
                    "project_name": ws.project_name,
                    "domain": ws.project_domain,
                    "keywords": ws.project_keywords,
                    "temporal_context": temporal_context,
                },
            }

        generated = generate_from_prompt(
            prompt,
            req.max_len,
            req.temperature
        )

        if not enforce_rules(generated, user.temperament):
            generated = "I apologize, I cannot provide that answer."

        # MODE-AWARE: verify code blocks only when code_mode is on
        try:
            if _accd_policy and not _accd_policy.get("code_mode", True):
                # chat / plan / research — stream as prose
                accd_frames = [f"#prose#{generated}"] if generated else []
                accd_summary = {
                    "blocks": 0, "verified": 0, "rejected": 0, "iterations": 0,
                    "mode_skipped_verification": _accd_mode or "chat",
                }
            else:
                accd_frames, accd_summary = accd_verify_and_frame(
                    generated,
                    max_iterations=(_accd_policy or {}).get("max_iterations", 3),
                )
        except Exception as e:
            accd_frames = [f"#error#integration: {type(e).__name__}: {e}"]
            accd_summary = {"error": str(e)}

        msg = Message(
            workspace_id=ws.id,
            user_id=user.id,
            role="assistant",
            content=generated,
            detected_domain=detect_domain(req.prompt),
            keywords=extract_keywords(req.prompt),
            grid_cv=build_project_grid_cv(
                extract_keywords(req.prompt)
            ),
            temporal_context=temporal_context
        )

        db.add(msg)
        db.commit()

        return {
            "generated": generated,
            "mode": _accd_mode,
            "mode_policy": _accd_policy,
            "frames": accd_frames,
            "verification": accd_summary,
            "workspace": {
                "id": str(ws.id),
                "project_name": ws.project_name,
                "domain": ws.project_domain,
                "keywords": ws.project_keywords,
                "temporal_context": temporal_context
            }
        }

    finally:
        db.close()

# General generation
@app.post("/generate")
async def generate(req: GenerateRequest):
    context = get_context_from_memory(req.prompt)
    prompt = build_prompt(
        query=req.prompt,
        context=context,
        workspace_name=req.workspace_name,
        conversation_history=req.conversation_history,
        temperament=req.temperament
    )
    generated = generate_from_prompt(prompt, req.max_len, req.temperature)
    follow_ups = generate_follow_ups(req.prompt, generated, detect_domain(req.prompt))
    if not enforce_rules(generated, req.temperament):
        generated = "I apologize, I cannot provide that answer."
    return {"generated": generated, "follow_ups": follow_ups}

# Prediction
@app.post("/predict")
async def predict(req: PredictRequest):
    if model is None or tokenizer_vocab is None:
        raise HTTPException(400, "Model not trained")
    input_ids = torch.tensor([encode_text(req.text)], dtype=torch.long).to(device)
    with torch.no_grad():
        logits = model(input_ids)[0, -1, :]
        probs = F.softmax(logits, dim=-1)
        topk = torch.topk(probs, req.top_k)
        predictions = []
        for i in range(req.top_k):
            word = reverse_vocab.get(topk.indices[i].item(), "<unk>")
            predictions.append({"word": word, "prob": topk.values[i].item()})
    return {"predictions": predictions}

# Research
@app.post("/research")
async def research(req: ResearchRequest):
    query = req.query.strip()
    cached = search_cache.get(query)
    if cached:
        return cached
    results = await asyncio.gather(
        fetch_dictionary(query.split()[0] if query.split() else query),
        fetch_news(query),
        fetch_books(query),
        fetch_elibrary(query),
        fetch_wikipedia(query)
    )
    data = {
        "dictionary": results[0],
        "news": results[1],
        "books": results[2],
        "elibrary": results[3],
        "wikipedia": results[4]
    }
    search_cache.set(query, data)
    return data


# Crawl
@app.post("/crawl")
async def crawl_web(req: CrawlRequest):
    text = web_crawler.crawl(req.url)
    doc_id = memory.add_document(text, "en", source=req.url)
    
    # Securely create the folder if it doesn't exist to avoid FileNotFoundError
    os.makedirs('data', exist_ok=True)
    with open('data/web_words.txt', 'a', encoding='utf-8') as f:
        f.write(text + '\n')
        
    return {"message": "Crawled", "doc_id": doc_id, "words": len(text.split())}


# Train
@app.post("/train")
async def train(req: TrainRequest):
    # ACCD-TRAIN: report torch availability, pass through params, keep model reload
    try:
        from training.train import train as do_train, TORCH_AVAILABLE as _TR
    except Exception:
        try:
            from train import train as do_train, TORCH_AVAILABLE as _TR
        except Exception:
            from train import train as do_train
            _TR = True

    if not _TR:
        return {
            "ok": False,
            "reason": "torch not installed on this runtime",
            "hint": "pip install torch (or deploy via the HF Spaces Docker image)",
            "label": req.label,
        }

    try:
        kwargs = {
            "epochs": req.epochs,
            "batch_size": req.batch_size,
        }
        # pass extended params only if the signature accepts them
        import inspect
        sig = inspect.signature(do_train)
        if "max_texts" in sig.parameters:
            kwargs["max_texts"] = req.max_texts
        if "lr" in sig.parameters:
            kwargs["lr"] = req.lr

        report = await asyncio.to_thread(do_train, **kwargs)
        load_model_if_exists()
        return {
            "ok": True,
            "label": req.label,
            "params": kwargs,
            "report": report if isinstance(report, dict) else str(report),
        }
    except Exception as e:
        return {
            "ok": False,
            "reason": f"{type(e).__name__}: {e}",
            "label": req.label,
        }


@app.get("/train/status")
async def train_status(user: User = Depends(get_current_user)):
    try:
        from training.train import TORCH_AVAILABLE as _TR
    except Exception:
        try:
            from train import TORCH_AVAILABLE as _TR
        except Exception:
            _TR = True
    return {
        "torch_available": _TR,
        "ready": _TR,
    }

# Summary
@app.post("/summary")
async def summary(req: SummaryRequest):
    summary_text = generate_ai_summary(req.text)
    return {"summary": summary_text}

# Follow-up
@app.post("/follow_up")
async def follow_up(req: FollowUpRequest):
    domain = detect_domain(req.query)
    follow_ups = generate_follow_ups(req.query, req.answer, domain)
    return {"follow_ups": follow_ups}

# Direct messaging endpoints (internal)
@app.post("/api/messages/send")
async def send_direct_message(req: DirectMessageRequest, user: User = Depends(get_current_user)):
    try:
        msg = send_message(user.phone, req.recipient_phone, req.content)
        return {"id": msg.id, "sender": msg.sender_phone, "recipient": msg.recipient_phone,
                "content": msg.content, "created_at": msg.created_at.isoformat()}
    except ValueError as e:
        raise HTTPException(404, str(e))

@app.get("/api/messages/conversations")
async def list_conversations(user: User = Depends(get_current_user)):
    return get_conversations(user.phone)

@app.get("/api/messages/with/{other_phone}")
async def get_messages(other_phone: str, user: User = Depends(get_current_user)):
    msgs = get_messages_between(user.phone, other_phone)
    return [{"id": m.id, "sender": m.sender_phone, "recipient": m.recipient_phone,
             "content": m.content, "created_at": m.created_at.isoformat()} for m in msgs]

# Public API endpoints (indexer, crawler, tokenizer, general AI)
@app.post("/api/v1/public/tokenize")
async def public_tokenize(text: str, lang: str = "en", api_key: str = Depends(verify_api_key)):
    tokens = tokenize(text, lang)
    return {
        "tokens": tokens,
        "grid_dims": grid_dims(lang),
        "languages": supported_languages()
    }

@app.post("/api/v1/public/index")
async def public_index(text: str, lang: str = "en", source: str = "", api_key: str = Depends(verify_api_key)):
    doc_id = memory.add_document(text, lang, source)
    return {"doc_id": doc_id, "message": "Document indexed"}

@app.post("/api/v1/public/crawl")
async def public_crawl(url: str, api_key: str = Depends(verify_api_key)):
    text = web_crawler.crawl(url)
    doc_id = memory.add_document(text, "en", url)
    return {"doc_id": doc_id, "words": len(text.split())}

@app.post("/api/v1/public/generate")
async def public_generate(req: GenerateRequest, api_key: str = Depends(verify_api_key)):
    context = get_context_from_memory(req.prompt)
    prompt = build_prompt(
        query=req.prompt,
        context=context,
        workspace_name=req.workspace_name,
        conversation_history=req.conversation_history,
        temperament=req.temperament
    )
    generated = generate_from_prompt(prompt, req.max_len, req.temperature)
    follow_ups = generate_follow_ups(req.prompt, generated, detect_domain(req.prompt))
    return {"generated": generated, "follow_ups": follow_ups}

@app.post("/api/v1/public/predict")
async def public_predict(req: PredictRequest, api_key: str = Depends(verify_api_key)):
    return await predict(req)

@app.post("/api/v1/public/research")
async def public_research(req: ResearchRequest, api_key: str = Depends(verify_api_key)):
    return await research(req)

@app.post("/api/v1/public/train")
async def public_train(req: TrainRequest, api_key: str = Depends(verify_api_key)):
    return await train(req)

# ==============================================================================
# APPLICATION LIFECYCLE
# ==============================================================================
from fastapi.responses import RedirectResponse as _AccdRedirect

@app.get("/")
async def _accd_root():
    return _AccdRedirect(url="/app")

@app.get("/health")
async def _accd_health():
    return {"ok": True, "service": "accodite"}

@app.on_event("startup")
async def startup_event():
    # Line 1: Build structural database tables safely on launch
    Base.metadata.create_all(bind=engine) 
    
    # Line 2: Offload the machine learning loop onto a non-blocking background thread
    # STARTUP-FIX: run the monitor task directly on the app's loop
    try:
        from training.background_training import auto_train_monitor as _accd_monitor
        asyncio.create_task(_accd_monitor())
        print("[ACCD] background monitor scheduled")
    except Exception as _e:
        print(f"[ACCD] monitor scheduling skipped: {type(_e).__name__}: {_e}")

    # SCHEMA-SYNC: add missing columns to existing tables (create_all can't)
    try:
        from db.sync_schema import sync_schema as _accd_sync
        added = _accd_sync(engine)
        if added:
            print(f"[ACCD] schema-sync added {len(added)} column(s)")
        else:
            print("[ACCD] schema-sync: no changes")
    except Exception as _e:
        print(f"[ACCD] schema-sync skipped: {type(_e).__name__}: {_e}")

    # UNIQUE-CONSTRAINTS: phone identity must be enforced at DB level
    try:
        from db.sync_schema import ensure_unique_constraints as _accd_uniq
        added_uniq = _accd_uniq(engine)
        if added_uniq:
            print(f"[ACCD] unique constraints added: {added_uniq}")
        else:
            print("[ACCD] unique constraints: all present")
    except Exception as _e:
        print(f"[ACCD] unique-constraints skipped: {type(_e).__name__}: {_e}")

    # ACCD-STARTUP: build pipeline singletons (grid, partition, gate, trigger, pstm)
    try:
        from integration import bootstrap as _accd_boot
        st = _accd_boot(root=os.path.dirname(os.path.abspath(__file__)) + "/..")
        print(f"[ACCD] bootstrap ready={st.get('ready')}")
        print(f"[ACCD] grid={type(st.get('grid')).__name__} "
              f"partition={type(st.get('partition')).__name__} "
              f"trigger={type(st.get('trigger')).__name__} "
              f"pstm={type(st.get('pstm')).__name__}")
    except Exception as e:
        print(f"[ACCD] startup error: {type(e).__name__}: {e}")


# ================================================
# SERVE FRONTEND (
#=====================================================
# FRONTEND-PATH: resolve relative to this file, not CWD
_frontend_candidates = [
    os.environ.get("ACCD_FRONTEND_DIR", ""),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "ui"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "ui"),
    "../frontend/ui",
    "frontend/ui",
]
_frontend_dir = next((d for d in _frontend_candidates if d and os.path.isdir(d)), None)
if _frontend_dir:
    app.mount("/app", StaticFiles(directory=_frontend_dir, html=True), name="frontend")
    print(f"[ACCD] frontend mounted at /app from {_frontend_dir}")
else:
    print("[ACCD] frontend directory not found — /app will 404")


