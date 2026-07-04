"""
search.py — 04/07/26 — @Supoz9 — v1.0

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
    """Score lexical simple type BM25-léger : recouvrement pondéré des termes.
    Complète le dense sur les correspondances exactes (IP, commandes, refs)."""
    def toks(s):
        return re.findall(r"[a-zA-Z0-9\.\-_/]+", s.lower())

    q = Counter(toks(query))
    d = Counter(toks(doc))
    if not q or not d:
        return 0.0
    inter = sum(min(q[t], d[t]) for t in q)
    # normalisation douce par la longueur du doc (évite de favoriser les longs)
    return inter / (1.0 + math.log(1 + sum(d.values())))


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

    # Fusion hybride : score = alpha * dense + (1-alpha) * lexical, normalisés.
    dense_scores = [1.0 - d for d in dists]  # cosine distance -> similarité
    lex_scores = [lexical_score(args.query, d) for d in docs]

    def norm(xs):
        lo, hi = min(xs), max(xs)
        return [(x - lo) / (hi - lo) if hi > lo else 0.5 for x in xs]

    dn, ln = norm(dense_scores), norm(lex_scores)
    hybrid = [args.alpha * dn[i] + (1 - args.alpha) * ln[i] for i in range(len(docs))]

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
              f"(dense={dn[i]:.2f}, lex={ln[i]:.2f}){flag_str}")
        print(f"   source: {m['source']}  |  type: {m['type']}  |  "
              f"activité: {m['activite']}  séq: {m['sequence']}  langue: {m['langue']}")
        extrait = docs[i].replace("\n", " ").strip()
        print(f"   « {extrait[:280]}{'…' if len(extrait) > 280 else ''} »\n")


if __name__ == "__main__":
    main()
