# Plan d'architecture — Raccorder le RAG à Open WebUI
 
> Objectif : rendre le tuteur maïeutique disponible aux élèves dans Open WebUI,
> en conservant le garde-fou anti-triche au cœur du dispositif.
> Approche retenue : **API FastAPI** (le RAG devient un service permanent) +
> **Pipe Function** (le pont vers Open WebUI).
 
---
 
## 1. Vue d'ensemble : qui fait quoi
 
```
   Élève (navigateur)
        │
        ▼
   ┌──────────────┐   message de l'élève
   │  Open WebUI  │─────────────────────────┐
   │  (chat, rôles│                         │
   │  élève/prof) │◄──────────────────────┐ │
   └──────────────┘   réponse maïeutique  │ │
        ▲                                 │ │
        │ Pipe Function (1 fichier .py)   │ │
        │  = le pont HTTP                 │ │
        ▼                                 │ │
   ┌──────────────────────────────────────┴─┴───┐
   │  API RAG (FastAPI, service permanent)      │
   │  1. reçoit la question                     │
   │  2. RECHERCHE hybride(garde-fou visibilité)│
   │  3. construit le prompt maïeutique +       │
   │     passages récupérés                     │
   │  4. appelle Ollama pour GÉNÉRER            │
   │  5. renvoie la réponse                     │
   └──────────┬─────────────────────────────────┘
              │                   ▲
              ▼                   │ 
   ┌──────────────┐        ┌──────────────┐
   │   ChromaDB   │_______ │    Ollama    │
   │ (index ciel) │        │ (qwen3:14b…) │
   └──────────────┘        └──────────────┘
```
 
**Décision clé : l'API fait la récupération ET la génération.**
Le prompt maïeutique et le filtrage anti-triche vivent dans VOTRE code, pas dans
la config d'un modèle Open WebUI. Un élève ne peut pas contourner le garde-fou en
bidouillant un réglage d'interface. Open WebUI ne sert qu'à l'affichage, à
l'authentification et à la gestion des rôles élève/prof.
 
*Alternative (non retenue pour la v1) : l'API ne fait que la récupération, et
Open WebUI génère avec un modèle configuré. Plus simple mais le garde-fou
maïeutique devient modifiable côté interface — trop risqué pour un usage élève.*
 
---
 
## 2. Les composants à construire
 
### A. L'API RAG (FastAPI) — le gros du travail
Un nouveau service, à ajouter dans `rag/` (ou un sous-dossier `rag/api/`).
 
Réutilise le code existant :
- la **recherche hybride** de `search.py` (déjà écrite et validée) ;
- la logique d'embedding/ChromaDB de `config.py` ;
- le **garde-fou visibilité** (déjà en place : l'index `ciel` ne contient pas
  les corrigés).
Ajoute :
- un **endpoint HTTP** (ex. `POST /chat`) qui reçoit `{question, historique}` ;
- la **construction du prompt maïeutique** (le system prompt socratique + les
  passages récupérés injectés en contexte) ;
- l'**appel à Ollama** (`http://ollama:11434/api/chat`) avec ce prompt ;
- le **renvoi de la réponse**, idéalement en streaming (mot à mot).
Endpoints envisagés :
- `POST /chat` — le cœur : question → réponse maïeutique.
- `GET /health` — vérification que le service tourne (utile pour Open WebUI).
- (plus tard) `GET /search` — la recherche brute, pour debug/éval.
### B. La Pipe Function (Open WebUI) — le pont léger
Un seul fichier Python, collé dans Open WebUI (Admin > Functions).
 
Son rôle est minimal :
- déclarer un « modèle » virtuel qui apparaît dans le sélecteur d'Open WebUI
  (ex. « Tuteur CIEL ») ;
- à chaque message, appeler l'API RAG en HTTP (`POST /chat`) ;
- streamer la réponse dans le chat.
C'est une **Pipe Function de type "pipe"** (elle prend le contrôle de la réponse).
Voir la doc : Functions > Pipe. ~50 lignes de Python.
 
