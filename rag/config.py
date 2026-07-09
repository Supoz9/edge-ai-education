"""
config.py — @author: supoz9 — v1.0

Paramètres centraux du module RAG Edge-IA CIEL.

Tout est pilotable par variables d'environnement pour rester containerisable
et partageable sans toucher au code. Les valeurs par défaut conviennent à un
déploiement standard (corpus monté dans le conteneur, embedding sur CPU).
"""

import os
from pathlib import Path

# --- Chemins -----------------------------------------------------------------
# Dans le conteneur, le corpus est monté en lecture seule sur /corpus
# et l'index Chroma persiste sur /chroma (volume nommé).
CORPUS_DIR = Path(os.environ.get("RAG_CORPUS_DIR", "/corpus"))
CHROMA_DIR = Path(os.environ.get("RAG_CHROMA_DIR", "/chroma"))

# --- Modèle d'embedding ------------------------------------------------------
# BGE-M3 : multilingue (FR + EN), produit dense ET lexical (sparse) en une passe.
EMBED_MODEL = os.environ.get("RAG_EMBED_MODEL", "BAAI/bge-m3")

# Bascule CPU / GPU. Par défaut CPU (préserve la VRAM pour les modèles Ollama).
# Mettre RAG_DEVICE=cuda pour utiliser le GPU (ingestion plus rapide).
DEVICE = os.environ.get("RAG_DEVICE", "cpu")

# --- Collection Chroma -------------------------------------------------------
COLLECTION_NAME = os.environ.get("RAG_COLLECTION", "ciel")

# --- Recherche hybride -------------------------------------------------------
# Poids relatif dense vs lexical dans la fusion des scores (0..1).
# 0.5 = équilibré. Plus haut = favorise le sémantique ; plus bas = le lexical.
HYBRID_ALPHA = float(os.environ.get("RAG_HYBRID_ALPHA", "0.5"))

# Nombre de passages remontés par défaut.
TOP_K = int(os.environ.get("RAG_TOP_K", "5"))

# --- Garde-fou anti-triche ---------------------------------------------------
# Types de documents JAMAIS servis à l'élève (exclus de l'index interrogeable).
# Voir RAG_INGESTION_SPEC.md §5, stratégie simple.
VISIBILITE_RESTREINTE = {"corrige", "coup-de-pouce"}

# Correspondance dossier -> (type, visibilite)
# Le type est REVALIDÉ contre le suffixe du nom de fichier (double sécurité).
DOSSIER_MAP = {
    "01_referentiel":   ("referentiel",   "libre"),
    "02_cours":         ("cours",         "libre"),
    "03_tp_enonces":    ("tp",            "libre"),
    "04_datasheets":    ("datasheet",     "libre"),
    "05_corriges":      ("corrige",       "restreinte"),
    "06_coups_de_pouce":("coup-de-pouce", "restreinte"),
}

# --- Chunking ----------------------------------------------------------------
# Taille cible d'un chunk en caractères (approximatif, le découpage respecte
# d'abord les frontières structurelles). Les blocs insécables (CLI, tableaux)
# ne sont jamais coupés même s'ils dépassent.
CHUNK_TARGET_CHARS = int(os.environ.get("RAG_CHUNK_CHARS", "1200"))
CHUNK_OVERLAP_CHARS = int(os.environ.get("RAG_CHUNK_OVERLAP", "150"))
