"""Ingreso interactivo de credenciales en el Llavero de macOS."""

import getpass
import sys

SERVICIO = "agente-postulaciones.linkedin"


def configurar():
    import keyring
    from keyring.backends.macOS import Keyring

    if sys.platform != "darwin":
        raise RuntimeError("Este comando requiere el Llavero de macOS.")
    if not sys.stdin.isatty():
        raise RuntimeError("Ejecutá este comando en una Terminal interactiva.")
    # Selección explícita para impedir el uso de un almacén de texto plano.
    llavero = Keyring()
    correo = input("Correo de LinkedIn: ").strip()
    if not correo or "@" not in correo:
        raise ValueError("Ingresá un correo válido.")
    secreto = getpass.getpass("Contraseña de LinkedIn (oculta): ")
    if not secreto:
        raise ValueError("La contraseña está vacía.")
    try:
        llavero.set_password(SERVICIO, correo, secreto)
        llavero.set_password(SERVICIO, "cuenta-activa", correo)
    finally:
        secreto = None
    print("Credenciales guardadas en el Llavero de macOS.")


def recuperar():
    """Recupera las credenciales usando exclusivamente el Llavero de macOS."""
    from keyring.backends.macOS import Keyring

    if sys.platform != "darwin":
        raise RuntimeError("Este comando requiere el Llavero de macOS.")
    llavero = Keyring()
    correo = llavero.get_password(SERVICIO, "cuenta-activa")
    secreto = llavero.get_password(SERVICIO, correo) if correo else None
    if not correo or not secreto:
        raise ValueError("Configurá las credenciales con --configurar-linkedin.")
    return correo, secreto
