"""Lectura de datos estructurados del aviso público de LinkedIn."""

import json
from dataclasses import dataclass
from html.parser import HTMLParser

import requests

from agente.historico import id_aviso


class Pagina(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.jsonld = []
        self.actual = None
        self.textos = []

    def handle_starttag(self, tag, attrs):
        if tag == "script" and dict(attrs).get("type") == "application/ld+json":
            self.actual = []

    def handle_data(self, texto):
        if self.actual is not None:
            self.actual.append(texto)
        else:
            self.textos.append(texto)

    def handle_endtag(self, tag):
        if tag == "script" and self.actual is not None:
            self.jsonld.append("".join(self.actual))
            self.actual = None


@dataclass(frozen=True)
class Aviso:
    empresa: str
    puesto: str
    descripcion: str


def extraer(html):
    pagina = Pagina()
    pagina.feed(html)
    candidatos = []
    for bloque in pagina.jsonld:
        try:
            dato = json.loads(bloque)
        except json.JSONDecodeError:
            continue
        candidatos.extend(dato if isinstance(dato, list) else [dato])
    while candidatos:
        dato = candidatos.pop(0)
        if not isinstance(dato, dict):
            continue
        candidatos.extend(dato.get("@graph", []))
        tipo = dato.get("@type")
        if tipo != "JobPosting" and not (isinstance(tipo, list) and "JobPosting" in tipo):
            continue
        organizacion = dato.get("hiringOrganization") or {}
        descripcion = Pagina()
        descripcion.feed(dato.get("description") or "")
        texto = " ".join(descripcion.textos).strip()
        empresa = organizacion.get("name", "").strip()
        puesto = dato.get("title", "").strip()
        if empresa and puesto and texto:
            return Aviso(empresa, puesto, texto)
    raise ValueError("El aviso no expone datos completos. Puede requerir sesión o estar cerrado.")


def leer_aviso(url):
    identificador = id_aviso(url)
    if not identificador:
        raise ValueError("Se requiere un enlace válido de aviso de LinkedIn.")
    respuesta = requests.get(
        f"https://www.linkedin.com/jobs/view/{identificador}/",
        timeout=30,
        allow_redirects=False,
    )
    respuesta.raise_for_status()
    if respuesta.is_redirect:
        raise ValueError("LinkedIn redirigió la consulta. Se requiere revisión del aviso.")
    return extraer(respuesta.text)
