"""Búsqueda de empleos en el navegador local del agente."""

import os
import re
import sys
from urllib.parse import urlencode, urljoin, urlsplit, parse_qs

from playwright.sync_api import sync_playwright, TimeoutError as BrowserTimeout, Error as BrowserError

from agente.avisos import Aviso, extraer
from agente.historico import id_aviso


def enlaces_busqueda(hrefs):
    encontrados = {}
    for href in hrefs:
        url = urljoin("https://www.linkedin.com", href)
        identificador = id_aviso(url)
        partes = urlsplit(url)
        host = partes.hostname or ""
        if not identificador and (host == "linkedin.com" or host.endswith(".linkedin.com")):
            candidato = parse_qs(partes.query).get("currentJobId", [""])[0]
            coincidencia = re.search(r"/jobs/view/(?:[^/]*-)?([0-9]+)", partes.path)
            if candidato.isdigit():
                identificador = candidato
            elif coincidencia:
                identificador = coincidencia.group(1)
        if identificador:
            encontrados[identificador] = f"https://www.linkedin.com/jobs/view/{identificador}/"
    return list(encontrados.values())



def sesion_iniciada(pagina):
    partes = urlsplit(pagina.url)
    if partes.hostname != "www.linkedin.com":
        return False
    if partes.path.startswith("/feed"):
        return True
    return pagina.locator(
        'a[href*="/mynetwork/"], a[href*="/messaging/"], button.global-nav__primary-link-me-menu-trigger'
    ).count() > 0


def esperar_sesion(pagina):
    if sesion_iniciada(pagina):
        return
    if not sys.stdin.isatty():
        raise ValueError("LinkedIn requiere intervención. Ejecutá la búsqueda desde Terminal.")
    input("Completá el acceso o la verificación en el navegador. Cuando veas tu cuenta abierta, presioná Enter aquí. ")
    pagina.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
    if not sesion_iniciada(pagina):
        raise ValueError("LinkedIn todavía no confirmó la sesión. Volvé a intentar la búsqueda.")


def iniciar_sesion(pagina):
    from agente.credenciales import recuperar

    pagina.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
    if sesion_iniciada(pagina):
        return
    pagina.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
    if sesion_iniciada(pagina):
        return
    correo, secreto = recuperar()
    try:
        if urlsplit(pagina.url).hostname != "www.linkedin.com":
            raise ValueError("El navegador debe estar en LinkedIn para iniciar sesión.")
        pagina.locator("#username").fill(correo, timeout=10000)
        pagina.locator("#password").fill(secreto, timeout=10000)
        pagina.locator('button[type="submit"]').click(timeout=10000)
    except BrowserError:
        # El usuario puede completar el acceso mientras se procesa el formulario.
        esperar_sesion(pagina)
        return
    finally:
        secreto = None
        correo = None
    try:
        pagina.wait_for_url("https://www.linkedin.com/feed/**", timeout=15000)
    except BrowserTimeout:
        esperar_sesion(pagina)
    if not sesion_iniciada(pagina):
        esperar_sesion(pagina)
    print("Sesión de LinkedIn iniciada.")




def leer_tarjetas(pagina, limite):
    """Abre tarjetas de la búsqueda nueva para obtener su enlace canónico."""
    tarjetas = pagina.get_by_role("button", name=re.compile(r".+ Dismiss .+ job"))
    if not tarjetas.count():
        return []
    urls = []
    for indice in range(min(tarjetas.count(), 50)):
        tarjetas = pagina.get_by_role("button", name=re.compile(r".+ Dismiss .+ job"))
        if indice >= tarjetas.count():
            break
        anterior = pagina.url
        tarjetas.nth(indice).click(timeout=10000)
        if indice:
            pagina.wait_for_url(lambda url: str(url) != anterior and "currentJobId=" in str(url), timeout=15000)
        else:
            pagina.wait_for_url(lambda url: "currentJobId=" in str(url), timeout=15000)
        urls = enlaces_busqueda(urls + [pagina.url])
        if len(urls) >= limite:
            break
    return urls[:limite]


def _texto_visible(pagina, selectores):
    for selector in selectores:
        try:
            elemento = pagina.locator(selector).filter(visible=True).first
            texto = elemento.inner_text(timeout=1200).strip()
            if texto:
                return texto
        except BrowserError:
            continue
    return ""


def _atributo(pagina, selector, nombre):
    try:
        elementos = pagina.locator(selector)
        return elementos.first.get_attribute(nombre, timeout=1200) if elementos.count() else ""
    except BrowserError:
        return ""


