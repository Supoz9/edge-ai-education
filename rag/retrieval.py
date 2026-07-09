
"""
retrieval.py — @author: supoz9 — v1.0

Cœur de la recherche RAG hybride, réutilisable.
 
Extrait de search.py pour être importé À LA FOIS par la CLI (search.py) et par
l'API (api-openwebui/api.py). Le modèle d'embedding et la connexion ChromaDB
sont chargés UNE SEULE FOIS (singleton) : coûteux à l'init, gratuit ensuite.
C'est ce qui permet à l'API de répondre vite à chaque requête d'élève.
 
GARDE-FOU : ne cherche que dans la collection 'ciel' (zone libre). Les corrigés
n'y sont pas indexés, donc ne peuvent jamais remonter.
"""
 
import re
from dataclasses import dataclass
 
import config
 
# --- Singletons (chargés à la première utilisation) --------------------------
_model = None
_collection = None
 
 
def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(config.EMBED_MODEL, device=config.DEVICE)
    return _model
 
 
def _get_collection():
    global _collection
    if _collection is None:
        import chromadb
        client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
        _collection = client.get_collection(config.COLLECTION_NAME)
    return _collection
 
 
# --- Scoring (identique à la version validée dans search.py) ------------------
 
def lexical_score(query: str, doc: str) -> float:
    """Proportion des termes de la requête présents dans le doc, bornée [0,1]."""
    def toks(s):
        return re.findall(r"[a-zA-Z0-9\.\-_/]+", s.lower())
 
    stop = {"le", "la", "les", "un", "une", "des", "de", "du", "à", "a",
            "pour", "sur", "que", "qui", "quoi", "est", "sert", "avec",
            "dans", "et", "ou", "comment", "quel", "quelle"}
    q_terms = [t for t in toks(query) if t not in stop and len(t) > 1]
    if not q_terms:
        q_terms = toks(query)
    if not q_terms:
        return 0.0
    d_tokens = set(toks(doc))
    hits = sum(1 for t in set(q_terms) if t in d_tokens)
    return hits / len(set(q_terms))
 
 
def length_penalty(doc: str, min_chars: int = 120) -> float:
    """Facteur [0,1] pénalisant les chunks trop courts."""
    n = len(doc.strip())
    return 1.0 if n >= min_chars else n / min_chars
 
 
# --- Résultat structuré ------------------------------------------------------
 
@dataclass
class Passage:
    """Un passage récupéré, avec son score et ses métadonnées."""
    text: str
    score: float
    dense: float
    lexical: float
    source: str
    type: str
    activite: str
    sequence: str
    langue: str
    contient_code: bool
    contient_tableau: bool
 
 
# --- LA fonction réutilisable ------------------------------------------------
 
def search_passages(query: str, k: int = None, doc_type: str = None,
                    alpha: float = None) -> list[Passage]:
    """
    Recherche hybride (dense + lexical) dans la collection 'ciel'.
    Renvoie les k meilleurs passages, triés par score décroissant.
 
    C'est le point d'entrée unique : la CLI et l'API l'appellent tous deux.
    Le garde-fou anti-triche est implicite (la collection 'ciel' ne contient
    pas les corrigés).
    """
    k = k if k is not None else config.TOP_K
    alpha = alpha if alpha is not None else config.HYBRID_ALPHA
 
    collection = _get_collection()
    model = _get_model()
 
    q_emb = model.encode([query], normalize_embeddings=True).tolist()
 
    where = {"type": doc_type} if doc_type else None
    pool = collection.query(
        query_embeddings=q_emb,
        n_results=max(k * 4, 20),
        where=where,
        include=["documents", "metadatas", "distances"],
    )
 
    docs = pool["documents"][0]
    metas = pool["metadatas"][0]
    dists = pool["distances"][0]
    if not docs:
        return []
 
    dense_scores = [1.0 - d for d in dists]
 
    def norm(xs):
        lo, hi = min(xs), max(xs)
        return [(x - lo) / (hi - lo) if hi > lo else 0.5 for x in xs]
 
    dn = norm(dense_scores)
    lex_raw = [lexical_score(query, d) for d in docs]
    pen = [length_penalty(d) for d in docs]
    hybrid = [pen[i] * (alpha * dn[i] + (1 - alpha) * lex_raw[i])
              for i in range(len(docs))]
 
    ranked = sorted(range(len(docs)), key=lambda i: hybrid[i], reverse=True)[:k]
 
    results = []
    for i in ranked:
        m = metas[i]
        results.append(Passage(
            text=docs[i],
            score=round(hybrid[i], 3),
            dense=round(dn[i], 3),
            lexical=round(lex_raw[i], 3),
            source=m.get("source", ""),
            type=m.get("type", ""),
            activite=m.get("activite", ""),
            sequence=m.get("sequence", ""),
            langue=m.get("langue", ""),
            contient_code=bool(m.get("contient_code")),
            contient_tableau=bool(m.get("contient_tableau")),
        ))
    return results
 
