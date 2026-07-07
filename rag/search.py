"""
search.py — 04/07/26 — @Supoz9 — v2.0

CLI de test de la recherche RAG (hybride dense + lexical).

Sert à VOUS, pendant le développement, à vérifier que le RAG remonte les bons
passages avant de le brancher aux élèves. Ce n'est pas l'interface élève (ce
sera Open WebUI) : c'est l'outil de mise au point.
 
Recherche hybride : combine le score dense (embedding BGE-M3) et un score
lexical (recouvrement de termes, façon BM25 léger) pour rattraper les tokens
exacts (références, commandes, IP) que le sémantique lisse.
 
GARDE-FOU : ne cherche que dans la collection 'ciel' (zone libre). Les corrigés
n'y sont pas indexés, donc ne peuvent jamais remonter.
 
Usage :
    python search.py "comment configurer un pool DHCP ?"
    python search.py "tension alimentation GP2Y0A41" --k 3
    python search.py "VLAN" --type cours          # filtre par type de doc
"""
 
import argparse
import math
import re
from collections import Counter
 
import config
 
 
def lexical_score(query: str, doc: str) -> float:
    """Score lexical type BM25-léger : proportion des termes de la REQUÊTE
    présents dans le doc. Complète le dense sur les correspondances exactes
    (IP, commandes, refs). Borné [0,1] : 1.0 = tous les mots de la question
    sont dans le passage. Évite l'aplatissement quand les docs ont des
    longueurs très différentes."""
    def toks(s):
        return re.findall(r"[a-zA-Z0-9\.\-_/]+", s.lower())
 
    # Mots de la requête, hors mots-outils très fréquents qui n'aident pas.
    stop = {"le", "la", "les", "un", "une", "des", "de", "du", "à", "a",
            "pour", "sur", "que", "qui", "quoi", "est", "sert", "avec",
            "dans", "et", "ou", "comment", "quel", "quelle"}
    q_terms = [t for t in toks(query) if t not in stop and len(t) > 1]
    if not q_terms:
        q_terms = toks(query)  # requête ne contenant que des stopwords
    if not q_terms:
        return 0.0
 
    d_tokens = set(toks(doc))
    hits = sum(1 for t in set(q_terms) if t in d_tokens)
    return hits / len(set(q_terms))
 
 
def length_penalty(doc: str, min_chars: int = 120) -> float:
    """Facteur [0,1] pénalisant les chunks trop courts. Un fragment de
    quelques mots ("qualification X X X") obtient un embedding trompeusement
    proche de tout ; on atténue son score pour qu'il ne pollue pas le top.
    Plein score dès ~min_chars atteints."""
    n = len(doc.strip())
    if n >= min_chars:
        return 1.0
    return n / min_chars  # montée linéaire de 0 à 1
 
 
def main():
    ap = argparse.ArgumentParser(description="Recherche RAG hybride (test CLI)")
    ap.add_argument("query", help="la question à poser au RAG")
    ap.add_argument("--k", type=int, default=config.TOP_K, help="nombre de résultats")
    ap.add_argument("--type", default=None,
                    help="filtre par type : cours|tp|datasheet|referentiel")
    ap.add_argument("--alpha", type=float, default=config.HYBRID_ALPHA,
                    help="poids dense vs lexical (0..1)")
    args = ap.parse_args()
 
    import chromadb
    from sentence_transformers import SentenceTransformer
 
    client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    try:
        collection = client.get_collection(config.COLLECTION_NAME)
    except Exception:
        print(f"Collection '{config.COLLECTION_NAME}' introuvable. "
              f"Lancez d'abord `python ingest.py`.")
        return
 
    model = SentenceTransformer(config.EMBED_MODEL, device=config.DEVICE)
    q_emb = model.encode([args.query], normalize_embeddings=True).tolist()
 
    # On récupère un vivier large côté dense, puis on re-score en hybride.
    where = {"type": args.type} if args.type else None
    pool = collection.query(
        query_embeddings=q_emb,
        n_results=max(args.k * 4, 20),
        where=where,
        include=["documents", "metadatas", "distances"],
    )
 
    docs = pool["documents"][0]
    metas = pool["metadatas"][0]
    dists = pool["distances"][0]
 
    if not docs:
        print("Aucun résultat. L'index est-il peuplé ? (`python ingest.py`)")
        return
 
    # Fusion hybride : score = alpha * dense + (1-alpha) * lexical, normalisés,
    # le tout pondéré par une pénalité de longueur (atténue les chunks courts).
    dense_scores = [1.0 - d for d in dists]  # cosine distance -> similarité
    lex_scores = [lexical_score(args.query, d) for d in docs]
 
    def norm(xs):
        lo, hi = min(xs), max(xs)
        return [(x - lo) / (hi - lo) if hi > lo else 0.5 for x in xs]
 
    dn, ln = norm(dense_scores), norm(lex_scores)
    # Le lexical n'est PAS renormalisé s'il est déjà borné [0,1] et informatif :
    # on garde sa valeur brute quand elle discrimine, sinon la normalisation
    # l'aplatirait. Ici on combine normalisé (dense) + brut borné (lexical).
    lex_raw = lex_scores  # déjà dans [0,1], interprétable tel quel
    pen = [length_penalty(d) for d in docs]
    hybrid = [
        pen[i] * (args.alpha * dn[i] + (1 - args.alpha) * lex_raw[i])
        for i in range(len(docs))
    ]
 
    ranked = sorted(range(len(docs)), key=lambda i: hybrid[i], reverse=True)[:args.k]
 
    print(f"\n🔎 Requête : {args.query}")
    print(f"   (hybride alpha={args.alpha}, k={args.k}"
          + (f", type={args.type}" if args.type else "") + ")\n")
    for rank, i in enumerate(ranked, 1):
        m = metas[i]
        flags = []
        if m.get("contient_code"):
            flags.append("CODE")
        if m.get("contient_tableau"):
            flags.append("TABLEAU")
        flag_str = f" [{'/'.join(flags)}]" if flags else ""
        print(f"— #{rank}  score={hybrid[i]:.3f}  "
              f"(dense={dn[i]:.2f}, lex={lex_raw[i]:.2f}, len×{pen[i]:.2f}){flag_str}")
        print(f"   source: {m['source']}  |  type: {m['type']}  |  "
              f"activité: {m['activite']}  séq: {m['sequence']}  langue: {m['langue']}")
        extrait = docs[i].replace("\n", " ").strip()
        print(f"   « {extrait[:280]}{'…' if len(extrait) > 280 else ''} »\n")
 
 
if __name__ == "__main__":
    main()
 
