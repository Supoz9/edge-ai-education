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
# On copie le code AVANT torch (voir explication dans la cible GPU).
COPY . .
# torch CPU-only : bien plus léger que la variante CUDA.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt
# Embedding sur CPU par défaut.
ENV RAG_DEVICE=cpu
# Conteneur "outil" : ne tourne pas en boucle, on l'invoque à la demande.
CMD ["python", "-c", "print('RAG (CPU) prêt. Utilisez: docker compose run rag python ingest.py'); import time; time.sleep(3600)"]
 
# ---------- Cible GPU ----------
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04 AS gpu
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/models_cache \
    DEBIAN_FRONTEND=noninteractive
WORKDIR /app
# Ubuntu 22.04 (base de l'image CUDA) fournit python3.10 — on demande donc
# "python3" (pas python3.12, absent des dépôts Jammy). 3.10 suffit pour ce code.
# python-is-python3 fait pointer "python" vers "python3" pour la commodité.
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip python-is-python3 build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
# IMPORTANT : on copie tout le code AVANT d'installer torch. Avec le legacy
# builder (BuildKit désactivé) et le multi-stage, un COPY placé en toute fin
# de stage peut ne pas être exécuté. Le placer ici garantit sa présence.
COPY . .
# torch CUDA (par défaut depuis PyPI, compatible CUDA 12.x).
RUN pip install --no-cache-dir torch \
    && pip install --no-cache-dir -r requirements.txt
ENV RAG_DEVICE=cuda
CMD ["python3", "-c", "print('RAG (GPU) prêt. Utilisez: docker compose run rag python ingest.py'); import time; time.sleep(3600)"]
 
