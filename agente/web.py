"""Interfaz web local para las tareas disponibles del agente."""

import json
import os
import re
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from agente.historico import Postulacion

MAX_BODY = 1_000_000


def crear_handler(raiz):
    raiz = Path(raiz).resolve()

    class Handler(BaseHTTPRequestHandler):
        server_version = "AgentePostulaciones/1.0"

        def log_message(self, formato, *args):
            # Evita que URLs o datos ingresados queden en la consola.
            return

        def _headers(self, tipo="application/json; charset=utf-8"):
            self.send_header("Content-Type", tipo)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:")
            self.send_header("Cache-Control", "no-store")

        def _json(self, datos, estado=200):
            cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
            self.send_response(estado)
            self._headers()
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        def _cuerpo(self):
            try:
                largo = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                raise ValueError("La solicitud no tiene un tamaño válido.")
            if largo < 0:
                raise ValueError("La solicitud no tiene un tamaño válido.")
            if largo > MAX_BODY:
                raise ValueError("El texto es demasiado largo (máximo 1 MB).")
            contenido = self.rfile.read(largo)
            try:
                return json.loads(contenido or b"{}")
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise ValueError("No pude leer los datos enviados.")

        def do_GET(self):
            ruta = urlparse(self.path).path
            if ruta == "/":
                archivo = raiz / "web" / "index.html"
                cuerpo = archivo.read_bytes()
                self.send_response(200)
                self._headers("text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(cuerpo)))
                self.end_headers()
                self.wfile.write(cuerpo)
                return
            if ruta == "/guia":
                cuerpo = (raiz / "README.md").read_bytes()
                self.send_response(200)
                self._headers("text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(cuerpo)))
                self.end_headers()
                self.wfile.write(cuerpo)
                return
            if ruta == "/styles.css" or ruta == "/app.js":
                archivo = raiz / "web" / ruta.lstrip("/")
                cuerpo = archivo.read_bytes()
                self.send_response(200)
                self._headers("text/css; charset=utf-8" if ruta.endswith(".css") else "text/javascript; charset=utf-8")
                self.send_header("Content-Length", str(len(cuerpo)))
                self.end_headers()
                self.wfile.write(cuerpo)
                return
            if ruta == "/api/status":
                credencial = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "")
                self._json({
                    "registro": bool(os.environ.get("AGENTE_SPREADSHEET_ID")),
                    "historial": bool(os.environ.get("HISTORICO_SPREADSHEET_ID")),
                    "credencial": bool(credencial and Path(credencial).is_file()),
                    "dependencias": _reportlab_disponible(),
                    "cv_maestro": (raiz / "datos" / "cv_maestro.yaml").is_file(),
                })
                return
            if ruta == "/api/postulaciones":
                try:
                    from agente.registro import leer_registro, abrir_registro, COLUMNAS

                    _, filas = leer_registro(abrir_registro())
                    datos = []
                    for fila in filas:
                        fila = fila + [""] * max(0, len(COLUMNAS) - len(fila))
                        registro = dict(zip(COLUMNAS, fila))
                        datos.append({
                            "empresa": registro["empresa"], "rol": registro["rol"],
                            "estado": registro["estado"], "fecha": registro["fecha_detectado"],
                            "url": registro["link_aviso"], "nota": registro["notas"],
                        })
                    self._json({"postulaciones": datos[::-1]})
                except Exception as error:
                    self._json({"error": _mensaje(error)}, 400)
                return
            if ruta.startswith("/api/archivos/"):
                nombre = unquote(ruta.removeprefix("/api/archivos/"))
                if not re.fullmatch(r"(?:CV|Carta)_[a-z0-9_-]+_\d{4}-\d{2}-\d{2}\.pdf", nombre, re.I):
                    self._json({"error": "No se encontró el archivo."}, 404)
                    return
                salida = (raiz / "salida").resolve()
                candidatos = list(salida.rglob(nombre)) if salida.is_dir() else []
                archivo = next((candidato.resolve() for candidato in candidatos
                                if candidato.is_file() and salida in candidato.resolve().parents), None)
                if archivo is None:
                    self._json({"error": "No se encontró el archivo."}, 404)
                    return
                cuerpo = archivo.read_bytes()
                self.send_response(200)
                self._headers("application/pdf")
                self.send_header("Content-Disposition", f'attachment; filename="{nombre}"')
                self.send_header("Content-Length", str(len(cuerpo)))
                self.end_headers()
                self.wfile.write(cuerpo)
                return
            self._json({"error": "No se encontró esa página."}, 404)

        def do_POST(self):
            try:
                datos = self._cuerpo()
                if self.path == "/api/postulaciones":
                    empresa = _texto(datos, "empresa", 160)
                    rol = _texto(datos, "rol", 200)
                    enlace = _texto(datos, "url", 1000)
                    if not re.match(r"^https?://", enlace, re.I):
                        raise ValueError("Pegá un enlace web válido para el aviso.")
                    from agente.registro import registrar

                    estado, motivo = registrar(Postulacion(empresa, rol, enlace))
                    self._json({"estado": estado, "motivo": motivo})
                    return
                if self.path == "/api/documentos":
                    empresa = _texto(datos, "empresa", 160)
                    rol = _texto(datos, "rol", 200)
                    aviso = _texto(datos, "aviso", 50_000)
                    from agente.generacion import generar

                    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as temporal:
                        temporal.write(aviso)
                        ruta_aviso = Path(temporal.name)
                    try:
                        documentos = generar(raiz / "datos/cv_maestro.yaml", empresa, rol, ruta_aviso, raiz / "salida")
                    finally:
                        ruta_aviso.unlink(missing_ok=True)
                    self._json({"archivos": [f"/api/archivos/{archivo.name}" for archivo in documentos]})
                    return
                self._json({"error": "No se encontró esa acción."}, 404)
            except (ValueError, KeyError, OSError, ImportError, PermissionError) as error:
                self._json({"error": _mensaje(error)}, 400)
            except Exception:
                self._json({"error": "Ocurrió un problema al procesar la solicitud. Revisá la configuración y volvé a intentar."}, 500)

    return Handler


def _texto(datos, clave, maximo):
    valor = datos.get(clave, "")
    if not isinstance(valor, str):
        raise ValueError("Revisá los campos del formulario.")
    valor = valor.strip()
    if not valor:
        raise ValueError("Completá todos los campos obligatorios.")
    if len(valor) > maximo:
        raise ValueError(f"El campo supera el máximo de {maximo:,} caracteres.")
    return valor


def _mensaje(error):
    texto = str(error)
    mensajes = {
        "GOOGLE_SERVICE_ACCOUNT_FILE": "Configurá GOOGLE_SERVICE_ACCOUNT_FILE para conectar Google Sheets.",
        "AGENTE_SPREADSHEET_ID": "Configurá AGENTE_SPREADSHEET_ID para conectar el registro.",
        "HISTORICO_SPREADSHEET_ID": "Configurá HISTORICO_SPREADSHEET_ID para consultar el historial.",
    }
    for clave, mensaje in mensajes.items():
        if clave in texto:
            return mensaje
    return texto or "No se pudo completar la acción."


def _reportlab_disponible():
    try:
        import reportlab  # noqa: F401
        return True
    except ImportError:
        return False


def servir(raiz):
    host = os.environ.get("AGENTE_WEB_HOST", "127.0.0.1")
    puerto = int(os.environ.get("AGENTE_WEB_PORT", "8765"))
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Por seguridad, la interfaz solo puede escuchar en localhost.")
    servidor = ThreadingHTTPServer((host, puerto), crear_handler(raiz))
    print(f"Interfaz lista en http://{host}:{puerto} (Ctrl+C para cerrar)")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nInterfaz cerrada.")
    finally:
        servidor.server_close()
