"""Decisiones previas al análisis de compatibilidad."""

from dataclasses import dataclass

from agente.historico import Historico, Postulacion, id_aviso


@dataclass(frozen=True)
class Resultado:
    estado: str
    motivo: str = ""


def filtrar(aviso: Postulacion, ids_registrados: set, historico: Historico) -> Resultado:
    identificador = id_aviso(aviso.link)
    if not identificador:
        return Resultado("revisar", "El enlace no contiene un ID de aviso de LinkedIn")
    if identificador in ids_registrados:
        return Resultado("omitir", "aviso ya registrado")
    coincidencia = historico.coincidencia(aviso)
    if coincidencia == "ya postulado":
        return Resultado("omitir", "ya postulado (planilla histórica)")
    if coincidencia:
        return Resultado("revisar", coincidencia)
    return Resultado("continuar")
