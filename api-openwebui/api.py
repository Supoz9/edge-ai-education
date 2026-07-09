
"""
api.py — @author: Supoz9 — v1.5


Flux d'une requête :
  1. reçoit la question de l'élève (POST /chat)
  2. RECHERCHE les passages pertinents (retrieval.search_passages, garde-fou inclus)
  3. construit un prompt (étape 1 : basique ; étape 2 : maïeutique)
  4. appelle Ollama pour GÉNÉRER la réponse
  5. renvoie la réponse
 
Étape 1 volontairement simple : pas de streaming, prompt non-maïeutique. But :
valider de bout en bout que question -> recherche -> Ollama -> réponse fonctionne.
Le prompt maïeutique viendra à l'étape 2 (prompts.py).
 
Ollama tourne sur l'HÔTE (pas dans Docker). Depuis le conteneur, on l'atteint
via host.docker.internal (lancer le conteneur avec
--add-host=host.docker.internal:host-gateway).
"""
 
import os
import sys
 
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
 
# retrieval.py vit dans le dossier rag/ ; on l'ajoute au path.
sys.path.insert(0, os.environ.get("RAG_DIR", "/app"))
from retrieval import search_passages  # noqa: E402
from prompts import build_messages  # noqa: E402
 
# --- Config ------------------------------------------------------------------
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:14b")
TOP_K = int(os.environ.get("API_TOP_K", "5"))
 
app = FastAPI(title="Tuteur RAG CIEL", version="0.1")
 
 
# --- Schémas -----------------------------------------------------------------
class ChatRequest(BaseModel):
    question: str
    k: int | None = None
 
 
class ChatResponse(BaseModel):
    reponse: str
    passages_utilises: list[dict]
 
 
# --- Appel Ollama ------------------------------------------------------------
def ask_ollama(messages: list) -> str:
    """Appelle Ollama en non-streaming (étape 1). Renvoie le texte complet.
 
    Prend une liste de messages (system maïeutique + user), pas un prompt brut.
    - `think: False` désactive le raisonnement verbeux de qwen3.
    - timeout large : la 1re requête charge le modèle en VRAM (lent), les
      suivantes sont rapides.
    """
    resp = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "think": False,  # désactive le bloc <think> de qwen3
        },
        timeout=600,
    )
    resp.raise_for_status()
    data = resp.json()
    msg = data.get("message", {})
    content = msg.get("content", "")
    if not content:
        content = data.get("response", "") or "(réponse vide du modèle)"
    return content
 
 
# --- Endpoints ---------------------------------------------------------------
@app.get("/health")
def health():
    """Vérifie que l'API tourne et qu'Ollama répond."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        ollama_ok = r.ok
    except Exception:
        ollama_ok = False
    return {"api": "ok", "ollama": "ok" if ollama_ok else "injoignable",
            "model": OLLAMA_MODEL}
 
 
@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Le cœur : question -> recherche -> Ollama -> réponse."""
    k = req.k or TOP_K
    try:
        passages = search_passages(req.question, k=k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de recherche RAG : {e}")
 
    prompt_messages = build_messages(req.question, passages)
 
    try:
        reponse = ask_ollama(prompt_messages)
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504,
                            detail="Ollama trop lent (timeout). Le modèle "
                                   "est-il en train de charger en VRAM ?")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502,
                            detail=f"Erreur d'appel à Ollama : {e}")
 
    return ChatResponse(
        reponse=reponse,
        passages_utilises=[
            {"source": p.source, "type": p.type, "score": p.score}
            for p in passages
        ],
    )
 
