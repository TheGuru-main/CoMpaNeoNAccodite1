import asyncio
import torch
import torch.nn.functional as F
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from api_auth import verify_api_key
from memory_grid import MemoryGrid
from web_crawler import WebCrawler
from tokenizer import tokenize, normalize_lang, grid_dims, supported_languages
from word_understanding import WordUnderstanding
from ai_model import MiniCompanionAI
from data_mixer import DataMixer
from external import fetch_dictionary, fetch_news, fetch_books, fetch_elibrary, fetch_wikipedia
from prompts_manager import build_prompt
from intent_analyzer import detect_domain
from rules import enforce_rules

router = APIRouter(prefix="/api/v1/public", tags=["Public API"])

# Shared instances (passed via dependency or global)
memory = None
web_crawler = None
model = None
tokenizer_vocab = None
reverse_vocab = None
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

def set_globals(memory_grid, crawler, ai_model, vocab, rev_vocab):
    global memory, web_crawler, model, tokenizer_vocab, reverse_vocab
    memory = memory_grid
    web_crawler = crawler
    model = ai_model
    tokenizer_vocab = vocab
    reverse_vocab = rev_vocab

# Models
class TokenizeRequest(BaseModel):
    text: str
    lang: str = "en"

class TokenizeResponse(BaseModel):
    tokens: List[Dict[str, Any]]
    grid_dims: Dict[str, Any]
    languages: List[Dict[str, Any]]

class IndexRequest(BaseModel):
    text: str
    lang: str = "en"
    source: str = ""

class CrawlRequest(BaseModel):
    url: str

class GenerateRequest(BaseModel):
    prompt: str
    max_len: int = 500
    temperature: float = 0.8
    workspace_name: Optional[str] = ""
    conversation_history: Optional[str] = ""
    temperament: str = "sanguine"

class GenerateResponse(BaseModel):
    generated: str
    follow_ups: List[str] = []

class PredictRequest(BaseModel):
    text: str
    top_k: int = 5

class PredictResponse(BaseModel):
    predictions: List[Dict[str, Any]]

class ResearchRequest(BaseModel):
    query: str

class ResearchResponse(BaseModel):
    dictionary: Dict
    news: Dict
    books: Dict
    elibrary: Dict
    wikipedia: Dict

# Dependency for API key
async def require_api_key(api_key: str = Depends(verify_api_key)):
    return api_key

# -------------------- Endpoints --------------------

@router.post("/tokenize", response_model=TokenizeResponse)
async def tokenize_text(req: TokenizeRequest, api_key: str = Depends(require_api_key)):
    tokens = tokenize(req.text, req.lang)
    return {
        "tokens": tokens,
        "grid_dims": grid_dims(req.lang),
        "languages": supported_languages()
    }

@router.post("/index")
async def index_document(req: IndexRequest, api_key: str = Depends(require_api_key)):
    doc_id = memory.add_document(req.text, req.lang, req.source)
    return {"doc_id": doc_id, "message": "Document indexed"}

@router.post("/crawl")
async def crawl_url(req: CrawlRequest, api_key: str = Depends(require_api_key)):
    text = web_crawler.crawl(req.url)
    doc_id = memory.add_document(text, "en", req.url)
    return {"doc_id": doc_id, "words": len(text.split())}

@router.post("/generate", response_model=GenerateResponse)
async def generate_public(req: GenerateRequest, api_key: str = Depends(require_api_key)):
    context = WordUnderstanding(memory).get_context(req.prompt)
    prompt = build_prompt(
        query=req.prompt,
        context=context,
        workspace_name=req.workspace_name,
        conversation_history=req.conversation_history,
        temperament=req.temperament
    )
    if model is not None and tokenizer_vocab is not None:
        input_ids = torch.tensor([encode_text(req.prompt)], dtype=torch.long).to(device)
        output_ids = []
        with torch.no_grad():
            for _ in range(req.max_len):
                logits = model(input_ids)[0, -1, :] / req.temperature
                probs = F.softmax(logits, dim=-1)
                next_id = torch.multinomial(probs, 1).item()
                output_ids.append(next_id)
                input_ids = torch.cat([input_ids, torch.tensor([[next_id]], device=device)], dim=1)
                if next_id == tokenizer_vocab.get("<end>", 3):
                    break
        generated = decode_ids(output_ids)
    else:
        generated = prompt
    if not enforce_rules(generated, req.temperament):
        generated = "I apologize, I cannot provide that answer."
    follow_ups = generate_follow_ups(req.prompt, generated, detect_domain(req.prompt))
    return {"generated": generated, "follow_ups": follow_ups}

@router.post("/predict", response_model=PredictResponse)
async def predict_public(req: PredictRequest, api_key: str = Depends(require_api_key)):
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

@router.post("/research", response_model=ResearchResponse)
async def research_public(req: ResearchRequest, api_key: str = Depends(require_api_key)):
    query = req.query.strip()
    results = await asyncio.gather(
        fetch_dictionary(query.split()[0] if query.split() else query),
        fetch_news(query),
        fetch_books(query),
        fetch_elibrary(query),
        fetch_wikipedia(query)
    )
    return {
        "dictionary": results[0],
        "news": results[1],
        "books": results[2],
        "elibrary": results[3],
        "wikipedia": results[4]
    }

@router.post("/train")
async def train_public(req: TrainRequest, api_key: str = Depends(require_api_key)):
    from train import train as do_train
    await asyncio.to_thread(do_train)
    return {"message": "Training completed"}

# Helper functions to encode/decode (copy from main.py)
def encode_text(text, lang="en"):
    # similar implementation as main.py
    pass

def decode_ids(ids):
    pass