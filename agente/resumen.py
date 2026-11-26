"""Notas breves para el panel y descripción completa en almacenamiento local."""

import json
import re
from pathlib import Path

from agente.historico import normalizar


def resumir(descripcion, antecedente=""):
    lineas = [re.sub(r"\s+", " ", linea).strip() for linea in descripcion.splitlines()]
    candidatas = [linea for linea in lineas if len(linea) >= 50]
    indicadores = (
        "experience", "experiencia", "lead", "lider", "responsib", "looking for",
        "buscamos", "years", "anos", "remote", "remoto",
    )
    priorizadas = sorted(
        enumerate(candidatas),
        key=lambda item: (-sum(termino in normalizar(item[1]) for termino in indicadores), item[0]),
    )
    texto = " ".join(linea for _, linea in priorizadas[:2])
    if not texto:
        texto = " ".join(lineas)
    prefijo = antecedente.strip()
    presupuesto = max(0, 320 - len(prefijo) - 2)
    if len(texto) > presupuesto:
        texto = texto[:max(0, presupuesto - 1)].rsplit(" ", 1)[0] + "…"
    return (prefijo + ". " if prefijo else "") + texto


def guardar_descripcion(identificador, aviso):
    carpeta = Path(__file__).resolve().parent.parent / "datos" / "avisos"
    carpeta.mkdir(parents=True, exist_ok=True)
    datos = dict(empresa=aviso.empresa, puesto=aviso.puesto, descripcion=aviso.descripcion,
                 fecha_publicacion=getattr(aviso, "fecha_publicacion", ""))
    (carpeta / f"{identificador}.json").write_text(
        json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
