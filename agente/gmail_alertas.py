"""Lee alertas de Gmail con OAuth de escritorio en modo solo lectura."""

import base64
import os
from email import policy
from email.parser import BytesParser

from google.auth.transport.requests import AuthorizedSession, Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from agente.ingesta import enlaces_alerta

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
API = "https://gmail.googleapis.com/gmail/v1/users/me/messages"


def autorizar(cliente, token):
    flow = InstalledAppFlow.from_client_secrets_file(str(cliente), SCOPES)
    credenciales = flow.run_local_server(port=0, timeout_seconds=180)
    fd = os.open(token, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as archivo:
        archivo.write(credenciales.to_json())


def leer_enlaces(token, dias):
    credenciales = Credentials.from_authorized_user_file(str(token), SCOPES)
    if not credenciales.valid:
        credenciales.refresh(Request())
    encontrados = {}
    parametros = {"q": f"from:jobalerts-noreply@linkedin.com newer_than:{dias}d", "maxResults": 100}
    with AuthorizedSession(credenciales) as sesion:
        while True:
            respuesta = sesion.get(API, params=parametros, timeout=30)
            respuesta.raise_for_status()
            pagina = respuesta.json()
            for mensaje in pagina.get("messages", []):
                respuesta = sesion.get(f"{API}/{mensaje['id']}", params={"format": "raw"}, timeout=30)
                respuesta.raise_for_status()
                raw = respuesta.json()["raw"]
                correo = BytesParser(policy=policy.default).parsebytes(
                    base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
                )
                if correo["From"].addresses[0].addr_spec.lower() != "jobalerts-noreply@linkedin.com":
                    continue
                for formato in ("plain", "html"):
                    cuerpo = correo.get_body(preferencelist=(formato,))
                    if cuerpo:
                        for url in enlaces_alerta(cuerpo.get_content()):
                            encontrados.setdefault(url, str(correo["Subject"] or ""))
            if not pagina.get("nextPageToken"):
                return encontrados
            parametros["pageToken"] = pagina["nextPageToken"]
