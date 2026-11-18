"""Genera borradores locales con hechos del CV maestro."""

import json
import re
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from agente.historico import normalizar


def coincidencias(texto, terminos):
    return [t for t in terminos if re.search(
        r"(?<!\w)" + re.escape(normalizar(t)) + r"(?!\w)", texto
    )]


def generar(ruta_cv, empresa, puesto, ruta_aviso, destino):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate

    empresa, puesto = empresa.strip(), puesto.strip()
    aviso = ruta_aviso.read_text(encoding="utf-8").strip()
    if not all((empresa, puesto, aviso)):
        raise ValueError("Completá empresa, puesto y texto del aviso.")

    cv = json.loads(ruta_cv.read_text(encoding="utf-8"))
    texto = normalizar(puesto + " " + aviso)
    habilidades = cv["habilidades"]
    relevantes = coincidencias(texto, habilidades)
    estilos = getSampleStyleSheet()
    azul = colors.HexColor("#183449")
    for nombre in ("Title", "Heading2", "Heading3"):
        estilos[nombre].textColor = azul
    estilos["Title"].alignment = 0
    estilos["Title"].fontSize = 23
    estilos["Title"].spaceAfter = 3
    estilos["Heading2"].fontSize = 10
    estilos["Heading2"].spaceBefore = 8
    estilos["Heading2"].spaceAfter = 3
    estilos["Heading3"].spaceBefore = 4
    estilos["Heading3"].spaceAfter = 2
    estilos["BodyText"].spaceBefore = 1
    estilos["BodyText"].spaceAfter = 3
    estilos.add(estilos["BodyText"].clone("Carta", fontSize=11, leading=15, spaceAfter=10))

    def parrafo(texto, estilo="BodyText"):
        return Paragraph(escape(texto), estilos[estilo])

    contacto = [cv["ubicacion"], cv.get("email"), cv["linkedin"].removeprefix("https://www.")]
    nombre = parrafo(cv["nombre"], "Title")

    def datos_contacto():
        return parrafo(" · ".join(dato for dato in contacto if dato))

    experiencias = cv["experiencias"]
    titular = cv.get("titular", experiencias[0]["cargo"])
    if relevantes:
        titular += " | " + " · ".join(relevantes[:2])
    documento = [nombre, parrafo(titular, "Heading3"), datos_contacto()]
    if cv.get("resumen"):
        documento.extend([
            parrafo("PERFIL PROFESIONAL", "Heading2"), parrafo(cv["resumen"]),
        ])

    principales = [e for e in experiencias if e["logros"] or e.get("nota_transicion")]
    anteriores = [e for e in experiencias if e not in principales]
    logros = []
    for titulo, grupo in (
        ("EXPERIENCIA PROFESIONAL", principales),
        ("EXPERIENCIA TÉCNICA ANTERIOR", anteriores),
    ):
        if not grupo:
            continue
        documento.append(parrafo(titulo, "Heading2"))
        for e in grupo:
            ordenados = sorted(
                e["logros"],
                key=lambda logro: -len(coincidencias(normalizar(logro), relevantes)),
            )
            logros.extend(ordenados)
            fechas = f'{e["inicio"]} - {e["fin"] or "Actualidad"}'
            linea = f'{e["empresa"]} | {e["cargo"]} · {fechas}'
            bloque = [parrafo(linea, "Heading3" if e in principales else "BodyText")]
            if e.get("nota_transicion"):
                bloque.append(parrafo(e["nota_transicion"]))
            bloque.extend(parrafo(logro) for logro in ordenados)
            documento.append(KeepTogether(bloque))

    documento.append(parrafo("HABILIDADES Y FORMACIÓN", "Heading2"))
    orden_habilidades = relevantes + [h for h in habilidades if h not in relevantes]
    documento.append(parrafo(" · ".join(orden_habilidades)))
    documento.extend(parrafo(item) for item in cv["formacion"])
    documento.append(parrafo(" · ".join(cv["idiomas"])))

    carta = [
        parrafo(cv["nombre"], "Title"),
        datos_contacto(),
        parrafo(f"{puesto}, {empresa}", "Heading3"),
        parrafo(f"Hola, equipo de {empresa}:", "Carta"),
    ]
    apertura = f"Me interesa postularme para el puesto de {puesto}."
    if relevantes:
        apertura += " Puedo aportar experiencia en " + ", ".join(relevantes[:3]) + "."
    carta.append(parrafo(apertura, "Carta"))
    ejemplos = sorted(
        logros, key=lambda logro: -len(coincidencias(normalizar(logro), relevantes))
    )
    carta.extend(parrafo(logro, "Carta") for logro in ejemplos[:2])
    carta.extend([
        parrafo("Gracias por considerar mi postulación.", "Carta"),
        parrafo(cv["nombre"], "Carta"),
    ])

    fecha = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).date().isoformat()
    nombre = re.sub(r"[^a-z0-9_-]+", "_", normalizar(f"{empresa}_{puesto}")).strip("_")
    carpeta = destino / f"{nombre[:110] or 'aviso'}_{fecha}"
    destino.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=destino) as temporal:
        borrador = Path(temporal) / carpeta.name
        borrador.mkdir()
        nombres = []
        for prefijo, contenido in (("CV", documento), ("Carta", carta)):
            archivo = f"{prefijo}_{carpeta.name}.pdf"
            SimpleDocTemplate(str(borrador / archivo), pagesize=A4,
                              leftMargin=48, rightMargin=48, topMargin=36,
                              bottomMargin=36).build(contenido)
            nombres.append(archivo)
        if carpeta.exists():
            raise FileExistsError(f"Ya existe {carpeta}. Elegí otro directorio de salida.")
        borrador.rename(carpeta)
    return [carpeta / nombre for nombre in nombres]
