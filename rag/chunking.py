"""
chunking.py — 04/07/26 — @Supoz9 — v2.0

Principes clés :
- Le nom de fichier encode les métadonnées (<activite>_<seq>_<slug>_<type>.pdf).
- Les blocs de commandes CLI et les tableaux sont INSÉCABLES : on ne les coupe
  jamais, sinon le RAG remonte des demi-commandes inexploitables.
- La granularité du <seq> est souple : "sq3" (cours = séquence entière) ou
  "sq2a6" (TP = séquence + activité). Voir remarque de l'enseignant.
"""
 
import re
from dataclasses import dataclass, field
from typing import Optional
 
import config
 
 
# --- 1. Parsing du nom de fichier -------------------------------------------
 
# <activite>_<seq>_<slug>_<type>.ext
# activite : R3, E1, D2, NA...   seq : sq3, sq2a6, NA...   type : dernier segment
FILENAME_RE = re.compile(
    r"^(?P<activite>[A-Za-z0-9]+)_(?P<seq>[A-Za-z0-9]+)_(?P<slug>.+)_(?P<type>[a-z\-]+)$"
)
 
 
@dataclass
class DocMeta:
    """Métadonnées d'un document, déduites du dossier + nom de fichier."""
    source: str          # nom du fichier sans extension
    type: str            # referentiel | cours | tp | datasheet | corrige | coup-de-pouce
    activite: str        # R3, E1... ou NA
    sequence: str        # sq3, sq2a6... ou NA
    slug: str
    visibilite: str      # libre | restreinte
    langue: str = "fr"   # rempli à l'ingestion (détection)
 
 
def parse_filename(filename_stem: str, dossier_type: str, dossier_visibilite: str) -> DocMeta:
    """
    Déduit les métadonnées d'un fichier. dossier_type/visibilite viennent du
    dossier (config.DOSSIER_MAP). On revalide le type contre le nom de fichier :
    en cas d'incohérence, on lève une erreur plutôt que de risquer une fuite.
    """
    m = FILENAME_RE.match(filename_stem)
    if not m:
        raise ValueError(
            f"Nom de fichier non conforme à la convention : '{filename_stem}'. "
            f"Attendu : <activite>_<seq>_<slug>_<type>  (ex: R3_sq2a6_reseau-lan-routage_tp)"
        )
    g = m.groupdict()
    type_fichier = g["type"]
 
    # Double sécurité : le type du nom de fichier doit matcher celui du dossier.
    if type_fichier != dossier_type:
        raise ValueError(
            f"INCOHÉRENCE DE TYPE pour '{filename_stem}' : le dossier implique "
            f"'{dossier_type}' mais le nom de fichier dit '{type_fichier}'. "
            f"Refus d'ingérer (garde-fou anti-fuite). Corrigez le rangement ou le nom."
        )
 
    return DocMeta(
        source=filename_stem,
        type=type_fichier,
        activite=g["activite"],
        sequence=g["seq"],
        slug=g["slug"],
        visibilite=dossier_visibilite,
    )
 
 
# --- 2. Détection des blocs insécables --------------------------------------
 
