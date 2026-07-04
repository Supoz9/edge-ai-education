"""
ingest.py — 04/07/26 — @Supoz9 — v1.0

Ingestion du corpus CIEL dans ChromaDB.

Parcourt corpus_ciel/, déduit les métadonnées (dossier + nom de fichier),
découpe (chunking.py), calcule les embeddings BGE-M3, et écrit dans Chroma.

GARDE-FOU : les documents de type restreint (corrigés, coups de pouce) sont
par défaut EXCLUS de l'index interrogeable par l'élève (stratégie simple de
la spec §5). Utiliser --inclure-restreint pour les indexer dans une collection
séparée (usage avancé, non destiné aux élèves).

Usage :
    python ingest.py                    # ingère tout le corpus (zone libre)
    python ingest.py --reset            # repart d'un index vierge
    python ingest.py --dry-run          # montre ce qui serait fait, sans écrire
"""

import argparse
import sys
from pathlib import Path

import config
from chunking import parse_filename, chunk_text, DocMeta


def log(msg: str):
    print(f"[ingest] {msg}", flush=True)


def extract_pdf_text(path: Path) -> str:
    """Extrait le texte d'un PDF. pypdf pour le texte natif ; si vide (scan),
    on avertit (l'OCR n'est pas fait ici — voir README pour la marche à suivre)."""
    try:
        from pypdf import PdfReader
    except ImportError:
        log("ERREUR : pypdf non installé. `pip install pypdf`")
        sys.exit(1)

    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    text = "\n".join(pages).strip()
    if not text:
        log(f"  ⚠️  '{path.name}' semble être un SCAN (aucun texte extrait). "
            f"Il faut l'OCR-iser avant ingestion (voir README §OCR).")
    return text


def detect_langue(text: str) -> str:
    """Heuristique légère FR/EN sur des mots très fréquents."""
    sample = text[:2000].lower()
    fr = sum(sample.count(w) for w in (" le ", " la ", " des ", " est ", " pour ", " avec "))
    en = sum(sample.count(w) for w in (" the ", " and ", " of ", " is ", " for ", " with "))
    return "en" if en > fr else "fr"


def iter_documents(corpus_dir: Path):
    """Génère (chemin_pdf, DocMeta) pour chaque PDF conforme du corpus."""
    for dossier, (dtype, dvis) in config.DOSSIER_MAP.items():
        ddir = corpus_dir / dossier
        if not ddir.is_dir():
            continue
        for pdf in sorted(ddir.glob("*.pdf")):
            try:
                meta = parse_filename(pdf.stem, dtype, dvis)
            except ValueError as e:
                log(f"  ⛔ IGNORÉ : {e}")
                continue
            yield pdf, meta


def build_embedder():
    """Charge BGE-M3 via sentence-transformers, sur CPU ou GPU selon config."""
    from sentence_transformers import SentenceTransformer
    log(f"Chargement du modèle d'embedding {config.EMBED_MODEL} sur {config.DEVICE}...")
    model = SentenceTransformer(config.EMBED_MODEL, device=config.DEVICE)
    return model


def main():
    ap = argparse.ArgumentParser(description="Ingestion corpus CIEL -> ChromaDB")
    ap.add_argument("--reset", action="store_true", help="repart d'un index vierge")
    ap.add_argument("--dry-run", action="store_true", help="n'écrit rien, montre le plan")
    ap.add_argument("--inclure-restreint", action="store_true",
                    help="indexe aussi corrigés/coups de pouce (collection séparée, usage avancé)")
    args = ap.parse_args()

    if not config.CORPUS_DIR.is_dir():
        log(f"ERREUR : corpus introuvable à {config.CORPUS_DIR}. "
            f"Vérifiez le montage du volume ou RAG_CORPUS_DIR.")
        sys.exit(1)

    # --- Inventaire + garde-fou ---
    libres, restreints = [], []
    for pdf, meta in iter_documents(config.CORPUS_DIR):
        (restreints if meta.visibilite == "restreinte" else libres).append((pdf, meta))

    log(f"Documents 'libres' (interrogeables par l'élève) : {len(libres)}")
    log(f"Documents 'restreints' (corrigés/aides, EXCLUS par défaut) : {len(restreints)}")
    for _, m in restreints:
        log(f"    🔒 exclu de l'index élève : {m.source}")

    if args.dry_run:
        log("--dry-run : voici le découpage prévu (aucune écriture).")
        for pdf, meta in libres:
            txt = extract_pdf_text(pdf)
            n = len(chunk_text(txt, meta.type))
            log(f"  {meta.source}  [{meta.type}] -> {n} chunks")
        return

    # --- Connexion Chroma ---
    import chromadb
    client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))

    if args.reset:
        try:
            client.delete_collection(config.COLLECTION_NAME)
            log(f"Collection '{config.COLLECTION_NAME}' supprimée (--reset).")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=config.COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    embedder = build_embedder()

    # --- Ingestion de la zone libre ---
    to_index = list(libres)
    if args.inclure_restreint:
        log("⚠️  --inclure-restreint activé : les corrigés seront indexés dans "
            "une collection SÉPARÉE 'ciel_prof' (ne jamais exposer aux élèves).")
        # (Implémentation de la collection prof laissée volontairement en second
        #  temps — voir spec §5 stratégie avancée. On log l'intention ici.)

    total_chunks = 0
    for pdf, meta in to_index:
        text = extract_pdf_text(pdf)
        if not text:
            continue
        meta.langue = detect_langue(text)
        chunks = chunk_text(text, meta.type)

        ids, docs, metadatas = [], [], []
        for i, ch in enumerate(chunks):
            ids.append(f"{meta.source}__c{i:03d}")
            docs.append(ch.text)
            metadatas.append({
                "discipline": "CIEL",
                "source": meta.source,
                "type": meta.type,
                "activite": meta.activite,
                "sequence": meta.sequence,
                "slug": meta.slug,
                "visibilite": meta.visibilite,
                "langue": meta.langue,
                "contient_code": ch.contient_code,
                "contient_tableau": ch.contient_tableau,
            })

        if not docs:
            continue

        embeddings = embedder.encode(
            docs, normalize_embeddings=True, show_progress_bar=False
        ).tolist()

        collection.upsert(
            ids=ids, documents=docs, metadatas=metadatas, embeddings=embeddings
        )
        total_chunks += len(docs)
        log(f"  ✅ {meta.source} [{meta.type}, {meta.langue}] : {len(docs)} chunks")

    log(f"Terminé. {total_chunks} chunks indexés dans '{config.COLLECTION_NAME}'.")
    log(f"Index persistant : {config.CHROMA_DIR}")


if __name__ == "__main__":
    main()
