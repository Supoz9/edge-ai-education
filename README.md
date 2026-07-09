# Edge-AI-Education : L'IA souveraine, frugale et maïeutique au Lycée

[![Souveraineté](https://img.shields.io/badge/RGPD-100%25_Local-green.svg)](#)
[![OS](https://img.shields.io/badge/OS-Debian_13-blue.svg)](#)
[![Licence](https://img.shields.io/badge/Licence-MIT-orange.svg)](#)

Ce projet propose une alternative concrète et opérationnelle à la centralisation des méga-modèles d'IA générative en nuage (Cloud). Déployée avec succès au laboratoire CIEL du Lycée Claude Chappe (Arnage), cette architecture repose sur le concept de **"Rigs" de calcul distribués par discipline**. Elle permet d'exécuter des modèles d'IA légers, ultra-spécialisés et totalement autonomes, directement dans la salle de cours.

> ℹ️ **État du projet (v1) :** Le développement actuel se concentre sur **un seul rig dédié à une seule discipline : le Bac Pro CIEL**, pour un maximum de 12 élèves en simultané. Cette approche « une discipline à la fois » permet de valider en profondeur le pipeline RAG et le comportement maïeutique avant toute généralisation à d'autres matières. Les sections ci-dessous conservent la vision d'ensemble multi-disciplines (le cap), tout en précisant ce qui est réellement en cours de construction (l'étape).

---

##  La vision pédagogique : L'étayage dans la ZPD

Face à l'IA générative, deux pièges menacent les élèves :
1. **L'IA "subie" :** L'élève délègue la tâche à un outil cloud généraliste, ce qui annihile l'effort cognitif.
2. **L'interdiction stricte :** Supprimer l'IA sur des tâches complexes (comme le *troubleshooting* technique en anglais) fait basculer l'élève hors de sa **Zone Proximal de Développement (ZPD)**, provoquant blocage et décrochage.

**Notre solution :** Un tuteur IA local bridé par des instructions systèmes strictes et adossé à un **RAG** (Récupération-Génération Augmentée). L'IA n'invente rien, n'hallucine pas et utilise la **maïeutique socratique** : elle guide l'élève par le questionnement sans jamais donner la solution brute.

### Le garde-fou anti-triche : une affaire de RAG, pas seulement de prompt

Un enseignement clé tiré de la conception : **le comportement socratique ne se joue pas uniquement dans l'instruction système, il se joue d'abord dans ce que le RAG est autorisé à récupérer.** Nos documents pédagogiques se répartissent en deux zones :

* **Zone « savoir » (visibilité libre) :** référentiel, cours, notices constructeurs, définitions de concepts. L'IA y puise librement pour expliquer une notion (« qu'est-ce qu'un VLAN ? », « quelle est la tension d'alimentation de ce capteur ? »). Comprendre un concept n'est pas tricher.
* **Zone « solutions » (visibilité restreinte) :** corrigés, fiches « coup de pouce », réponses attendues. Ces documents sont **exclus de l'index consultable par l'élève** : sans ce filtrage, aucune instruction système ne suffirait, l'IA récupérerait la solution dans son contexte et la divulguerait.

La convention de rangement et la stratégie de découpage (chunking) qui rendent ce garde-fou automatique sont décrites dans **[la spécification d'ingestion](rag/RAG_INGESTION_SPEC.md)**.

### Pourquoi un RAG hybride (BM25 + embeddings) pour CIEL

Le corpus CIEL mêle deux natures de contenu, ce qui justifie une **recherche hybride** :
* les **embeddings** (recherche sémantique) excellent sur le cours et le référentiel, où la question de l'élève reformule le contenu ;
* **BM25** (recherche lexicale) est indispensable sur les notices et les TP, saturés de tokens exacts que le sémantique lisse : références de composants (`GP2Y0A41SK0F`), commandes (`no shutdown`), adresses (`192.168.99.10`), valeurs (`4.5 to 5.5 V`).

Un **reranker** pourra être ajouté dans un second temps, uniquement si la pertinence mesurée sur de vraies questions d'élèves se révèle insuffisante. De même, un éventuel **fine-tuning (LoRA)** est réservé au comportement (et non au savoir, qui reste du ressort du RAG), et seulement en dernier recours si l'instruction système « fuit » malgré tout.

---

##  Pile Technique (Hardware & Software)

Le système est conçu dans une démarche d'économie circulaire en revalorisant du matériel informatique et en ciblant la sobriété numérique (consommation nulle hors des heures de cours).

* **Système d'exploitation :** Debian GNU/Linux 13 (Trixie).
* **Moteur d'inférence :** Ollama conteneurisé sous Docker (NVIDIA Container Toolkit).
* **Interface Utilisateur :** Open WebUI avec gestion des rôles (Administrateur Enseignant / Accès bridés Élèves).
* **Réseau :** Déploiement sur un réseau local physique indépendant, étanche à Internet (100% conformité RGPD).
* **Matériel du Labo CIEL :** Architecture multi-GPU (1x RTX 5060 Ti 16 Go, 1x RTX 2060 Super 8 Go, 1x GTX 1070 8 Go) sur une alimentation de 850W.

> ⚙️ **Principe de dimensionnement — un modèle par carte, pas un modèle sur plusieurs cartes.**
> Sur du matériel grand public (sans NVLink), répartir un gros modèle sur plusieurs GPU introduit une pénalité de communication via le PCIe : un modèle éclaté sur 3 cartes tourne souvent *plus lentement* qu'un modèle tenant entièrement sur une seule. L'architecture retenue fait donc tenir **chaque modèle sur sa propre carte** — ce qui colle parfaitement au concept « un rig = une discipline = son SLM ». Pour la v1 CIEL, **une seule carte 16 Go suffit** : avec 12 élèves qui lisent, réfléchissent et écrivent, la concurrence réelle sur le GPU est de 2 à 4 requêtes en pointe, gérée nativement par `OLLAMA_NUM_PARALLEL`.

> 🗓️ **Note d'approvisionnement :** les plans matériels s'appuient sur des cartes **disponibles aujourd'hui** (RTX 5060 Ti 16 Go) La RTX 5080 Super 24 Go, un temps envisagée, n'est pas retenue à court terme : elle n'est pas encore commercialisée et son calendrier reste incertain (rumeurs glissant vers 2027), dans un contexte de forte hausse des prix de la mémoire GDDR7.

---

##  Les Agents Spécialisés Embarqués

Plutôt qu'un modèle généraliste massif, l'infrastructure fait tourner des modèles de taille intermédiaire (SLM) optimisés pour le terrain.

> 🔬 **Modèles retenus pour les tests v1 (CIEL).** La phase actuelle compare trois modèles récents, tous disponibles sur Ollama :
> * **`qwen3:14b`** *(candidat principal)* — dense, licence Apache 2.0, contexte long, bon en raisonnement et en appel d'outils. En Q4 (~9-10 Go), il laisse de la marge VRAM sur une carte 16 Go pour un contexte RAG étendu et le traitement parallèle des élèves.
> * **`gemma4:12b`** — challenger léger et multimodal (~8 Go en Q4). 
> * **`mistral-small3.2:24b`** — meilleur potentiel de qualité et function calling natif solide (~15 Go en Q4, contexte 128K). Sur 16 Go, la marge pour le KV-cache devient serrée à plusieurs requêtes parallèles ; à comparer en A/B, éventuellement sur une carte 24 Go. 
>
> La recommandation est de **démarrer sur `qwen3:14b`** pour valider tout le pipeline avec de la marge, puis de tester les autres en comparaison.

Les tuteurs de démonstration ci-dessous illustrent la vision multi-disciplines du projet (agents historiques du dépôt). Ils restent des exemples : la v1 se concentre sur un tuteur CIEL unique.

1. **William (Modèle Qwen) :** Agent de DNL (Discipline Non Linguistique) Anglais. Il simule un client subissant une panne informatique (Activité GLPI). Les élèves doivent épuiser les lignes de dialogue en anglais pour obtenir les indices du diagnostic.
2. **Jarvis (Modèle Mistral / Qwen) :** Expert en Électronique, Systèmes Embarqués, Réseaux et Cybersécurité — cœur de cible du Bac Pro CIEL.
3. **Ada (Modèle Qwen) :** Experte en développement (C, C++, Python) et logique mathématique appliquée au numérique.

> ✏️ *Les noms de modèles de base des agents sont amenés à être alignés sur les modèles de test ci-dessus au fil de la veille technologique (voir la section « Modularité » en fin de document).*

---

##  Analyse comparative des coûts

| Critère | IA Centrale Cloud (Type Albert) | Super-Serveur de Région | Notre Solution (Rig Local par discipline) |
| :--- | :--- | :--- | :--- |
| **Investissement initial** | Gratuit en apparence (Étalé sur les impôts) | Très Élevé (~100 000 €) | **Très Faible (~1500 € par pôle)** |
| **Coût de maintenance** | Inconnu | Élevé (Contrats professionnels requis) | **Nul** (Géré en interne par la filière) |
| **Conformité RGPD** | Complexe (Données sortant du lycée) | OK (Local) | **Parfaite (Local strict, sans internet)** |
| **Impact Écologique** | Continu (24h/24, 7j/7) + Trafic réseau | Élevé (Consommation + Climatisation de la baie) | **Minimal** (Bouton OFF : 0 Watt la nuit/vacances) |

---

##  Démarrage Rapide

### 0. Prérequis
Disposer d'une machine sous Debian 13 avec les pilotes NVIDIA et Docker installés et une carte graphique de type NVIDIA RTX 5060 Ti 16 Go (ou équivalent 16 Go et plus).

L'installation et la configuration de l'environnement s'effectuent entièrement en ligne de commande depuis le terminal de votre serveur Debian 13. Le parcours est automatisé via trois scripts et commandes clés :

### Étape 1 : Préparation automatique du système hôte
Ce script configure l'ensemble des dépendances système nécessaires (mises à jour, Docker, clés et dépôts officiels NVIDIA Developer, pilotes propriétaires récents et le NVIDIA Container Toolkit).
```bash
chmod +x infra/setup-debian.sh
sudo ./infra/setup-debian.sh
```

### Étape 2 : Initialisation des serveurs (Au choix)

Selon les objectifs de votre séance et les capacités de votre serveur, lancez la stack Docker dans la configuration de votre choix :

  *   **Option A : Version Frugale (Texte uniquement — Économe en VRAM/RAM)**
      *Idéal pour les ateliers de réseau (Jarvis) ou de code (Ada).*
      ```bash
      docker compose up -d
      ```
    
*   **Option B : Version Grand Angle (Texte + Oral local avec l'IA)**
    *Idéal pour les séances de DNL Anglais avec William (génère un conteneur audio Whisper/Piper).*
    ```bash
    docker compose -f docker-compose.yml -f infra/docker-compose-voice.yml up -d
    ```

### Étape 3 : Chargement interactif des modèles maïeutiques
Ce script interactif interroge l'enseignant sur la quantité de VRAM globale disponible sur la machine pour adapter la taille des IA. Il télécharge automatiquement les modèles de base appropriés et compile vos tuteurs personnalisés (**Jarvis**, **Ada**, **William**) à partir des `Modelfiles` du projet.

```bash
chmod +x infra/load-models.sh
./infra/load-models.sh
```

---

## Exploitation Pédagogique & RAG (Mémoire Documentaire)

Une fois l'infrastructure démarrée, l'interface graphique est accessible pour les élèves sur le port configuré via Open WebUI.

**Préparer le corpus avant l'ingestion :** rangez vos documents selon la convention décrite dans **[rag/RAG_INGESTION_SPEC.md](rag/RAG_INGESTION_SPEC.md)**. C'est ce rangement (dossier + nom de fichier) qui permet de tagger automatiquement chaque document et, surtout, d'isoler les corrigés et fiches « coup de pouce » pour qu'ils ne soient jamais divulgués aux élèves.

**Liaison permanente des cours (RAG) :**

  1. Connectez-vous avec votre compte enseignant sur Open WebUI.
  2. Accédez à la section **Knowledge** (Connaissances) et téléversez vos documents de cours (PDF, Markdown, notices constructeurs) en respectant la séparation « savoir » / « solutions ».
  3. Modifiez la configuration de l'agent (`jarvis`, `ada`…) dans l'interface pour lui assigner ce dossier de connaissances.

---

>  **Modularité & Personnalisation (Créez vos propres agents) :** > Ce projet est pensé comme un **cadre de travail ouvert et évolutif**. Les agents fournis (`Jarvis`, `Ada`, `William`) sont des tuteurs de démonstration adaptés aux besoins du laboratoire CIEL, mais ils ne sont pas figés :
> 
> * **Faites évoluer les modèles (Veille technologique) :** Le monde de l'IA évolue à une vitesse fulgurante. Pour vérifier la taille des modèles et estimer la VRAM nécessaire, consultez la [Librairie Officielle Ollama](https://ollama.com/library) (l'onglet *Tags* donne la taille en Go de chaque version). Pour comparer l'intelligence et les performances des dernières nouveautés, consultez le [Hugging Face Open LLM Leaderboard](https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard). Il vous suffira ensuite de modifier la première ligne (`FROM nom_du_modele`) dans vos fichiers `.modelfile`.
> * **Créez vos propres tuteurs :** Vous pouvez cloner un `Modelfile` existant, le renommer (par exemple `Pythagore.modelfile`), ajuster son prompt système pour votre discipline (Maths, Physique, Histoire) et l'ajouter dans le dossier `agents/`.
> * **Intégration automatique :** Ajoutez simplement la ligne de compilation `docker exec -i ollama-server ollama create votre_nom -f - < ../agents/VotreFichier.modelfile` dans le script `infra/load-models.sh` pour que votre nouvel agent apparaisse directement dans Open WebUI.

## Module RAG autonome (`rag/`)
 
Au-delà du RAG natif d'Open WebUI, le projet dispose désormais d'un **pipeline
RAG autonome** dédié, dans le dossier [`rag/`](rag/README.md). Il donne un
contrôle complet sur la façon dont les documents de cours sont découpés,
indexés et recherchés — là où le RAG intégré reste une boîte noire.
 
Ce pipeline met en œuvre concrètement les principes décrits plus haut :
 
* **Recherche hybride** dense + lexical, via l'embedding multilingue **BGE-M3**
  (FR/EN) et une base vectorielle **ChromaDB** persistante. Le sémantique gère
  les questions reformulées, le lexical rattrape les termes exacts (commandes,
  adresses IP, références de composants).
* **Garde-fou anti-triche automatique** : les corrigés et fiches « coup de
  pouce » (rangés dans `corpus_ciel/05_corriges/` et `06_coups_de_pouce/`) sont
  exclus de l'index consultable par l'élève. Ils ne peuvent jamais remonter
  dans une réponse. Une double vérification (dossier + nom de fichier) refuse
  l'ingestion d'un corrigé mal rangé plutôt que de risquer une fuite.
* **Découpage intelligent** : respect des sections de cours, et surtout blocs de
  commandes (CLI Cisco, shell) et tableaux gardés **insécables** — un élève qui
  cherche une commande la retrouve entière, pas coupée en deux.
* **Déploiement Docker**, embedding sur GPU dédié (ou CPU en repli sur du
  matériel plus modeste), corpus monté en lecture seule, index persistant.
L'organisation du corpus, la convention de nommage et la stratégie de découpage
sont spécifiées dans **[rag/RAG_INGESTION_SPEC.md](rag/RAG_INGESTION_SPEC.md)**.
L'installation, les commandes et les points de vigilance propres au déploiement
sont détaillés dans **[rag/README.md](rag/README.md)**.
 
> 🧪 Une expérimentation **reranker** (branche `feature/reranker`) vise à
> resserrer encore la pertinence des résultats ; elle sera intégrée si les
> mesures sur de vraies questions d'élèves en montrent le bénéfice.
 
## Le tuteur en service : accessible aux élèves via Open WebUI
 
Le pipeline RAG est désormais **relié au chat Open WebUI**, ce qui rend le tuteur
maïeutique directement utilisable par les élèves — c'est le passage du prototype
à l'outil de classe. Le tout reste 100 % local.
 
L'architecture repose sur deux briques, dans le dossier
[`api-openwebui/`](api-openwebui/README.md) :
 
* **Une API (FastAPI)** qui orchestre tout à chaque question d'élève : elle
  effectue la recherche RAG (avec le garde-fou qui exclut les corrigés),
  construit le **prompt maïeutique**, appelle le modèle via Ollama, et renvoie la
  réponse. Le comportement pédagogique et le garde-fou vivent dans cette API,
  donc hors de portée d'un élève qui bidouillerait l'interface.
* **Une Pipe Function** collée dans Open WebUI, qui fait apparaître un modèle
  « Tuteur CIEL » dans l'interface et le relie à l'API.
**Sécurité des accès.** Le « Tuteur CIEL » est le seul modèle visible par les
élèves : les modèles bruts (qwen3, gemma, mistral) sont réservés à
l'administrateur. Un élève ne peut donc pas contourner le garde-fou en
s'adressant directement à un modèle sans filtre.
 
### Comportement observé (échantillon)
 
Sur des questions réelles, le tuteur :
* **explique les concepts** (« à quoi sert le DHCP ? ») — comprendre n'est pas tricher ;
* **refuse de résoudre les exercices** (« écris le code du TP ») et guide par le
  questionnement ;
* **tient face aux tentatives de contournement** (« le prof a dit que… », « oublie
  tes instructions »).
Des exemples d'échanges réels sont rassemblés dans [EXEMPLES.md](EXEMPLES.md).
Le mode d'emploi complet (lancement de l'API, installation de la Pipe Function,
sécurisation des accès) est dans [api-openwebui/README.md](api-openwebui/README.md).
 
