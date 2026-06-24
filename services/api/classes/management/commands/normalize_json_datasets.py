import json
import os
import glob
from typing import Any, Dict, List, Tuple

from django.core.management.base import BaseCommand

from utils.etl_normalization import (
    canonical_subject_name,
    canonical_teacher_name,
    load_aliases,
    norm_key,
)


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _read_json(path: str) -> Any:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _write_json(path: str, data: Any) -> None:
    _ensure_dir(os.path.dirname(path))
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _copy_file(src: str, dst: str) -> None:
    _ensure_dir(os.path.dirname(dst))
    with open(src, 'rb') as rf:
        raw = rf.read()
    with open(dst, 'wb') as wf:
        wf.write(raw)


class Command(BaseCommand):
    help = 'Normaliza los JSON en base_de_datos_json/ y escribe una copia en base_de_datos_json/normalized/ (no modifica originales).'

    def add_arguments(self, parser):
        parser.add_argument('--base-dir', default='base_de_datos_json')
        parser.add_argument('--out-dir', default='base_de_datos_json/normalized')

    def handle(self, *args, **opts):
        base_dir: str = opts['base_dir']
        out_dir: str = opts['out_dir']

        subj_aliases, teacher_aliases = load_aliases(base_dir)

        logs_dir = os.path.join(base_dir, 'etl_logs')
        _ensure_dir(logs_dir)

        unmatched_subjects: List[str] = []
        unmatched_teachers: List[str] = []
        # Not “unmatched” vs DB here (we don't touch DB), just "suspicious/empty" values.

        def canon_subj(raw: Any) -> str:
            s = canonical_subject_name(raw, subj_aliases)
            if not s:
                unmatched_subjects.append(str(raw))
            return s

        def canon_teacher(raw: Any) -> str:
            s = canonical_teacher_name(raw, teacher_aliases)
            if not s:
                unmatched_teachers.append(str(raw))
            return s

        # 1) Agrupaciones: asignaciones + docentes
        agrup_asig_src = os.path.join(base_dir, 'asignaciones_grupales', 'ASIGNACIONES_agrupaciones.json')
        agrup_doc_src = os.path.join(base_dir, 'asignaciones_grupales', 'asignaciones_docentes.json')

        if os.path.exists(agrup_asig_src):
            data = _read_json(agrup_asig_src)
            out: List[Dict[str, Any]] = []
            for row in data:
                r = dict(row)
                r['agrupacion'] = canon_subj(row.get('agrupacion'))
                out.append(r)
            _write_json(os.path.join(out_dir, 'asignaciones_grupales', 'ASIGNACIONES_agrupaciones.json'), out)

        if os.path.exists(agrup_doc_src):
            data = _read_json(agrup_doc_src)
            out: List[Dict[str, Any]] = []
            for row in data:
                r = dict(row)
                r['agrupacion'] = canon_subj(row.get('agrupacion'))
                r['docente_asignado'] = canon_teacher(row.get('docente_asignado'))
                out.append(r)
            _write_json(os.path.join(out_dir, 'asignaciones_grupales', 'asignaciones_docentes.json'), out)

        # 2) Instrumento_Agrupaciones: ASIGNACIONES_*.json
        instrumentos_dir = os.path.join(base_dir, 'Instrumento_Agrupaciones')
        if os.path.exists(instrumentos_dir):
            for path in sorted(glob.glob(os.path.join(instrumentos_dir, 'ASIGNACIONES_*.json'))):
                data = _read_json(path)
                out_rows = []
                for row in data:
                    fields = dict(row.get('fields', {}))
                    # teacher + instrument name
                    fields['docente_nombre'] = canon_teacher(fields.get('docente_nombre'))
                    fields['clase'] = canon_subj(fields.get('clase'))
                    row2 = dict(row)
                    row2['fields'] = fields
                    out_rows.append(row2)

                rel = os.path.relpath(path, base_dir)
                _write_json(os.path.join(out_dir, rel), out_rows)

            # Copy estudiantes con representantes as-is (no schema to normalize here yet)
            rep_src = os.path.join(instrumentos_dir, 'ESTUDIANTES_CON_REPRESENTANTES.json')
            if os.path.exists(rep_src):
                _copy_file(rep_src, os.path.join(out_dir, 'Instrumento_Agrupaciones', 'ESTUDIANTES_CON_REPRESENTANTES.json'))

        # 3) Horarios académicos
        horarios_src = os.path.join(base_dir, 'horarios_academicos', 'REPORTE_DOCENTES_HORARIOS_0858.json')
        if os.path.exists(horarios_src):
            data = _read_json(horarios_src)
            out_rows = []
            for row in data:
                fields = dict(row.get('fields', {}))
                fields['clase'] = canon_subj(fields.get('clase'))
                fields['docente'] = canon_teacher(fields.get('docente'))
                row2 = dict(row)
                row2['fields'] = fields
                out_rows.append(row2)
            _write_json(os.path.join(out_dir, 'horarios_academicos', 'REPORTE_DOCENTES_HORARIOS_0858.json'), out_rows)

        # 4) Estudiantes matriculados: copy as-is (canonicalization happens in ETL)
        estudiantes_dir = os.path.join(base_dir, 'estudiantes_matriculados')
        if os.path.exists(estudiantes_dir):
            for path in sorted(glob.glob(os.path.join(estudiantes_dir, '*.json'))):
                rel = os.path.relpath(path, base_dir)
                _copy_file(path, os.path.join(out_dir, rel))

        # 5) Personal docente: copy as-is (JSONL)
        docentes_src = os.path.join(base_dir, 'personal_docente', 'DOCENTES.json')
        if os.path.exists(docentes_src):
            rel = os.path.relpath(docentes_src, base_dir)
            _copy_file(docentes_src, os.path.join(out_dir, rel))

        # Copy other known files that commands expect
        tutores_src = os.path.join(base_dir, 'personal_docente', 'REPORTE_TUTORES_CURSOS_20251204_165037.json')
        if os.path.exists(tutores_src):
            rel = os.path.relpath(tutores_src, base_dir)
            _copy_file(tutores_src, os.path.join(out_dir, rel))

        # Write audit (best-effort)
        def _write_list(path: str, values: List[str]) -> None:
            values = [v for v in values if v and v.strip()]
            with open(path, 'w', encoding='utf-8') as f:
                for v in sorted(set(values), key=lambda x: norm_key(x)):
                    f.write(v.strip() + '\n')

        _write_list(os.path.join(logs_dir, 'normalize_empty_subjects.txt'), unmatched_subjects)
        _write_list(os.path.join(logs_dir, 'normalize_empty_teachers.txt'), unmatched_teachers)

        self.stdout.write(self.style.SUCCESS(f"OK: Normalized datasets written to {out_dir}"))