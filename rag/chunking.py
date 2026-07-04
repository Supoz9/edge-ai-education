"""
chunking.py — 04/07/26 — @Supoz9 — v1.0

Découpage intelligent des documents selon RAG_INGESTION_SPEC.md.

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

    # Filet de sécurité : si un chunk de texte pur dépasse largement la cible,
    # on le redécoupe sur les paragraphes (sans jamais toucher aux insécables).
    final: list[Chunk] = []
    for c in chunks:
        if (c.contient_code or c.contient_tableau
                or len(c.text) <= config.CHUNK_TARGET_CHARS * 1.6):
            final.append(c)
        else:
            for part in _split_paragraphs(c.text, config.CHUNK_TARGET_CHARS,
                                          config.CHUNK_OVERLAP_CHARS):
                final.append(Chunk(text=part))
    return final


def _split_paragraphs(text: str, target: int, overlap: int) -> list[str]:
    paras = re.split(r"\n\s*\n", text)
    out, cur = [], ""
    for p in paras:
        if len(cur) + len(p) <= target:
            cur = (cur + "\n\n" + p).strip()
        else:
            if cur:
                out.append(cur)
            cur = (cur[-overlap:] + "\n\n" + p).strip() if overlap and cur else p
    if cur:
        out.append(cur)
    return out
