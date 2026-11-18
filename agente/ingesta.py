"""Extrae enlaces canónicos de avisos desde el cuerpo de una alerta."""

import re

from agente.historico import id_aviso


def enlaces_alerta(cuerpo: str) -> list[str]:
    enlaces = {}
    for enlace in re.findall(r"https?://[^\s<>\"']+", cuerpo):
        identificador = id_aviso(enlace.replace("/comm/jobs/view/", "/jobs/view/", 1))
        if identificador:
            enlaces[identificador] = f"https://www.linkedin.com/jobs/view/{identificador}/"
    return list(enlaces.values())
