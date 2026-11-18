"""Contrasta las experiencias del CV con Positions.csv de LinkedIn."""

import csv
import json
from datetime import datetime
from pathlib import Path

from agente.historico import normalizar


def fecha_linkedin(valor):
    valor = " ".join(valor.split())
    if not valor or valor.casefold() in {"present", "actualidad"}:
        return None
    meses = "jan feb mar apr may jun jul aug sep oct nov dec".split()
    partes = valor.casefold().split()
    if len(partes) == 2 and partes[0] in meses:
        valor = f"{partes[1]}-{meses.index(partes[0]) + 1:02}"
    return datetime.strptime(valor, "%Y-%m").strftime("%Y-%m")


def clave(empresa, cargo, inicio, fin):
    return normalizar(empresa), normalizar(cargo), inicio, fin


def validar_cv(ruta_cv: Path, ruta_positions: Path):
    cv = json.loads(ruta_cv.read_text(encoding="utf-8"))
    with ruta_positions.open(encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo)
        columnas = ("Company Name", "Title", "Started On", "Finished On")
        if not set(columnas).issubset(lector.fieldnames or []):
            raise ValueError("Positions.csv no tiene los encabezados esperados.")
        posiciones = {
            clave(fila[columnas[0]], fila[columnas[1]],
                  fecha_linkedin(fila[columnas[2]]), fecha_linkedin(fila[columnas[3]]))
            for fila in lector
        }
    return [
        experiencia["id"]
        for experiencia in cv["experiencias"]
        if clave(*(experiencia[campo] for campo in ("empresa", "cargo", "inicio", "fin")))
        not in posiciones
    ]