# Lignes ressemblant à des commandes réseau / CLI Cisco / shell.
CLI_HINTS = (
    "Router", "Switch", "config", "interface", "ip ", "no shutdown",
    "enable", "dhcp", "network", "default-router", "dns-server",
    "$", "#", "sudo", "docker", "ollama", "ping", "ipconfig", "ifconfig",
)
 
 
def _looks_like_cli(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    return any(s.startswith(h) or h in s[:20] for h in CLI_HINTS)
 
 
def _looks_like_table_row(line: str) -> bool:
    # Ligne de tableau : plusieurs colonnes séparées par | ou par des espaces
    # multiples, ou contenant des IP / masques.
    if line.count("|") >= 2:
        return True
    if re.search(r"\d+\.\d+\.\d+\.\d+", line):  # adresse IP
        return True
    if re.search(r"\s{3,}\S+\s{3,}\S+", line):  # colonnes espacées
        return True
    return False
 
 
# --- 3. Découpage principal --------------------------------------------------
 
@dataclass
class Chunk:
    text: str
    contient_code: bool = False
    contient_tableau: bool = False
    extra: dict = field(default_factory=dict)
 
 
def chunk_text(raw_text: str, doc_type: str) -> list[Chunk]:
    """
    Découpe le texte en respectant les frontières naturelles et en gardant les
    blocs CLI / tableaux insécables. La stratégie de frontière dépend du type :
      - referentiel : coupe sur les activités (E1, R3, T1...)
      - cours/datasheet : coupe sur les titres de section / lignes courtes en gras
      - tp/corrige : coupe sur les étapes numérotées, sans casser CLI/tableaux
    """
    lines = raw_text.splitlines()
 
    # Regroupe d'abord les lignes en "blocs logiques" : un bloc CLI/tableau
    # contigu reste soudé, le reste est du texte courant.
    blocs: list[Chunk] = []
    buffer: list[str] = []
    buf_is_code = False
    buf_is_table = False
 
    def flush():
        nonlocal buffer, buf_is_code, buf_is_table
        if buffer and any(l.strip() for l in buffer):
            blocs.append(Chunk(
                text="\n".join(buffer).strip(),
                contient_code=buf_is_code,
                contient_tableau=buf_is_table,
            ))
        buffer, buf_is_code, buf_is_table = [], False, False
 
    for line in lines:
        is_cli = _looks_like_cli(line)
        is_tab = _looks_like_table_row(line)
 
        if is_cli or is_tab:
            # démarre/continue un bloc spécial ; si on était en texte normal, on flush
            if buffer and not (buf_is_code or buf_is_table):
                flush()
            buffer.append(line)
            buf_is_code = buf_is_code or is_cli
            buf_is_table = buf_is_table or is_tab
        else:
            # ligne normale ; si on sortait d'un bloc spécial, on le flush d'abord
            if buffer and (buf_is_code or buf_is_table):
                flush()
            buffer.append(line)
    flush()
 
    # Fusionne les blocs de texte courant jusqu'à la taille cible, MAIS ne fusionne
    # jamais un bloc insécable avec autre chose : il reste un chunk à part entière.
    chunks: list[Chunk] = []
    acc: list[str] = []
 
    def flush_acc():
        nonlocal acc
        if acc:
            txt = "\n".join(acc).strip()
            if txt:
                chunks.append(Chunk(text=txt))
        acc = []
 
    for b in blocs:
        if b.contient_code or b.contient_tableau:
            flush_acc()
            chunks.append(b)  # insécable : tel quel
        else:
            acc.append(b.text)
            if sum(len(x) for x in acc) >= config.CHUNK_TARGET_CHARS:
                flush_acc()
    flush_acc()
 
    # Filet de sécurité + segmentation structurelle. Deux cas de redécoupage :
    #   (a) le chunk est STRUCTURÉ en sections (>=3 sections "1.", "Phase 2"...) :
    #       on découpe sur ces sections QUELLE QUE SOIT la taille, car chaque
    #       section est une unité de sens à retrouver séparément ;
    #   (b) sinon, on ne redécoupe que si le chunk dépasse le seuil de taille.
    # Les blocs insécables (CLI, tableaux) ne sont jamais touchés.
    final: list[Chunk] = []
    for c in chunks:
        if c.contient_code or c.contient_tableau:
            final.append(c)
            continue
 
        n_sections = len(SECTION_RE.findall(c.text))
        trop_long = len(c.text) > config.CHUNK_TARGET_CHARS * 1.15
 
        if n_sections >= 3 or trop_long:
            for part in _split_units(c.text, config.CHUNK_TARGET_CHARS,
                                     config.CHUNK_OVERLAP_CHARS):
                final.append(Chunk(text=part))
        else:
            final.append(c)
    return final
 
 
# Frontières de section fréquentes dans les cours/TP : "1.", "2. ", "Phase 1",
# "Étape 3", titres courts en fin de ligne, etc. Sert à couper proprement.
SECTION_RE = re.compile(
    r"(?m)^(?:\s*(?:\d+\.\s|Phase\s+\d+|Étape\s+\d+|Partie\s+\d+|[IVX]+\.\s))"
)
 
 
def _split_units(text: str, target: int, overlap: int) -> list[str]:
    """Redécoupe un texte en respectant, par ordre de préférence :
    1) les frontières de section (1., Phase 2, Étape 3...) — chaque section
       devient un chunk distinct ; seules les sections MINUSCULES sont fusionnées
       avec la suivante (évite les micro-chunks) ;
    2) à défaut de sections, les sauts de ligne simples, regroupés à la cible ;
    3) en dernier recours, coupe dure à la taille cible.
    Fonctionne même sur des PDF sans lignes vides (cas pypdf fréquent)."""
    positions = [m.start() for m in SECTION_RE.finditer(text)]
 
    # --- Cas 1 : document structuré en sections -> une section = un chunk ---
    if len(positions) >= 2:
        sections = []
        if positions[0] > 0:
            pre = text[:positions[0]].strip()
            if pre:
                sections.append(pre)
        for i, start in enumerate(positions):
            end = positions[i + 1] if i + 1 < len(positions) else len(text)
            sections.append(text[start:end].strip())
 
        # Seuil en dessous duquel une section est trop petite pour vivre seule
        # (on la fusionne alors avec la suivante). Sinon elle reste un chunk.
        MIN = max(120, target // 6)
        out, cur = [], ""
        for s in sections:
            # section géante -> coupe dure par fenêtres
            while len(s) > target * 1.5:
                out.append(s[:target])
                s = s[max(0, target - overlap):]
            if len(cur) < MIN:
                cur = (cur + "\n" + s).strip() if cur else s
            else:
                out.append(cur)
                cur = s
        if cur:
            # si le dernier morceau est minuscule, on le recolle au précédent
            if out and len(cur) < MIN:
                out[-1] = (out[-1] + "\n" + cur).strip()
            else:
                out.append(cur)
        return out
 
    # --- Cas 2/3 : pas de sections -> lignes regroupées à la taille cible ---
    units = [u.strip() for u in text.split("\n") if u.strip()]
    out, cur = [], ""
    for u in units:
        while len(u) > target:
            out.append(u[:target])
            u = u[max(0, target - overlap):]
        if len(cur) + len(u) + 1 <= target:
            cur = (cur + "\n" + u).strip()
        else:
            if cur:
                out.append(cur)
            cur = u
    if cur:
        out.append(cur)
    return out
 
