import json
import os
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


_SPANISH_LOWER_WORDS = {
    'de', 'del', 'la', 'las', 'el', 'los', 'y', 'o', 'en', 'para', 'con', 'a', 'al', 'por',
}


def _strip_accents(s: str) -> str:
    nfkd = unicodedata.normalize('NFKD', s)
    return nfkd.encode('ascii', 'ignore').decode('utf-8')


def norm_key(value: Any) -> str:
    """Normalization key for matching (accent-insensitive, casefold, whitespace normalized)."""
    if value is None:
        return ''
    s = str(value)
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    s = _strip_accents(s)
    return s.casefold()


def _smart_title(text: str) -> str:
    """Title-case-ish formatting but keeps common Spanish particles in lowercase."""
    parts = [p for p in re.split(r"\s+", (text or '').strip()) if p]
    if not parts:
        return ''

    out = []
    for i, p in enumerate(parts):
        # Preserve all-caps tokens (acronyms)
        if p.isupper() and len(p) <= 6:
            out.append(p)
            continue

        lower = p.lower()
        if i != 0 and lower in _SPANISH_LOWER_WORDS:
            out.append(lower)
        else:
            out.append(lower[:1].upper() + lower[1:])

    return ' '.join(out)


def _clean_person_name(raw: str) -> str:
    # Strip punctuation that commonly appears in datasets and remove known titles.
    s = (raw or '').strip()
    s = s.replace('.', ' ')
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"^(mgs|lic|dr|ing)\s+", "", s, flags=re.IGNORECASE)
    return s.strip()


@dataclass(frozen=True)
class GradeLevelParsed:
    level: Optional[str]
    section: Optional[str]


def map_grade_level(curso_raw: Any, paralelo_raw: Any) -> GradeLevelParsed:
    """Map course/section inputs into the GradeLevel.level (1..11) and section (A/B/...)."""
    curso = (str(curso_raw).strip() if curso_raw is not None else '')
    paralelo = (str(paralelo_raw).strip() if paralelo_raw is not None else '')

    # Normalize section like "B (vespertina)" -> "B"
    section = paralelo.split('(')[0].strip() if paralelo else None

    # Extract primary course name, ignoring parenthesized info for initial mapping
    curso_main_part = re.sub(r'\s*\(.*\)\s*', '', curso).strip()
    s_normalized = norm_key(curso_main_part)

    # IMPORTANT: order matters (longer patterns first).
    # Convert keys to normalized form for comparison
    mapping_ordered = [
        ('11o (3o bachillerato)', '11'), # Full form with bachillerato
        ('10o (2o bachillerato)', '10'), # Full form with bachillerato
        ('9o (1o bachillerato)', '9'),  # Full form with bachillerato

        ('undécimo año', '11'), ('undecimo año', '11'),
        ('décimo año', '10'), ('decimo año', '10'),
        ('noveno año', '9'),
        ('octavo año', '8'),
        ('séptimo año', '7'), ('septimo año', '7'),
        ('sexto año', '6'),
        ('quinto año', '5'),
        ('cuarto año', '4'),
        ('tercero año', '3'),
        ('segundo año', '2'),
        ('primero año', '1'),

        ('undécimo', '11'), ('undecimo', '11'), ('onceavo', '11'),
        ('décimo', '10'), ('decimo', '10'),
        ('noveno', '9'),
        ('octavo', '8'),
        ('séptimo', '7'), ('septimo', '7'),
        ('sexto', '6'),
        ('quinto', '5'),
        ('cuarto', '4'),
        ('tercero', '3'),
        ('segundo', '2'),
        ('primero', '1'),

        ('11o', '11'), ('10o', '10'), ('9o', '9'), ('8o', '8'), ('7o', '7'),
        ('6o', '6'), ('5o', '5'), ('4o', '4'), ('3o', '3'), ('2o', '2'), ('1o', '1'),
        
        ('11', '11'), ('10', '10'), ('9', '9'), ('8', '8'), ('7', '7'),
        ('6', '6'), ('5', '5'), ('4', '4'), ('3', '3'), ('2', '2'), ('1', '1'),
    ]

    level = None
    for k_raw, v in mapping_ordered:
        if s_normalized == norm_key(k_raw): # Exact match after normalization
            level = v
            break
    
    return GradeLevelParsed(level=level, section=section)


def load_aliases(base_dir: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Load subject/teacher alias maps from base_dir/etl_mappings/*.json (if present)."""
    mappings_dir = os.path.join(base_dir, 'etl_mappings')
    subj_path = os.path.join(mappings_dir, 'subjects_aliases.json')
    teach_path = os.path.join(mappings_dir, 'teachers_aliases.json')

    def _load(path: str) -> Dict[str, str]:
        if not os.path.exists(path):
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        # normalize keys for matching
        return {norm_key(k): str(v).strip() for k, v in data.items() if k and v}

    return _load(subj_path), _load(teach_path)


def canonical_subject_name(raw: Any, subject_aliases: Optional[Dict[str, str]] = None) -> str:
    s = (str(raw).strip() if raw is not None else '')
    if not s:
        return ''

    key = norm_key(s)
    if subject_aliases and key in subject_aliases:
        return subject_aliases[key]

    # Default formatting: normalize whitespace + smart title.
    s = re.sub(r"\s+", " ", s)
    return _smart_title(s)


def canonical_teacher_name(raw: Any, teacher_aliases: Optional[Dict[str, str]] = None) -> str:
    s = _clean_person_name(str(raw) if raw is not None else '')
    if not s:
        return ''

    key = norm_key(s)
    if teacher_aliases and key in teacher_aliases:
        return teacher_aliases[key]

    # Do not title-case aggressively: keep original accents/casing as much as possible but normalize spaces.
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def clase_paralelo_key_for_grade(grade_level_level: str, grade_level_section: str) -> str:
    """Encode grade+section into Clase.paralelo so the existing uniqueness constraint stays valid."""
    if not (grade_level_level and grade_level_section):
        return ''
    return f"{grade_level_level}-{grade_level_section}"