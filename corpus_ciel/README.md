# Corpus CIEL — dossier de données pédagogiques
 
> ⚠️ **Ce dossier n'est PAS versionné.** Seule sa **structure** (dossiers + ce README)
> est présente dans le dépôt. Vos documents réels (`.pdf`, `.md`…) sont **ignorés par
> Git** via le `.gitignore` du projet et ne sont donc jamais publiés en ligne.
> C'est volontaire : les corrigés et fiches d'aide ne doivent pas fuiter, et les
> ressources de cours restent votre propriété.
 
Ce dossier accueille les documents que le pipeline RAG va ingérer. La règle
fondamentale — **le rangement EST la métadonnée** — est détaillée dans la
[spécification d'ingestion](../rag/RAG_INGESTION_SPEC.md). Ce fichier en est le
rappel opérationnel.
 
---
 
## Où ranger quoi
 
| Dossier              | Type de document                         | Visibilité par l'IA         |
|----------------------|------------------------------------------|-----------------------------|
| `01_referentiel/`    | Référentiel, RAP, attendus officiels     | **Libre** (citable)         |
| `02_cours/`          | Cours, supports théoriques, définitions  | **Libre** (citable)         |
| `03_tp_enonces/`     | Énoncés de TP (le sujet donné à l'élève) | **Libre** (citable)         |
| `04_datasheets/`     | Notices constructeurs, datasheets        | **Libre** (citable)         |
| `05_corriges/`       | Corrigés, solutions attendues            | **RESTREINTE** (jamais servie) |
| `06_coups_de_pouce/` | Fiches d'aide, indices, checklists       | **RESTREINTE** (jamais servie) |
 
**En cas de doute sur un document, placez-le en zone restreinte (`05_` ou `06_`).**
Principe fail-safe : mieux vaut une IA trop prudente qu'une IA qui divulgue une
solution.
 
---
 
## Convention de nommage des fichiers
 
```
<activite>_<seq>_<slug-descriptif>_<type>.pdf
```
 
* `<activite>` : code RAP (`R3`, `E1`, `D2`…) ou `NA` si non applicable
* `<seq>`      : séquence/activité (`sq2a6`…) ou `NA`
* `<slug>`     : description courte en minuscules-avec-tirets
* `<type>`     : **doit correspondre au dossier** (`referentiel`, `cours`, `tp`,
  `datasheet`, `corrige`, `coup-de-pouce`)
Le `<type>` dans le nom du fichier **double** l'information du dossier : c'est une
sécurité. Le script d'ingestion peut détecter une incohérence (par ex. un fichier
`..._corrige.pdf` rangé par erreur dans `02_cours/`) et refuser l'ingestion plutôt
que de risquer une fuite.
 
### Exemples
 
```
01_referentiel/     NA_NA_referentiel-rap_referentiel.pdf
02_cours/           R3_sq2a6_modele-osi-tcpip_cours.pdf
03_tp_enonces/      R3_sq2a6_reseau-lan-routage_tp.pdf
04_datasheets/      NA_NA_sharp-gp2y0a41sk0f_datasheet.pdf
05_corriges/        R3_sq2a6_reseau-lan-routage_corrige.pdf
06_coups_de_pouce/  R3_sq2a6_reseau-lan-routage_coup-de-pouce.pdf
```
 
Un énoncé et son aide/corrigé se lient automatiquement : **même `activite` + même
`seq` + même `slug`**, seul le `<type>` change.
 
---
 
## Rappel Git
 
Avant votre premier `git add`, vérifiez que vos PDF n'apparaissent pas :
 
```bash
git status
```
 
`corpus_ciel/` ne doit lister que les `.gitkeep` et ce `README.md` — jamais vos
documents. Si des `.pdf` apparaissent, le `.gitignore` n'est pas actif : corrigez-le
**avant** de committer (sortir des fichiers de l'historique après coup est pénible).
 
