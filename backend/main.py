import os
import json
import asyncio
import torch
import torch.nn.functional as F
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
from bubblejumbo_rules import BubbleJumboRules
from word_understanding import WordUnderstanding
from summary import generate_summary as generate_ai_summary
from follow_up import generate_follow_ups
from message import send_message, get_conversations, get_messages_between, DirectMessage

app = FastAPI(title="CoMpaNeoN AI", version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Global components
model: Optional[MiniCompanionAI] = None
tokenizer_vocab: Optional[Dict[str, int]] = None
reverse_vocab: Optional[Dict[int, str]] = None

memory = MemoryGrid()
web_crawler = WebCrawler()
mixer = DataMixer()
search_cache = SearchCache(ttl_seconds=300)
memory_cache = MemoryCache()
bubble_rules = BubbleJumboRules()
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
    if os.path.exists('companion_model.pth'):
        model = MiniCompanionAI(len(tokenizer_vocab))
        model.load_state_dict(torch.load('companion_model.pth', map_location=device))
        model.to(device)
        model.eval()
    else:
        model = None

load_model_if_exists()

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
    epochs: int = 30
    batch_size: int = 8

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

        return {
            "ok": True,
            "workspace_id": str(ws.id),
            "keywords": all_keywords,
            "grid_cv": project_grid_cv,
            "domain": message_domain,
            "temporal_context": temporal_context
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

        generated = generate_from_prompt(
            prompt,
            req.max_len,
            req.temperature
        )

        if not enforce_rules(generated, user.temperament):
            generated = "I apologize, I cannot provide that answer."

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
    from train import train as do_train
    await asyncio.to_thread(do_train, epochs=req.epochs, batch_size=req.batch_size)
    load_model_if_exists()
    return {"message": "Training completed"}

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
@app.on_event("startup")
async def startup_event():
    # Line 1: Build structural database tables safely on launch
    Base.metadata.create_all(bind=engine) 
    
    # Line 2: Offload the machine learning loop onto a non-blocking background thread
    asyncio.create_task(asyncio.to_thread(start_background_training))


# ================================================
# SERVE FRONTEND (
#=====================================================
app.mount("/app", StaticFiles(directory="../frontend/ui", html=True), name="frontend")


