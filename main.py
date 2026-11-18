import argparse
from tempfile import mkdtemp
from pathlib import Path

from agente.filtro import filtrar
from agente.historico import Historico, Postulacion


def main():
    parser = argparse.ArgumentParser(description="Agente local de postulaciones")
    parser.add_argument("--demo", action="store_true", help="Ejecuta el filtro con datos ficticios")
    parser.add_argument("--consultar-historial", nargs=3, metavar=("EMPRESA", "PUESTO", "URL"))
    registro = parser.add_mutually_exclusive_group()
    registro.add_argument("--listar-registro", action="store_true")
    registro.add_argument("--registrar-aviso", nargs=3, metavar=("EMPRESA", "PUESTO", "URL"))
    parser.add_argument("--validar-cv", metavar="POSITIONS_CSV")
    parser.add_argument("--generar", nargs=3, metavar=("EMPRESA", "PUESTO", "AVISO_TXT"))
    registro.add_argument("--preparar", nargs=4, metavar=("EMPRESA", "PUESTO", "URL", "AVISO_TXT"))
    parser.add_argument("--salida", type=Path)
    registro.add_argument("--autorizar-gmail", action="store_true")
    registro.add_argument("--importar-alertas", type=int, metavar="DIAS")
    parser.add_argument("--simular", action="store_true")
    registro.add_argument("--leer-aviso", metavar="URL")
    registro.add_argument("--buscar-linkedin", metavar="PALABRAS")
    parser.add_argument("--ubicacion", default="Argentina")
    parser.add_argument("--limite", type=int, default=10)
    registro.add_argument("--configurar-linkedin", action="store_true")
    args = parser.parse_args()
    raiz = Path(__file__).resolve().parent
    if args.configurar_linkedin:
        from agente.credenciales import configurar
        from keyring.errors import KeyringError

        try:
            configurar()
        except (ValueError, RuntimeError, KeyringError, EOFError):
            parser.exit(1, "No se guardaron las credenciales. Revisá el acceso al Llavero y volvé a intentarlo desde Terminal.\n")
        return
    if args.buscar_linkedin:
        from keyring.errors import KeyringError
        from agente.linkedin import buscar
        from agente.registro import importar_alertas
        from playwright.sync_api import Error as BrowserError
        from requests.exceptions import RequestException
        from gspread.exceptions import GSpreadException
        from google.auth.exceptions import GoogleAuthError

        if not 1 <= args.limite <= 25:
            parser.error("--limite debe estar entre 1 y 25.")
        try:
            cantidad = buscar(raiz / "credenciales/linkedin-perfil", args.buscar_linkedin,
                              args.ubicacion, args.limite, args.simular, importar_alertas)
            print(f"Avisos {'detectados' if args.simular else 'cargados'}: {cantidad}")
        except KeyringError:
            parser.exit(1, "No se pudo acceder al Llavero de macOS. Revisá su autorización.\n")
        except (BrowserError, ValueError, OSError, EOFError, KeyError,
                RequestException, GSpreadException, GoogleAuthError) as error:
            parser.exit(1, f"No se pudo completar la búsqueda: {error}\n")
        return
    if args.leer_aviso:
        from agente.avisos import leer_aviso
        from requests.exceptions import RequestException

        try:
            aviso = leer_aviso(args.leer_aviso)
        except (ValueError, RequestException) as error:
            parser.exit(1, f"No se pudo leer el aviso: {error}\n")
        print(aviso.empresa, aviso.puesto, aviso.descripcion, sep="\n\n")
        return
    if args.autorizar_gmail or args.importar_alertas is not None:
        from google.auth.exceptions import GoogleAuthError
        from gspread.exceptions import GSpreadException
        from requests.exceptions import RequestException
        from agente.gmail_alertas import autorizar, leer_enlaces
        from agente.registro import importar_alertas

        token = raiz / "credenciales/gmail-token.json"
        try:
            if args.autorizar_gmail:
                autorizar(raiz / "credenciales/gmail-oauth.json", token)
                print("Gmail autorizado en modo lectura.")
                return
            if args.importar_alertas < 1:
                parser.error("DIAS debe ser mayor que cero.")
            if not token.exists():
                parser.error("Primero ejecutá --autorizar-gmail con el cliente OAuth configurado.")
            enlaces = leer_enlaces(token, args.importar_alertas)
            if args.simular:
                print(*enlaces, sep="\n")
            else:
                print(f"Avisos nuevos en revisión: {importar_alertas(enlaces)}")
        except (ValueError, OSError, KeyError, GoogleAuthError, GSpreadException, RequestException) as error:
            parser.exit(1, f"No se pudieron procesar las alertas: {error}\n")
        return
    if args.preparar:
        from google.auth.exceptions import GoogleAuthError
        from gspread.exceptions import GSpreadException
        from requests.exceptions import RequestException
        from agente.generacion import generar
        from agente.registro import registrar

        empresa, puesto, url, archivo = args.preparar
        destino = (args.salida or raiz / "salida").resolve()

        def preparar(identificador):
            destino.mkdir(parents=True, exist_ok=True)
            carpeta = Path(mkdtemp(prefix=f"{identificador}-", dir=destino))
            try:
                documentos = generar(raiz / "datos/cv_maestro.yaml", empresa, puesto,
                                     Path(archivo), carpeta)
            except Exception:
                carpeta.rmdir()
                raise
            print(*documentos, sep="\n")
            return documentos

        try:
            print(*registrar(Postulacion(empresa, puesto, url), preparar), sep=" | ")
        except PermissionError:
            parser.exit(1, "La cuenta de servicio necesita acceso al registro, historial y archivos locales.\n")
        except (ValueError, OSError, KeyError, GoogleAuthError, GSpreadException, RequestException) as error:
            parser.exit(1, f"No se pudo preparar el aviso: {error}\n")
        return
    if args.generar:
        from agente.generacion import generar

        empresa, puesto, aviso = args.generar
        try:
            documentos = generar(raiz / "datos/cv_maestro.yaml", empresa, puesto,
                                 Path(aviso), args.salida or raiz / "salida")
        except (ImportError, OSError, ValueError, KeyError) as error:
            parser.exit(1, f"No se pudieron generar los documentos: {error}\n")
        print(*documentos, sep="\n")
        return
    if args.validar_cv:
        from agente.validador import validar_cv

        ruta_cv = Path(__file__).resolve().parent / "datos" / "cv_maestro.yaml"
        try:
            diferencias = validar_cv(ruta_cv, Path(args.validar_cv))
        except (ValueError, OSError, KeyError, TypeError) as error:
            parser.exit(1, f"No se pudo validar el CV: {error}\n")
        if diferencias:
            parser.exit(1, "Revisar experiencias: " + ", ".join(diferencias) + "\n")
        print("Empresas, cargos y fechas coinciden con Positions.csv.")
        return
    if args.listar_registro or args.registrar_aviso:
        from agente.registro import abrir_registro, leer_registro, registrar

        try:
            if args.registrar_aviso:
                print(*registrar(Postulacion(*args.registrar_aviso)), sep=" | ")
            else:
                _, filas = leer_registro(abrir_registro())
                print(f"Avisos registrados: {sum(bool(fila and fila[0]) for fila in filas)}")
        except (ImportError, KeyError, ValueError, OSError, PermissionError) as error:
            parser.exit(1, f"No se pudo acceder al registro: {error}\n")
        return
    if args.consultar_historial:
        from agente.historico_sheets import cargar_historico

        try:
            historico = cargar_historico()
        except (ImportError, KeyError, ValueError, OSError) as error:
            parser.exit(1, f"No se pudo cargar el historial: {error}\n")
        resultado = filtrar(Postulacion(*args.consultar_historial), set(), historico)
        print(resultado.estado, resultado.motivo)
        return
    if not args.demo:
        parser.print_help()
        return

    historico = Historico([Postulacion("Ejemplo S.A.", "Engineering Manager")])
    for indice, rol in enumerate(
        ("Engineering Manager", "Sr. Engineering Manager", "Data Analyst"), start=1
    ):
        aviso = Postulacion("Ejemplo", rol, f"https://www.linkedin.com/jobs/view/{indice}/")
        resultado = filtrar(aviso, set(), historico)
        detalle = f" ({resultado.motivo})" if resultado.motivo else ""
        print(f"{rol} → {resultado.estado}{detalle}")


if __name__ == "__main__":
    main()
