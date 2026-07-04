 Module RAG — Edge-IA CIEL

RAG autonome (indépendant du RAG natif d'Open WebUI) : **recherche hybride
dense + lexical** sur ChromaDB, avec embedding **BGE-M3** multilingue (FR/EN)
et un **garde-fou anti-triche** qui exclut les corrigés de l'index élève.

Conçu pour tourner **dans Docker**, en overlay de la stack existante (comme
l'overlay voix). Voir la conception détaillée dans
[RAG_INGESTION_SPEC.md](RAG_INGESTION_SPEC.md).

---

## Architecture

| Fichier                   | Rôle                                                        |
|---------------------------|-------------------------------------------------------------|
| `config.py`               | Tous les paramètres (pilotables par variables d'env)        |
| `chunking.py`             | Découpage par type + blocs CLI/tableaux **insécables**      |
| `ingest.py`               | PDF → chunks → embeddings → ChromaDB (+ garde-fou)          |
| `search.py`               | CLI de test de la recherche hybride                         |
| `Dockerfile`              | Image du service, cibles **cpu** (défaut) et **gpu**        |
| `docker-compose-rag.yml`  | Overlay ajoutant le service `rag` à la stack                |
| `requirements.txt`        | Dépendances Python                                           |

Le **corpus** (`corpus_ciel/`, à la racine du projet) est monté en lecture
seule. L'**index Chroma** et le **cache du modèle** persistent dans des volumes
Docker nommés (survivent aux redémarrages).

---

## Prérequis

- La stack de base tourne (`infra/docker-compose.yml` : Ollama + Open WebUI).
- Le corpus est rangé et nommé selon la convention (voir
  `corpus_ciel/README.md`). **Les corrigés sont bien dans `05_` / `06_`.**
- Les commandes se lancent depuis la **racine du projet**.

---

## Utilisation (CPU par défaut)

**1. Construire l'image du service RAG**
```bash
docker compose -f infra/docker-compose.yml -f rag/docker-compose-rag.yml build rag
```

**2. Ingérer le corpus** (première fois, ou après ajout de documents)
```bash
docker compose -f infra/docker-compose.yml -f rag/docker-compose-rag.yml \
  run --rm rag python ingest.py
```
- Ajout incrémental : relancez simplement `ingest.py`, ChromaDB fait un `upsert`.
- Repartir de zéro : `... run --rm rag python ingest.py --reset`.
- Voir le plan sans rien écrire : `... run --rm rag python ingest.py --dry-run`.

**3. Tester la recherche** (votre outil de mise au point)
```bash
docker compose -f infra/docker-compose.yml -f rag/docker-compose-rag.yml \
  run --rm rag python search.py "comment configurer un pool DHCP ?"

# filtrer par type, ajuster le nombre de résultats ou le poids hybride :
... run --rm rag python search.py "tension alimentation GP2Y0A41" --k 3
... run --rm rag python search.py "VLAN" --type cours --alpha 0.6
```

---

## Passer l'embedding sur GPU

Par défaut l'embedding tourne sur **CPU** (préserve la VRAM pour les modèles
Ollama ; l'ingestion est ponctuelle, donc la lenteur CPU est acceptable).

Pour utiliser le **GPU** (ingestion plus rapide) :
1. Décommentez la section `deploy.resources` dans `docker-compose-rag.yml`.
2. Lancez avec les variables :
```bash
RAG_BUILD_TARGET=gpu RAG_DEVICE=cuda \
  docker compose -f infra/docker-compose.yml -f rag/docker-compose-rag.yml build rag
RAG_BUILD_TARGET=gpu RAG_DEVICE=cuda \
  docker compose -f infra/docker-compose.yml -f rag/docker-compose-rag.yml \
  run --rm rag python ingest.py
```

---

## Le garde-fou anti-triche (rappel)

- Les documents de `05_corriges/` et `06_coups_de_pouce/` sont **exclus** de la
  collection interrogeable (`ciel`). Ils ne peuvent donc **jamais** remonter
  dans une recherche élève. C'est la « stratégie simple » de la spec (§5).
- Double sécurité : si un fichier `..._corrige.pdf` est rangé par erreur dans un
  dossier « libre » (ou l'inverse), l'ingestion **refuse** ce fichier et le
  signale, au lieu de risquer une fuite.

---

## OCR (PDF scannés)

`ingest.py` extrait le texte natif des PDF. Si un PDF est un **scan** (image),
aucun texte n'est extrait et un avertissement s'affiche. Il faut alors l'OCR-iser
en amont (par ex. `ocrmypdf entrée.pdf sortie.pdf`) puis replacer la version
océrisée dans le corpus. L'OCR n'est volontairement pas fait ici pour garder
l'image du service légère.

---

## Prochaine étape : brancher à Open WebUI

Cette CLI valide la *récupération*. L'étape suivante sera une petite **API**
(FastAPI) exposant la recherche, que l'on connectera à Open WebUI pour que les
élèves en bénéficient — la génération de réponse passera alors par Ollama
(`http://ollama:11434`, déjà câblé dans l'environnement du service). À faire
une fois la qualité de récupération jugée satisfaisante sur de vraies questions.
