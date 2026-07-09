# Module API + Open WebUI — Le tuteur en service
 
Ce module relie le pipeline RAG au chat **Open WebUI**, pour rendre le tuteur
maïeutique accessible aux élèves. Il comprend une **API FastAPI** (qui orchestre
recherche RAG + garde-fou + génération) et une **Pipe Function** (le pont vers
Open WebUI).
 
Ce document contient d'abord la **vision d'architecture**, puis le **mode
d'emploi réel** validé sur le rig.
 
---
 
## Architecture
 
```
   Élève (navigateur)
        │  message
        ▼
   ┌──────────────┐
   │  Open WebUI  │  (chat, comptes, rôles élève/prof)
   └──────┬───────┘
          │ Pipe Function (pipe_function.py, collée dans Open WebUI)
          │  = pont HTTP
          ▼
   ┌────────────────────────────────────────────┐
   │  API FastAPI (api.py, service Docker)      │
   │  1. reçoit la question                     │
   │  2. RECHERCHE hybride (garde-fou visibilité)│
   │  3. construit le prompt MAÏEUTIQUE +        │
   │     passages récupérés (prompts.py)         │
   │  4. appelle Ollama pour GÉNÉRER             │
   │  5. renvoie la réponse                      │
   └───────┬───────────────────────┬────────────┘
           ▼                       ▼
   ┌──────────────┐        ┌──────────────┐
   │   ChromaDB   │        │    Ollama    │
   │ (index ciel) │        │  (hôte:11434)│
   └──────────────┘        └──────────────┘
```
 
**Décision clé : l'API fait la récupération ET la génération.** Le prompt
maïeutique et le filtrage anti-triche vivent dans le code de l'API, pas dans la
config d'Open WebUI. Un élève ne peut pas contourner le garde-fou en bidouillant
un réglage d'interface. Open WebUI ne sert qu'à l'affichage, l'authentification
et la gestion des rôles.
 
### Fichiers
- `api.py` — le service FastAPI. Endpoints `POST /chat` et `GET /health`.
- `prompts.py` — **le cœur pédagogique** : le system prompt maïeutique. À itérer
  ici sans toucher au reste.
- `pipe_function.py` — la Pipe Function à coller dans Open WebUI.
- `test_maieutique.sh` — batterie de test du comportement (concepts / exercices /
  contournements).
- `retrieval.py` vit dans `rag/` (cœur de recherche partagé par la CLI et l'API).
---
 
## Prérequis
 
1. Le **module RAG fonctionne** et l'index est peuplé (voir `rag/README.md`).
   L'image `edge-rag:gpu` existe et contient le code.
2. **Ollama tourne sur l'hôte** et écoute sur toutes les interfaces (pas seulement
   127.0.0.1), sinon le conteneur API ne peut pas le joindre :
```bash
   sudo systemctl edit ollama
   # ajouter, dans la zone d'édition :
   #   [Service]
   #   Environment="OLLAMA_HOST=0.0.0.0:11434"
   sudo systemctl daemon-reload && sudo systemctl restart ollama
   # vérifier : sudo ss -tlnp | grep 11434  -> doit montrer *:11434
```
3. **Open WebUI tourne** (conteneur `open-webui`, port 3000).
---
 
## 1. Lancer l'API en service permanent
 
```bash
docker run -d --name tuteur-api --restart unless-stopped \
  --gpus '"device=1"' \
  --add-host=host.docker.internal:host-gateway \
  -p 8000:8000 \
  -v ~/Projets/edge-ai-education/rag:/app \
  -v ~/Projets/edge-ai-education/api-openwebui:/api \
  -v edge-ai-education_rag_chroma:/chroma \
  -v edge-ai-education_rag_models:/models_cache \
  -e RAG_DEVICE=cuda \
  -e RAG_CHROMA_DIR=/chroma \
  -e RAG_DIR=/app \
  -e HF_HUB_DISABLE_XET=1 \
  -e OLLAMA_URL=http://172.17.0.1:11434 \
  edge-rag:gpu \
  sh -c "cd /api && uvicorn api:app --host 0.0.0.0 --port 8000"
```
 
- `-d` : détaché (tourne en fond). `--restart unless-stopped` : redémarre au boot.
- `OLLAMA_URL=http://172.17.0.1:11434` : joint Ollama sur l'hôte via la passerelle
  Docker (l'API est dans un conteneur).
- `--gpus '"device=1"'` : embedding sur la 2060 Super (5060 Ti libre pour Ollama).
Vérifier :
```bash
docker ps --filter name=tuteur-api          # doit être "Up"
curl http://localhost:8000/health           # {"api":"ok","ollama":"ok",...}
```
 
Gérer le service : `docker logs tuteur-api --tail 30`, `docker restart tuteur-api`,
`docker stop tuteur-api`.
 
---
 
## 2. Installer la Pipe Function dans Open WebUI
 
1. Ouvrir Open WebUI, se connecter en **admin** (le 1er compte créé est admin).
2. **Admin Panel > Fonctions > +** (nouvelle fonction).
3. Coller tout le contenu de `pipe_function.py`. Nommer « Tuteur CIEL ». Sauver.
4. **Activer** la fonction (interrupteur).
La Pipe appelle l'API via `http://172.17.0.1:8000` (réglable dans les "Valves" de
la fonction). « Tuteur CIEL » apparaît alors dans le sélecteur de modèles.
 
---
 
## 3. Sécuriser les accès élève (ESSENTIEL)
 
Sans cette étape, un élève peut parler directement aux modèles bruts (qwen3…) et
**contourner tout le garde-fou**. Dans **Admin Panel > Réglages > Modèles** :
 
- **Tuteur CIEL → PUBLIC** (visible par tous les élèves).
- **qwen3 / gemma / mistral → PRIVÉ** (visibles par l'admin seulement).
Vérifier en se connectant avec un compte élève de test : le sélecteur ne doit
montrer **que** « Tuteur CIEL ».
 
---
 
## 4. Comptes
 
- **1er compte créé = admin/prof.** Créez-le en premier.
- Comptes élèves : création manuelle, ou inscription (Admin > Réglages) selon
  votre organisation.
- Astuce test : un compte « test-out » pour éprouver des questions hors corpus,
  un compte « test-corpus » pour le comportement strictement sur les cours.
---
 
## Tester le comportement maïeutique
 
Batterie automatique (concepts expliqués / exercices refusés / contournements
tenus) :
```bash
bash test_maieutique.sh          # API sur localhost:8000
```
 
---
 
## Invariants à préserver
 
- **Le garde-fou est double** : les corrigés sont exclus de l'index RAG (niveau
  récupération) ET le prompt maïeutique refuse de livrer les solutions (niveau
  comportement). Ne pas affaiblir l'un en pensant que l'autre suffit.
- **Les modèles bruts restent privés.** La sécurité des accès élève repose là-dessus.
- **Le prompt maïeutique** (`prompts.py`) est le cœur pédagogique : l'itérer avec
  soin, en testant via `test_maieutique.sh` après chaque changement.
---
 
## Améliorations à venir
 
- **Streaming** des réponses (mot à mot) pour une meilleure UX.
- **Reranker** (branche dédiée) si les mesures montrent un gain de pertinence.
- **Fine-tuning** maïeutique (branche dédiée) en dernier recours, si le prompt
  « fuit » malgré tout.
- Intégration de l'API à la stack **Docker Compose** (plutôt qu'un `docker run`).
 
