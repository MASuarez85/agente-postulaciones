"""Consulta de postulaciones previas sobre filas ya cargadas."""

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Postulacion:
    empresa: str
    rol: str
    link: str = ""


def id_aviso(link: str) -> str:
    try:
        url = urlsplit(link.strip())
        host = url.hostname or ""
    except ValueError:
        return ""
    if url.scheme not in {"https", "http"}:
        return ""
    if host != "linkedin.com" and not host.endswith(".linkedin.com"):
        return ""
    match = re.fullmatch(r"/jobs/view/(?:[^/]+-)?([0-9]+)/?", url.path)
    return match.group(1) if match else ""


def normalizar(texto: str) -> str:
    caracteres = unicodedata.normalize("NFKD", texto.casefold())
    return " ".join(
        "".join(c for c in caracteres if not unicodedata.combining(c)).split()
    )


def normalizar_empresa(empresa: str) -> str:
    return re.sub(
        r"(?:,?\s+(?:s\.?\s*a\.?|s\.?\s*r\.?\s*l\.?|inc\.?|llc\.?|ltd\.?))$",
        "",
        normalizar(empresa),
    )


class Historico:
    def __init__(self, filas):
        self.ids = set()
        self.empresas = set()
        self.roles_por_empresa = {}
        for fila in filas:
            empresa = normalizar_empresa(fila.empresa)
            if empresa:
                self.empresas.add(empresa)
            identificador = id_aviso(fila.link)
            if identificador:
                self.ids.add(identificador)
            if not identificador:
                rol = normalizar(fila.rol)
                if empresa and rol:
                    self.roles_por_empresa.setdefault(empresa, set()).add(rol)

    def coincidencia(self, aviso: Postulacion) -> str:
        if id_aviso(aviso.link) in self.ids:
            return "ya postulado"
        roles = self.roles_por_empresa.get(normalizar_empresa(aviso.empresa), set())
        rol = normalizar(aviso.rol)
        if rol in roles:
            return "ya postulado"
        if any(SequenceMatcher(None, rol, previo).ratio() >= 0.8 for previo in roles):
            return "posible postulación previa"
        if normalizar_empresa(aviso.empresa) in self.empresas:
            return "postulación previa en la misma empresa"
        return ""
