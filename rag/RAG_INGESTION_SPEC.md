# Spécification d'ingestion RAG — Edge-IA CIEL

> Convention de rangement + nommage permettant à un script d'ingestion de tagger
> automatiquement chaque document, sans intervention manuelle fichier par fichier.
> Principe directeur : **le rangement est la métadonnée.**

---

## 1. Le principe : convention, pas tag manuel

Le script d'ingestion déduit toutes les métadonnées d'un chunk à partir de **deux
sources redondantes** :

1. le **dossier** dans lequel se trouve le PDF ;
2. le **nom du fichier**, qui encode aussi le type.

La redondance est volontaire. Le garde-fou anti-triche (voir 5) repose sur le fait
qu'un corrigé ne soit jamais servi à l'élève. Si l'information de type ne vivait que
dans le dossier, une seule erreur de rangement suffirait à divulguer un corrigé. En
la codant **aussi** dans le nom du fichier, on obtient une double sécurité : le script
peut détecter une incohérence (fichier `...-corrige.pdf` rangé dans `01_cours/`) et
refuser d'ingérer plutôt que de risquer une fuite.

---

## 2. Arborescence des dossiers

```
corpus_ciel/
├── 01_referentiel/        → type=referentiel   visibilite=libre
├── 02_cours/              → type=cours          visibilite=libre
├── 03_tp_enonces/         → type=tp             visibilite=libre
├── 04_datasheets/         → type=datasheet      visibilite=libre
├── 05_corriges/           → type=corrige        visibilite=RESTREINTE
└── 06_coups_de_pouce/     → type=coup_de_pouce  visibilite=RESTREINTE
```