def leer_detalle(pagina):
    """Lee los metadatos públicos y el contenido visible de un aviso."""
    try:
        estructurado = extraer(pagina.content())
        if estructurado.empresa and estructurado.puesto and estructurado.descripcion:
            if not estructurado.fecha_publicacion:
                tiempo = _atributo(pagina, "time[datetime]", "datetime") or ""
                fecha = tiempo[:10] if re.match(r"^\d{4}-\d{2}-\d{2}", tiempo) else ""
                estructurado = Aviso(estructurado.empresa, estructurado.puesto, estructurado.descripcion, fecha)
            return estructurado
    except ValueError:
        pass

    titulo = _texto_visible(pagina, ["h1", ".job-details-jobs-unified-top-card__job-title"])
    empresa = _texto_visible(pagina, [
        ".job-details-jobs-unified-top-card__company-name",
        ".jobs-unified-top-card__company-name",
        ".topcard__org-name-link",
        '[data-test-id="job-details-company-name"]',
        'a[href*="/company/"]',
    ])
    descripcion = _texto_visible(pagina, [
        "#job-details",
        ".jobs-description__content",
        ".show-more-less-html__markup",
        ".jobs-box__html-content",
    ])

    titulo_meta = ""
    titulo_meta = _atributo(pagina, 'meta[property="og:title"]', "content")
    titulo_pagina = pagina.title().strip()
    candidatos = [titulo_meta, titulo_pagina]
    for candidato in candidatos:
        partes = [parte.strip() for parte in candidato.split("|") if parte.strip()]
        partes = [parte for parte in partes if parte.casefold() not in {"linkedin", "jobs", "empleos"}]
        if not titulo and partes:
            titulo = partes[0]
        if not empresa and len(partes) > 1:
            empresa = partes[1]
        if titulo and empresa:
            break
    if not descripcion:
        descripcion = _atributo(pagina, 'meta[name="description"]', "content") or ""

    tiempo = _atributo(pagina, "time[datetime]", "datetime") or ""
    fecha = tiempo[:10] if re.match(r"^\d{4}-\d{2}-\d{2}", tiempo) else ""
    if not all((titulo, empresa, descripcion)):
        raise ValueError("LinkedIn no expuso empresa, puesto y descripción completos.")
    return Aviso(empresa, titulo, descripcion, fecha)


def buscar(perfil, palabras, ubicacion, limite, simular, importar):
    perfil.mkdir(parents=True, exist_ok=True)
    os.chmod(perfil, 0o700)
    with sync_playwright() as playwright:
        contexto = playwright.chromium.launch_persistent_context(str(perfil), headless=False)
        try:
            pagina = contexto.new_page()
            iniciar_sesion(pagina)
            pagina.goto("https://www.linkedin.com/jobs/search/?" + urlencode(
                {"keywords": palabras, "location": ubicacion}
            ), wait_until="domcontentloaded")
            enlaces = pagina.locator('a[href*="/jobs/view/"], a[href*="currentJobId="]')
            tarjetas = pagina.locator('[data-job-id], [data-occludable-job-id]')
            pagina.locator(
                'a[href*="/jobs/view/"], a[href*="currentJobId="], [data-job-id], [data-occludable-job-id]'
            ).first.wait_for(state="attached", timeout=30000)
            urls = leer_tarjetas(pagina, limite)
            hrefs = list(urls)
            sin_cambios = 0
            cantidad_anterior = 0
            for intento in range(12):
                hrefs.extend(pagina.locator(
                    'a[href*="/jobs/view/"], a[href*="currentJobId="], [data-job-id], [data-occludable-job-id]'
                ).evaluate_all("""elements => elements.flatMap(element => {
                    const values = [];
                    const href = element.getAttribute("href");
                    if (href) values.push(href);
                    const id = element.getAttribute("data-job-id") ||
                               element.getAttribute("data-occludable-job-id");
                    if (id && /^[0-9]+$/.test(id)) values.push("/jobs/view/" + id + "/");
                    return values;
                })"""))
                urls = enlaces_busqueda(hrefs)
                if len(urls) >= limite:
                    break
                sin_cambios = sin_cambios + 1 if len(urls) == cantidad_anterior else 0
                if sin_cambios >= 4:
                    break
                cantidad_anterior = len(urls)
                pagina.locator(
                    '[data-job-id], [data-occludable-job-id], a[href*="/jobs/view/"], a[href*="currentJobId="]'
                ).evaluate_all("""elements => {
                    const last = elements[elements.length - 1];
                    if (last) last.scrollIntoView({block: "end"});
                }""")
                # LinkedIn carga tarjetas adicionales después del desplazamiento.
                pagina.wait_for_timeout(1000)
            urls = urls[:limite]
            print(f"Avisos identificados en resultados: {len(urls)}")
            if not urls:
                raise ValueError("LinkedIn mostró resultados, pero no se pudieron identificar sus avisos.")
            if simular:
                print(*urls, sep="\n")
                return len(urls)

            def leer(url):
                pagina.goto(url, wait_until="domcontentloaded")
                return leer_detalle(pagina)

            return importar(dict.fromkeys(urls, palabras), lector=leer)
        finally:
            contexto.close()


def reintentar_lecturas(perfil, urls, importar):
    """Vuelve a leer detalles de links incompletos usando la sesión local."""
    perfil.mkdir(parents=True, exist_ok=True)
    os.chmod(perfil, 0o700)
    with sync_playwright() as playwright:
        contexto = playwright.chromium.launch_persistent_context(str(perfil), headless=False)
        try:
            pagina = contexto.new_page()
            iniciar_sesion(pagina)

            def leer(url):
                pagina.goto(url, wait_until="domcontentloaded")
                return leer_detalle(pagina)

            return importar(dict.fromkeys(urls, "reintento de lectura"), lector=leer)
        finally:
            contexto.close()
