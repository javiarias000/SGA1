"""
Malla curricular del Conservatorio Bolívar según Ministerio de Educación.
Fuente: Acuerdo Ministerial — Bachillerato Complementario Artístico, Música.
Años de estudio: 1° al 11° (edades 7-17).
Valores = horas semanales por asignatura por año.
"""

# ─── ASIGNATURAS COMUNES ────────────────────────────────────────────────────
# [año1, año2, ..., año11]  0 = no se dicta ese año
ASIGNATURAS_COMUNES = [
    {
        "nombre": "Instrumento Principal",
        "tipo": "INSTRUMENTO",
        "horas": [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
    },
    {
        "nombre": "Educación Rítmica Audioceptiva",
        "tipo": "TEORIA",
        "horas": [2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    },
    {
        "nombre": "Orquesta Pedagógica",
        "tipo": "AGRUPACION",
        "horas": [2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    },
    {
        "nombre": "Lenguaje Musical",
        "tipo": "TEORIA",
        "horas": [0, 0, 4, 4, 4, 4, 4, 0, 0, 0, 0],
    },
    {
        "nombre": "Instrumento Complementario",
        "tipo": "INSTRUMENTO",
        "horas": [0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0],
    },
    {
        "nombre": "Armonía",
        "tipo": "TEORIA",
        "horas": [0, 0, 0, 0, 0, 2, 2, 2, 0, 0, 0],
    },
    {
        "nombre": "Formas Musicales",
        "tipo": "TEORIA",
        "horas": [0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0],
    },
    {
        "nombre": "Informática Aplicada",
        "tipo": "TEORIA",
        "horas": [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
    },
    {
        "nombre": "Historia de la Música",
        "tipo": "TEORIA",
        "horas": [0, 0, 0, 0, 0, 0, 2, 2, 2, 0, 0],
    },
    {
        "nombre": "Coro",
        "tipo": "AGRUPACION",
        "horas": [2, 2, 2, 2, 2, 0, 0, 0, 0, 0, 0],
    },
    {
        "nombre": "Orquesta",
        "tipo": "AGRUPACION",
        "horas": [0, 0, 0, 4, 4, 4, 4, 4, 4, 4, 4],
    },
    {
        "nombre": "Conjunto Instrumental, Vocal o Mixto",
        "tipo": "AGRUPACION",
        "horas": [0, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
    },
]

# ─── MÓDULOS FORMATIVOS ─────────────────────────────────────────────────────
MODULOS_FORMATIVOS = [
    {
        "nombre": "Capacitación en Música",
        "tipo": "MODULO",
        "horas": [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0],
    },
    {
        "nombre": "Producción Artístico-Musical",
        "tipo": "MODULO",
        "horas": [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1],
    },
    {
        "nombre": "Creación y Arreglos",
        "tipo": "MODULO",
        "horas": [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1],
    },
    {
        "nombre": "Formación y Orientación Laboral",
        "tipo": "MODULO",
        "horas": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    },
]

# ─── ASIGNATURAS COMPLEMENTARIAS ────────────────────────────────────────────
ASIGNATURAS_COMPLEMENTARIAS = [
    {
        "nombre": "Teatro para Cantantes",
        "tipo": "COMPLEMENTARIA",
        "horas": [0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0],
    },
    {
        "nombre": "Fonética para Cantantes",
        "tipo": "COMPLEMENTARIA",
        "horas": [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0],
    },
    {
        "nombre": "Repertorio para Cantantes",
        "tipo": "COMPLEMENTARIA",
        "horas": [0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2],
    },
    {
        "nombre": "Acompañamiento para Pianistas",
        "tipo": "COMPLEMENTARIA",
        "horas": [0, 0, 0, 0, 0, 0, 0, 0, 2, 2, 2],
    },
]

# ─── INSTRUMENTOS DISPONIBLES ───────────────────────────────────────────────
INSTRUMENTOS = [
    "Flauta Traversa",
    "Oboe/Corno inglés",
    "Clarinete",
    "Saxofón",
    "Fagot",
    "Corno Francés",
    "Trompeta",
    "Trombón",
    "Tuba",
    "Percusión",
    "Canto",
    "Piano",
    "Acordeón",
    "Guitarra",
    "Arpa Diatónica",
    "Violín",
    "Viola",
    "Violonchelo",
    "Contrabajo",
]


def get_materias_para_anio(anio: int) -> list[dict]:
    """
    Retorna lista de materias asignadas para el año dado (1-11).
    Incluye nombre, tipo y horas semanales.
    """
    if not 1 <= anio <= 11:
        return []

    idx = anio - 1
    materias = []

    for grupo in [ASIGNATURAS_COMUNES, MODULOS_FORMATIVOS, ASIGNATURAS_COMPLEMENTARIAS]:
        for materia in grupo:
            horas = materia["horas"][idx]
            if horas > 0:
                materias.append({
                    "nombre": materia["nombre"],
                    "tipo": materia["tipo"],
                    "horas_semanales": horas,
                })

    return materias