Règle absolue : **tout ce qui contient une solution attendue va dans `05_` ou `06_`.**
En cas de doute sur un document, il va en zone restreinte par défaut (fail-safe :
mieux vaut une IA trop prudente qu'une IA qui divulgue).

Note sur les énoncés de TP (`03_`) : ils restent en visibilité libre car l'élève a le
droit de les lire (c'est son sujet). Mais leurs **questions à trous et réponses
attendues** ne doivent pas être « complétées » par l'IA — c'est le rôle du system
prompt (mode socratique sur `type=tp`), pas du filtrage RAG.

---

## 3. Convention de nommage des fichiers

```
<activite>_<seq>_<slug-descriptif>_<type>.pdf
```

Champs, séparés par `_` :

| Champ         | Exemples                        | Rôle                                             |
|---------------|---------------------------------|--------------------------------------------------|
| `activite`    | `R3`, `E1`, `D2`, `NA`          | Code activité RAP (`NA` si non applicable)       |
| `seq`         | `sq2a6`, `sq1a3`, `NA`          | Séquence / activité pédagogique                  |
| `slug`        | `reseau-lan-routage`            | Description courte, en minuscules, tirets        |
| `type`        | `cours`, `tp`, `corrige`, …     | **Doit correspondre au dossier** (voir 2)       |

Exemples :

```
01_referentiel/       NA_NA_referentiel-rap_referentiel.pdf   
03_tp_enonces/  R3_sq2a6_reseau-lan-routage_tp.pdf
06_coups_de_pouce/ R3_sq2a6_reseau-lan-routage_coup-de-pouce.pdf
04_datasheets/  NA_NA_sharp-gp2y0a41sk0f_datasheet.pdf
```

Le lien entre l'énoncé et sa fiche coup de pouce se fait tout seul : même `activite`
+ même `seq` + même `slug`, seul le `type` change. Le script peut ainsi savoir que la
fiche `R3_sq2a6_...` est le corrigé d'appoint de l'énoncé `R3_sq2a6_...`.

---

## 4. Schéma de métadonnées produit par le script

Pour chaque chunk, le script génère :

```json
{
  "discipline": "CIEL",
  "source": "R3_sq2a6_reseau-lan-routage_tp",
  "type": "tp",
  "activite": "R3",
  "sequence": "sq2a6",
  "chapitre": "routage inter-réseaux",
  "visibilite": "libre",
  "langue": "fr",
  "chunk_id": "R3_sq2a6_..._c07",
  "contient_code": true,
  "contient_tableau": false
}
```

- `chapitre` : déduit du `slug` ou d'un mapping séquence→chapitre que vous fournissez
  une fois pour toutes (petit CSV).
- `langue` : détectée automatiquement (les datasheets sont souvent en anglais).
- `contient_code` / `contient_tableau` : drapeaux posés par les règles de chunking
  (6), utiles pour le reranking et pour éviter de casser ces blocs.

---

## 5. Le garde-fou anti-triche (le point critique)

Deux niveaux de visibilité :

**`libre`** — récupérable et citable par l'IA sans réserve. L'élève demande « c'est
quoi un VLAN », « quelle est la tension d'alim du capteur » → l'IA puise ici.

**`restreinte`** — corrigés et fiches coup de pouce. Deux stratégies possibles, à
choisir selon votre appétence technique :

- *Stratégie simple (recommandée pour la v1)* : ces chunks sont **totalement exclus**
  de l'index de recherche des élèves. L'IA ne les voit jamais. Elle guide l'élève à
  partir du seul énoncé + cours, en mode socratique. Simple, robuste, zéro fuite.

- *Stratégie avancée (plus tard)* : ces chunks vivent dans un **canal séparé** que le
  system prompt reçoit sous une étiquette explicite du genre « CONTEXTE PROF — sert à
  calibrer tes indices, ne JAMAIS le divulguer ». L'IA sait alors où l'élève doit
  arriver et peut doser ses indices, sans donner la réponse. Plus puissant
  pédagogiquement, mais demande un system prompt très solide et des tests anti-fuite.

Commencez par la stratégie simple. Vous passerez à l'avancée seulement si vous
constatez que l'IA guide « à l'aveugle » de façon trop imprécise.

---

## 6. Règles de chunking par type

Le découpage naïf « N tokens avec overlap » casse les commandes et les tableaux. Règles :

| Type          | Unité de chunk                                             | Insécables                       |
|---------------|------------------------------------------------------------|----------------------------------|
| `referentiel` | 1 activité (E1, R3…) = 1 chunk                              | bloc « résultats attendus »      |
| `cours`       | 1 section / sous-titre = 1 chunk                           | définitions                      |
| `tp`          | 1 étape / partie numérotée = 1 chunk                       | **blocs CLI**, **tableaux**      |
| `datasheet`   | 1 section (ratings, caractéristiques…) = 1 chunk           | **tableaux de valeurs**          |
| `corrige`     | idem énoncé correspondant                                  | idem                             |

Traitement spécial des **blocs de commandes** (CLI Cisco, code) : ne jamais les couper.
Un bloc `ip dhcp pool ... / network ... / default-router ...` reste entier, sinon l'IA
récupère une demi-commande inexploitable.

Traitement spécial des **tableaux** : les linéariser en texte pour que BM25 **et**
l'embedding les retrouvent. Exemple, le plan d'adressage du TP devient :
`« Réseau TECHNIQUE : interface routeur G0/0, réseau 192.168.10.0/24, passerelle
192.168.10.1 »` — une ligne par entrée. Les valeurs exactes (IP, ports) restent alors
cherchables par correspondance lexicale.

---

## 7. Pourquoi RAG hybride (BM25 + embeddings) sur CE corpus


- **Embeddings (dense)** : forts sur le cours et le référentiel, où la question de
  l'élève est reformulée (« à quoi sert la passerelle » ≠ mots exacts du cours).
- **BM25 (lexical)** : indispensable sur les datasheets et les TP, pleins de tokens
  exacts que le dense lisse — références (`GP2Y0A41SK0F`), commandes (`no shutdown`),
  adresses (`192.168.99.10`), valeurs (`4.5 to 5.5 V`).

Le hybride prend le meilleur des deux. Sur un corpus purement littéraire, le dense
seul suffirait — mais CIEL est justement le cas où le lexical paie.

---

## 8. Ordre de mise en œuvre suggéré

1. Ranger les PDF selon 2 + renommer selon 3 (le gros du travail manuel, une fois).
2. Script d'ingestion : parcours des dossiers → déduction métadonnées → chunking 6
   → exclusion des `restreinte` de l'index élève (stratégie simple 5).
3. RAG hybride BM25 + dense sur l'index « libre ».
4. System prompt maïeutique, avec comportement adapté au champ `type`.
5. Mesure sur de vraies questions d'élèves. **Reranker** ajouté seulement si la
   pertinence mesurée est insuffisante.
6. LoRA comportemental en tout dernier recours, si le prompt « fuit » malgré tout. (QLoRA ?)
