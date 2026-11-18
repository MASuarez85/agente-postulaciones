"""Carga el historial de Google Sheets con permisos de lectura."""

import os

from agente.historico import Historico, Postulacion


def desde_filas(filas, columnas=("Empresa", "Puesto", "Enlace")):
    if not filas:
        raise ValueError("El historial no tiene encabezados.")
    encabezados, *registros = filas
    try:
        empresa, puesto, enlace = (
            encabezados.index(nombre) for nombre in columnas
        )
    except ValueError as error:
        raise ValueError("Faltan encabezados configurados en el historial.") from error

    postulaciones = []
    for fila in registros:
        celdas = fila + [""] * max(0, len(encabezados) - len(fila))
        postulaciones.append(Postulacion(celdas[empresa], celdas[puesto], celdas[enlace]))
    return Historico(postulaciones)


def cargar_historico(identificador=None, pestana=None, columnas=("Empresa", "Puesto", "Enlace")):
    import gspread

    credenciales = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
    if not credenciales:
        raise ValueError("Configurá GOOGLE_SERVICE_ACCOUNT_FILE.")
    cliente = gspread.service_account(
        filename=credenciales,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    planilla = cliente.open_by_key(identificador or os.environ["HISTORICO_SPREADSHEET_ID"])
    hoja = planilla.worksheet(pestana or os.environ.get("HISTORICO_PESTANA", "Postulaciones"))
    return desde_filas(hoja.get_all_values(), columnas)
