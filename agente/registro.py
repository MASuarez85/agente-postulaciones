"""Registro operativo y consulta del historial antes de escribir."""

import os
from datetime import datetime
from zoneinfo import ZoneInfo

from agente.filtro import filtrar
from agente.historico import id_aviso
from agente.historico_sheets import cargar_historico
from agente.resumen import resumir, guardar_descripcion

COLUMNAS = ["id_aviso","fecha_detectado","empresa","rol","link_aviso","ubicacion_modalidad","elegible_argentina","puntaje","link_cv","link_carta","estado","fecha_postulacion","ultimo_aviso_mail","notas"]


def abrir_registro():
    import gspread

    identificador = os.environ["AGENTE_SPREADSHEET_ID"]
    if identificador == os.environ.get("HISTORICO_SPREADSHEET_ID"):
        raise ValueError("El registro operativo debe ser distinto del historial.")
    cliente = gspread.service_account(
        filename=os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    return cliente.open_by_key(identificador)


def leer_registro(planilla):
    hoja = planilla.worksheet("Postulaciones")
    filas = hoja.get_all_values()
    if not filas or filas[0] != COLUMNAS:
        raise ValueError("Los encabezados del registro no coinciden con el RFC.")
    return hoja, filas[1:]


def registrar(aviso, preparar=None):
    planilla = abrir_registro()
    config = dict(planilla.worksheet("Config").get_all_values()[1:])
    if config["historico_spreadsheet_id"] == planilla.id:
        raise ValueError("El registro operativo debe ser distinto del historial.")
    historico = cargar_historico(
        config["historico_spreadsheet_id"],
        config["historico_pestana"],
        tuple(config[f"historico_{campo}"] for campo in ("empresa", "puesto", "enlace")),
    )
    hoja, filas = leer_registro(planilla)
    resultado = filtrar(aviso, {fila[0] for fila in filas if fila}, historico)
    identificador = id_aviso(aviso.link)
    if resultado.estado == "omitir" or not identificador:
        return resultado.estado, resultado.motivo

    estado = "revisar"
    nota = resultado.motivo or "Pendiente de validar elegibilidad y compatibilidad"
    documentos = preparar(identificador) if preparar and resultado.estado == "continuar" else []
    if documentos:
        estado = "pendiente de confirmación"
        nota = "Revisá elegibilidad, compatibilidad y PDFs locales antes de postularte. " + str(documentos[0].parent)
    datos = dict(
        id_aviso=identificador,
        fecha_detectado=datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).date().isoformat(),
        empresa=aviso.empresa,
        rol=aviso.rol,
        link_aviso=aviso.link,
        estado=estado,
        notas=nota,
    )
    hoja.append_row([datos.get(columna, "") for columna in COLUMNAS], value_input_option="RAW")
    return estado, nota


def importar_alertas(enlaces, lector=None):
    """Agrega avisos nuevos a la cola de revisión y omite IDs conocidos."""
    planilla = abrir_registro()
    hoja, filas = leer_registro(planilla)
    config = dict(planilla.worksheet("Config").get_all_values()[1:])
    historico = cargar_historico(
        config["historico_spreadsheet_id"],
        config["historico_pestana"],
        tuple(config[f"historico_{campo}"] for campo in ("empresa", "puesto", "enlace")),
    )
    conocidos = historico.ids | {fila[0] for fila in filas if fila}
    fecha = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).date().isoformat()
    from agente.avisos import leer_aviso
    from agente.historico import Postulacion
    from requests.exceptions import RequestException

    lector = lector or leer_aviso
    nuevas = []
    repetidos = 0
    previos = 0
    invalidos = 0
    for url, asunto in enlaces.items():
        identificador = id_aviso(url)
        if not identificador:
            invalidos += 1
            continue
        if identificador in conocidos:
            repetidos += 1
            continue
        conocidos.add(identificador)
        datos = dict(id_aviso=identificador, fecha_detectado=fecha, link_aviso=url,
                     estado="revisar", notas=f"Alerta Gmail: {asunto}. Verificá empresa, puesto, historial y elegibilidad en el aviso.")
        try:
            aviso = lector(url)
            guardar_descripcion(identificador, aviso)
            coincidencia = historico.coincidencia(Postulacion(aviso.empresa, aviso.puesto, url))
            if coincidencia == "ya postulado":
                previos += 1
                continue
            datos.update(empresa=aviso.empresa, rol=aviso.puesto)
            datos["notas"] = resumir(aviso.descripcion, coincidencia)
        except (ValueError, RequestException) as error:
            datos["notas"] = f"Alerta Gmail: {asunto}. Lectura pendiente: {error}"
        nuevas.append([datos.get(columna, "") for columna in COLUMNAS])
    if nuevas:
        hoja.append_rows(nuevas, value_input_option="RAW")
    print(f"Resumen de importación. Repetidos por ID: {repetidos}. Postulaciones previas: {previos}. Enlaces inválidos: {invalidos}. Nuevos: {len(nuevas)}.")
    return len(nuevas)
