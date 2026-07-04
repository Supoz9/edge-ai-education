# Dockerfile — service RAG Edge-IA CIEL
#
# Deux cibles :
#   - "cpu" (par défaut) : image légère, torch CPU. Préserve la VRAM pour Ollama.
#   - "gpu"              : image CUDA, torch GPU. Ingestion plus rapide.
#
# Build CPU :  docker build --target cpu -t edge-rag:cpu ./rag
# Build GPU :  docker build --target gpu -t edge-rag:gpu ./rag
#
# En pratique on ne build pas à la main : docker-compose-rag.yml s'en charge
# et sélectionne la cible via la variable RAG_BUILD_TARGET (cpu|gpu).

# ---------- Base commune (dépendances applicatives) ----------
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/models_cache

WORKDIR /app

# Dépendances système minimales (pypdf n'a pas besoin de grand-chose).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# ---------- Cible CPU ----------
FROM base AS cpu
# torch CPU-only : bien plus léger que la variante CUDA.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt
COPY . .
# Embedding sur CPU par défaut.
ENV RAG_DEVICE=cpu
# Conteneur "outil" : ne tourne pas en boucle, on l'invoque à la demande
# (ingest / search). tail -f garde le conteneur vivant si lancé en service.
CMD ["python", "-c", "print('RAG (CPU) prêt. Utilisez: docker compose run rag python ingest.py'); import time; time.sleep(3600)"]

# ---------- Cible GPU ----------
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04 AS gpu
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/models_cache \
    DEBIAN_FRONTEND=noninteractive
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.12 python3-pip build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
# torch CUDA (par défaut depuis PyPI, compatible CUDA 12.x).
RUN pip install --no-cache-dir --break-system-packages torch \
    && pip install --no-cache-dir --break-system-packages -r requirements.txt
COPY . .
ENV RAG_DEVICE=cuda
CMD ["python3", "-c", "print('RAG (GPU) prêt. Utilisez: docker compose run rag python ingest.py'); import time; time.sleep(3600)"]