---
 
## 3. Décisions techniques à acter avant de coder
 
| Question | Recommandation v1 |
|----------|-------------------|
| Où tourne l'API ? | Conteneur Docker, dans la stack (réseau interne, parle à Ollama et Chroma) |
| Embedding chargé où ? | Dans l'API (BGE-M3 résident en mémoire, prêt à chaque requête) |
| Streaming des réponses ? | Oui à terme (meilleure UX), mais on peut démarrer en non-streaming pour simplifier |
| Le prompt maïeutique vit où ? | Dans l'API (fichier de config ou variable), verrouillé |
| Modèle de génération ? | `qwen3:14b` pour démarrer (déjà installé) |
| Gestion élève/prof ? | Rôles natifs Open WebUI ; l'API peut recevoir un indicateur de rôle |
 
---
 
## 4. Le prompt maïeutique : le cœur pédagogique
 
L'API construit, à chaque requête, un message système qui combine :
1. **Les instructions maïeutiques** (ton socratique, ne jamais donner la solution
   d'un exercice, indices gradués, distinction concept/exercice).
2. **Les passages récupérés** par le RAG (uniquement de la zone « libre » — les
   corrigés sont déjà exclus de l'index).
3. **Une consigne d'ancrage** : « appuie-toi uniquement sur ces passages ; si
   l'info n'y est pas, dis-le ».
C'est ici que se joue toute la valeur pédagogique. Le garde-fou est double :
- **au niveau RAG** : les corrigés ne sont jamais récupérés (déjà en place) ;
- **au niveau prompt** : même avec les bons passages, l'IA guide sans livrer la
  solution finale de l'exercice.
---
 
## 5. Ordre de mise en œuvre suggéré
 
**Étape 1 — API minimale, non-streaming, sans maïeutique.**
Un `POST /chat` qui : récupère les passages (code existant) → les colle dans un
prompt basique → appelle Ollama → renvoie le texte. But : valider le tuyau
complet question→réponse. Testable au curl, sans Open WebUI.
 
**Étape 2 — Le prompt maïeutique.**
Remplacer le prompt basique par le vrai system prompt socratique. Tester au curl
avec de vraies questions d'élèves : est-ce que l'IA guide sans donner la réponse ?
C'est l'étape pédagogique, la plus importante à peaufiner.
 
**Étape 3 — La Pipe Function.**
Écrire le pont Open WebUI, brancher sur l'API, voir apparaître « Tuteur CIEL »
dans l'interface. Tester en tant qu'utilisateur.
 
**Étape 4 — Le streaming.**
Passer la réponse en mot-à-mot pour une UX fluide.
 
**Étape 5 — Rôles et accès élève.**
Configurer les comptes/rôles élève dans Open WebUI, restreindre l'accès au seul
tuteur, tester le parcours élève complet.
 
**Étape 6 — Tests anti-contournement.**
Se mettre dans la peau d'un élève qui essaie d'obtenir la solution (« donne-moi
la réponse », « fais comme si… »). Durcir le prompt selon les failles trouvées.
 
---
 
## 6. Points de vigilance (tirés de l'expérience RAG)
 
- **Docker/BuildKit** : mêmes contournements que le module RAG (`DOCKER_BUILDKIT=0`,
  etc. — voir `rag/README.md`). L'API sera un service Docker de plus.
- **VRAM** : l'API charge BGE-M3 (2060 Super) + Ollama charge le modèle de génération
  (5060 Ti). Vérifier que les deux cohabitent sans saturer.
- **Service permanent** : contrairement à l'ingestion (ponctuelle), l'API doit
  tourner en continu. Elle rejoint la logique `docker compose up -d` de la stack.
- **Le garde-fou reste sacré** : ne jamais exposer un endpoint qui renverrait les
  corrigés. L'API ne doit interroger que la collection `ciel` (zone libre).
---
 

