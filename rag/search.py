"""
search.py — @Supoz9 — v2.0

CLI de test de la recherche RAG (hybride dense + lexical).

Outil de mise au point pour VOUS (pas l'interface élève). Il s'appuie sur
retrieval.py, le même cœur de recherche que l'API utilisera — garantissant que
ce que vous testez ici est exactement ce que les élèves obtiendront.
 
Usage :
    python search.py "comment configurer un pool DHCP ?"
    python search.py "tension alimentation GP2Y0A41" --k 3
    python search.py "VLAN" --type cours
"""
 
import argparse
 
import config
from retrieval import search_passages
 
 
def main():
    ap = argparse.ArgumentParser(description="Recherche RAG hybride (test CLI)")
    ap.add_argument("query", help="la question à poser au RAG")
    ap.add_argument("--k", type=int, default=config.TOP_K, help="nombre de résultats")
    ap.add_argument("--type", default=None,
                    help="filtre par type : cours|tp|datasheet|referentiel")
    ap.add_argument("--alpha", type=float, default=config.HYBRID_ALPHA,
                    help="poids dense vs lexical (0..1)")
    args = ap.parse_args()
 
    try:
        passages = search_passages(args.query, k=args.k, doc_type=args.type,
                                   alpha=args.alpha)
    except Exception as e:
        print(f"Erreur : {e}\nL'index est-il peuplé ? (`python ingest.py`)")
        return
 
    if not passages:
        print("Aucun résultat. L'index est-il peuplé ? (`python ingest.py`)")
        return
 
    print(f"\n🔎 Requête : {args.query}")
    print(f"   (hybride alpha={args.alpha}, k={args.k}"
          + (f", type={args.type}" if args.type else "") + ")\n")
    for rank, p in enumerate(passages, 1):
        flags = []
        if p.contient_code:
            flags.append("CODE")
        if p.contient_tableau:
            flags.append("TABLEAU")
        flag_str = f" [{'/'.join(flags)}]" if flags else ""
        print(f"— #{rank}  score={p.score:.3f}  "
              f"(dense={p.dense:.2f}, lex={p.lexical:.2f}){flag_str}")
        print(f"   source: {p.source}  |  type: {p.type}  |  "
              f"activité: {p.activite}  séq: {p.sequence}  langue: {p.langue}")
        extrait = p.text.replace("\n", " ").strip()
        print(f"   « {extrait[:280]}{'…' if len(extrait) > 280 else ''} »\n")
 
 
if __name__ == "__main__":
    main()
 
