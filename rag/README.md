 # Module RAG — Edge-IA CIEL
 
RAG autonome (indépendant du RAG natif d'Open WebUI) : **recherche hybride
dense + lexical** sur ChromaDB, avec embedding **BGE-M3** multilingue (FR/EN)
et un **garde-fou anti-triche** qui exclut les corrigés de l'index élève.
 
Conçu pour tourner **dans Docker**. Voir la conception détaillée dans
[RAG_INGESTION_SPEC.md](RAG_INGESTION_SPEC.md).
 
> ⚠️ **À LIRE AVANT DE COMMENCER — spécificités de ce déploiement.**
> Ce module a été mis au point sur un rig réel (Ubuntu Server + 2 GPU) et
> plusieurs contournements se sont révélés nécessaires. Ils sont **indispensables** :
> sans eux, le build ou l'ingestion échouent. Chaque commande ci-dessous les
> intègre déjà. La section [« Pièges connus »](#pièges-connus-et-pourquoi-ces-contournements)
> en fin de document explique le *pourquoi* de chacun.
>
> En résumé : on **build avec `DOCKER_BUILDKIT=0`**, on **lance en `docker run`
> direct** (pas `docker compose run`), et on ajoute **`HF_HUB_DISABLE_XET=1`**
> pour le téléchargement du modèle.
 
---
 
## Architecture
 
| Fichier                   | Rôle                                                        |
|---------------------------|-------------------------------------------------------------|
| `config.py`               | Tous les paramètres (pilotables par variables d'env)        |
| `chunking.py`             | Découpage par sections + blocs CLI/tableaux insécables      |
| `ingest.py`               | PDF vers chunks vers embeddings vers ChromaDB (+ garde-fou) |
| `search.py`               | CLI de test de la recherche hybride                         |
| `Dockerfile`              | Image du service, cibles cpu (défaut) et gpu                |
| `docker-compose-rag.yml`  | Overlay Compose (usage futur, cf. pièges)                   |
| `requirements.txt`        | Dépendances Python                                          |
 
Le **corpus** (`corpus_ciel/`, à la racine du projet) est monté en lecture
seule. L'**index Chroma** et le **cache du modèle** persistent dans des volumes
Docker nommés (survivent aux redémarrages).
 
---
 
## Prérequis (installés une fois)
 
1. **Docker + Docker Compose V2.** Vérifier : `docker compose version`.
   Si absent : `sudo apt-get install docker-compose-v2`.
2. **NVIDIA Container Toolkit** (pour l'embedding GPU). Vérifier :
   `docker info | grep -i runtime` doit lister `nvidia`. Sinon :
```bash
   curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
     sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
     && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
     sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
     sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
   sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
   sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker
```
   Tester : `docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi`.
3. **Corpus rangé** selon la convention (voir `corpus_ciel/README.md`).
   Les corrigés et coups de pouce sont bien dans `05_` / `06_`.
4. **Utilisateur dans le groupe docker** (pour éviter `sudo`) :
   `sudo usermod -aG docker $USER` puis reconnexion.
 
Toutes les commandes se lancent **depuis la racine du projet**.
 
---
 
## Procédure GPU (recommandée sur ce rig)
 
L'embedding tourne sur la **RTX 2060 Super (GPU 1)**, laissant la **RTX 5060 Ti
(GPU 0)** libre pour les modèles Ollama. Voir [« Répartition GPU »](#répartition-gpu).
 
### 1. Construire l'image GPU
 
```bash
DOCKER_BUILDKIT=0 docker build --target gpu -t edge-rag:gpu ./rag
```
 
> Le premier build télécharge l'image CUDA et torch CUDA (~2-3 Go). Long **une
> fois**. `DOCKER_BUILDKIT=0` est **obligatoire** (voir pièges).
 
Vérifier que l'image contient bien le code :
```bash
docker run --rm edge-rag:gpu ls /app     # doit lister ingest.py, chunking.py...
```
 
### 2. Ingérer le corpus
 
```bash
docker run --rm --gpus '"device=1"' \
  -v ~/Projets/edge-ai-education/corpus_ciel:/corpus:ro \
  -v edge-ai-education_rag_chroma:/chroma \
  -v edge-ai-education_rag_models:/models_cache \
  -e RAG_DEVICE=cuda \
  -e RAG_CORPUS_DIR=/corpus \
  -e RAG_CHROMA_DIR=/chroma \
  -e HF_HUB_DISABLE_XET=1 \
  edge-rag:gpu python ingest.py
```
 
> Le premier lancement télécharge **BGE-M3** (~2 Go, mis en cache ensuite).
> `HF_HUB_DISABLE_XET=1` est **obligatoire** sinon le téléchargement se fige.
> Options : `--dry-run` (plan sans écriture), `--reset` (index vierge).
> Ajouter des documents = relancer `ingest.py` (ChromaDB fait un `upsert`).
 
### 3. Tester la recherche
 
```bash
docker run --rm --gpus '"device=1"' \
  -v edge-ai-education_rag_chroma:/chroma \
  -v edge-ai-education_rag_models:/models_cache \
  -e RAG_DEVICE=cuda \
  -e RAG_CHROMA_DIR=/chroma \
  -e HF_HUB_DISABLE_XET=1 \
  edge-rag:gpu python search.py "à quoi sert une boucle pour automatiser ?"
 
# options : --k 3 (nb résultats), --type cours|tp|referentiel, --alpha 0.6
```
 
---
 
## Procédure CPU (matériel sans GPU dédié)
 
Pour un utilisateur sans GPU à consacrer à l'embedding. Plus lent à l'ingestion
mais aucune VRAM consommée. Remplacer la cible et le device :
 
```bash
DOCKER_BUILDKIT=0 docker build --target cpu -t edge-rag:cpu ./rag
 
docker run --rm \
  -v ~/Projets/edge-ai-education/corpus_ciel:/corpus:ro \
  -v edge-ai-education_rag_chroma:/chroma \
  -v edge-ai-education_rag_models:/models_cache \
  -e RAG_DEVICE=cpu \
  -e RAG_CORPUS_DIR=/corpus \
  -e RAG_CHROMA_DIR=/chroma \
  -e HF_HUB_DISABLE_XET=1 \
  edge-rag:cpu python ingest.py
```
 
> Sur un CPU d'entrée de gamme, l'ingestion peut être très lente. Comme c'est
> une opération ponctuelle, c'est acceptable.
 
---
 
## Répartition GPU
 
Sur un rig à deux cartes, l'embedding et l'inférence sont deux charges séparées
qu'on place sur des cartes différentes pour qu'elles ne se disputent pas la VRAM.
 
- **Principe** (réutilisable) : `--gpus '"device=N"'` cible la carte N pour
  l'embedding. Cohérent avec le concept « un modèle par carte ».
- **Sur ce rig** : embedding sur la **2060 Super (device=1)**, ce qui laisse la
  **5060 Ti 16 Go (device=0)** entièrement disponible pour les modèles Ollama.
- **Autre matériel** : changez le numéro (`device=0`) ou passez en procédure CPU.
Vérifier pendant l'ingestion, dans un 2e terminal : `watch -n 1 nvidia-smi` —
la mémoire doit monter sur le GPU visé, pas sur l'autre.
 
---
 
## Le garde-fou anti-triche
 
- Les documents de `05_corriges/` et `06_coups_de_pouce/` sont **exclus** de la
  collection interrogeable (`ciel`). Ils ne peuvent donc **jamais** remonter
  dans une recherche élève. C'est la « stratégie simple » de la spec (§5).
- Double sécurité : si un fichier `..._corrige.pdf` est rangé par erreur dans un
  dossier « libre » (ou l'inverse), l'ingestion **refuse** ce fichier et le
  signale, au lieu de risquer une fuite.
- Vérifiable à l'ingestion : les documents restreints sont listés avec 🔒.
---
 
## Notes sur la qualité de récupération
 
- **Chunking par sections** : les cours/TP sont découpés sur leurs sections
  numérotées (`1.`, `2.`, `Phase 3`…). Les blocs de commandes CLI et les
  tableaux restent **insécables** (jamais coupés en deux).
- **Recherche hybride** : combine le score sémantique (BGE-M3) et un score
  lexical (proportion des mots de la question présents dans le passage). Le
  lexical rattrape les termes exacts (commandes, IP, références) que le
  sémantique lisse.
- **Pénalité de longueur** : les chunks très courts sont atténués pour ne pas
  polluer le haut du classement.
- **Registre des requêtes** : BGE-M3 est meilleur sur des **questions en langage
  naturel** (« à quoi sert X ») que sur des suites de mots-clés. C'est cohérent
  avec l'usage réel (élèves qui posent des questions à un tuteur).
- **Code en capture d'écran** : le code présent sous forme d'image dans certains
  PDF n'est pas extrait (pypdf ne lit que le texte natif). Les consignes autour
  le sont. Acceptable et cohérent avec le principe anti-triche.
---
 
## Pièges connus (et pourquoi ces contournements)
 
Ces points ont coûté du temps à diagnostiquer ; les documenter évite de les revivre.
 
**1. `DOCKER_BUILDKIT=0` obligatoire au build.**
BuildKit (le builder moderne) est mal configuré sur ce rig (buildx non installé),
ce qui produit un **contexte de build vide** : `COPY . .` ne copie alors que
`requirements.txt`, et le conteneur n'a pas les scripts (`can't open file
'/app/ingest.py'`). Le builder classique (`DOCKER_BUILDKIT=0`) copie
correctement. *Alternative propre à terme : installer `docker-buildx-plugin`.*
 
**2. Lancer en `docker run` direct, pas `docker compose run`.**
`docker compose run` tente de reconstruire l'image via BuildKit au lancement, ce
qui recasse le `/app`. On lance donc l'image déjà construite directement avec
`docker run`. *(Le fichier `docker-compose-rag.yml` reste fourni pour référence
et pour un usage futur une fois BuildKit réparé.)*
 
**3. `HF_HUB_DISABLE_XET=1` obligatoire à l'ingestion.**
Le protocole de téléchargement « Xet » de Hugging Face se fige sur ce réseau ;
le modèle BGE-M3 ne se télécharge jamais (bloqué sur « Chargement du modèle... »).
Désactiver Xet force le téléchargement HTTP classique, qui aboutit.
 
**4. `COPY . .` avant `pip install torch` dans le Dockerfile.**
Avec le builder classique et le multi-stage, un `COPY` placé en toute fin de
stage peut ne pas être exécuté. On copie donc le code **avant** torch. (Déjà
corrigé dans le Dockerfile ; ne pas réinverser.)
 
**5. Warning `version is obsolete` sur `infra/docker-compose.yml`.**
Sans gravité (vieille clé `version:` ignorée par Compose V2).
 
**6. Messages `Failed to send telemetry event`.**
Sans gravité : ChromaDB n'arrive pas à envoyer ses statistiques anonymes.
N'affecte ni l'ingestion ni la recherche.
 
---
 
## Prochaine étape : brancher à Open WebUI
 
Cette CLI valide la *récupération*. L'étape suivante sera une petite **API**
(FastAPI) exposant la recherche, connectée à Open WebUI pour que les élèves en
bénéficient — la génération de réponse passera alors par Ollama
(`http://ollama:11434`). À faire une fois la qualité de récupération jugée
satisfaisante. Une expérimentation **reranker** (branche dédiée) est aussi
envisagée pour resserrer la pertinence sur les requêtes faibles.
 
