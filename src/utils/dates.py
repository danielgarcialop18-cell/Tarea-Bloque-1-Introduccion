# dates.py — Funciones auxiliares de fechas
# -----------------------------------------
# Ejemplo de función para convertir un string de fecha a datetime.

from dateutil import parser

def parse_date(date_str):
    return parser.isoparse(date_str)
