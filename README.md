# Edge-AI-Education : L'IA souveraine, frugale et maïeutique au Lycée

[![Souveraineté](https://img.shields.io/badge/RGPD-100%25_Local-green.svg)](#)
[![OS](https://img.shields.io/badge/OS-Debian_13-blue.svg)](#)
[![Licence](https://img.shields.io/badge/Licence-MIT-orange.svg)](#)

Ce projet propose une alternative concrète et opérationnelle à la centralisation des méga-modèles d'IA générative en nuage (Cloud). Déployée avec succès au laboratoire CIEL du Lycée Claude Chappe (Arnage), cette architecture repose sur le concept de **"Rigs" de calcul distribués par discipline**. Elle permet d'exécuter des modèles d'IA légers, ultra-spécialisés et totalement autonomes, directement dans la salle de cours.

---

##  La vision pédagogique : L'étayage dans la ZPD

Face à l'IA générative, deux pièges menacent les élèves :
1. **L'IA "subie" :** L'élève délègue la tâche à un outil cloud généraliste, ce qui annihile l'effort cognitif.
2. **L'interdiction stricte :** Supprimer l'IA sur des tâches complexes (comme le *troubleshooting* technique en anglais) fait basculer l'élève hors de sa **Zone Proximal de Développement (ZPD)**, provoquant blocage et décrochage.

**Notre solution :** Un tuteur IA local bridé par des instructions systèmes strictes et adossé à un **RAG** (Récupération-Génération Augmentée). L'IA n'invente rien, n'hallucine pas et utilise la **maïeutique socratique** : elle guide l'élève par le questionnement sans jamais donner la solution brute.

---

##  Pile Technique (Hardware & Software)

Le système est conçu dans une démarche d'économie circulaire en revalorisant du matériel informatique et en ciblant la sobriété numérique (consommation nulle hors des heures de cours).

* **Système d'exploitation :** Debian GNU/Linux 13 (Trixie).
* **Moteur d'inférence :** Ollama conteneurisé sous Docker (NVIDIA Container Toolkit).
* **Interface Utilisateur :** Open WebUI avec gestion des rôles (Administrateur Enseignant / Accès bridés Élèves).
* **Réseau :** Déploiement sur un réseau local physique indépendant, étanche à Internet (100% conformité RGPD).
* **Matériel du Labo CIEL :** Architecture multi-GPU (1x RTX 5060 Ti 16 Go, 1x RTX 2060 Super 8 Go, 1x GTX 1070 8 Go) sur une alimentation de 850W.

---

##  Les Agents Spécialisés Embarqués

Plutôt qu'un modèle généraliste massif, l'infrastructure fait tourner des modèles de taille intermédiaire (SLM) optimisés pour le terrain :

1. **William (Modèle Qwen) :** Agent de DNL (Discipline Non Linguistique) Anglais. Il simule un client subissant une panne informatique (Activité GLPI). Les élèves doivent épuiser les lignes de dialogue en anglais pour obtenir les indices du diagnostic.
2. **Jarvis (Modèle Mistral-Nemo 12B) :** Expert en Électronique, Systèmes Embarqués, Réseaux et Cybersécurité.
3. **Ada (Modèle Qwen 3.6 35B) :** Experte en développement (C, C++, Python) et logique mathématique appliquée au numérique.

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
Disposer d'une machine sous Debian 13 avec les pilotes NVIDIA et Docker installés et carte graphique type Nvidia GF 5060 Ti 16go.

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
Ce script interactif interroge l'enseignant sur la quantité de VRAM globale disponible sur la machine pour adapter la taille des IA. Il télécharge automatiquement les modèles de base appropriés et compile vos tuteurs personnalisés (**Jarvis**, **Ada**, **William**) à partir des `Modelfiles` du projet. (le monde de l'IA évolue rapidement n'hesiter 

```bash
chmod +x infra/load-models.sh
./infra/load-models.sh
```

---

Exploitation Pédagogique & RAG (Mémoire Documentaire)

Une fois l'infrastructure démarrée, l'interface graphique est accessible pour les élèves sur le port configuré via Open WebUI.
Liaison permanente des cours (RAG) :

  Connectez-vous avec votre compte enseignant sur Open WebUI.

  Accédez à la section Knowledge (Connaissances) et téléversez vos documents de cours (PDF, Markdown, notices constructeurs).

  Modifiez la configuration de l'agent jarvis ou ada dans l'interface pour lui assigner ce dossier de connaissances.

---

>  **Modularité & Personnalisation (Créez vos propres agents) :** > Ce projet est pensé comme un **cadre de travail ouvert et évolutif**. Les agents fournis (`Jarvis`, `Ada`, `William`) sont des tuteurs de démonstration adaptés aux besoins du laboratoire CIEL, mais ils ne sont pas figés :
> 
> * **Faites évoluer les modèles (Veille technologique) :** Le monde de l'IA évolue à une vitesse fulgurante. Pour vérifier la taille des modèles et estimer la VRAM nécessaire, consultez la [Librairie Officielle Ollama](https://ollama.com/library) (l'onglet *Tags* donne la taille en Go de chaque version). Pour comparer l'intelligence et les performances des dernières nouveautés, consultez le [Hugging Face Open LLM Leaderboard](https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard). Il vous suffira ensuite de modifier la première ligne (`FROM nom_du_modele`) dans vos fichiers `.modelfile`.
> * **Créez vos propres tuteurs :** Vous pouvez cloner un `Modelfile` existant, le renommer (par exemple `Pythagore.modelfile`), ajuster son prompt système pour votre discipline (Maths, Physique, Histoire) et l'ajouter dans le dossier `agents/`.
> * **Intégration automatique :** Ajoutez simplement la ligne de compilation `docker exec -i ollama-server ollama create votre_nom -f - < ../agents/VotreFichier.modelfile` dans le script `infra/load-models.sh` pour que votre nouvel agent apparaisse directement dans Open WebUI.

