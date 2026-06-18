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

### 1. Prérequis
Disposer d'une machine sous Debian 13 avec les pilotes NVIDIA et Docker installés.

### 2. Déploiement de la Stack
Clonez le dépôt et lancez l'infrastructure avec Docker Compose :

```bash
git clone [https://github.com/Supoz9/edge-ai-education.git](https://github.com/Supoz9/edge-ai-education.git)
cd edge-ai-education/infra
docker compose up -d
