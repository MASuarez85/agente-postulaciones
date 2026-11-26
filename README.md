# Agente de postulaciones

## Documentación del producto

- [PRD](docs/PRD.md): objetivos, alcance y requisitos del agente.
- [RFC](docs/RFC.md): arquitectura propuesta y reglas de operación.
- [Changelog](docs/CHANGELOG.md): cambios relevantes del producto y su diseño.

El PRD y el RFC describen el producto objetivo y su arquitectura; no implican que todas esas capacidades ya estén implementadas. El prototipo actual permite buscar en LinkedIn con una configuración de palabras clave por usuario, evaluar los avisos encontrados con Claude y registrarlos para revisión. La programación diaria, otros portales, la preparación con IA y el envío automático siguen pendientes. La demo usa datos ficticios y no necesita credenciales ni paquetes externos.

```sh
python3 main.py --demo
```

El proyecto apunta a Python 3.12. La demo también funciona con Python 3.9.

Para completar la fase de registro queda conectar Google Sheets, configurar la planilla del agente e identificar la pestaña y las columnas de empresa, rol y enlace del historial. El módulo de historial solo recibe filas para consulta. El acceso real a la planilla histórica deberá configurarse en modo lectura.

## Consultar el historial de Google Sheets

La pestaña `Postulaciones` usa los encabezados `Empresa`, `Puesto` y `Enlace`.
La consulta carga las filas una vez por ejecución y aplica el filtro existente.

1. Instalá las dependencias en tu entorno virtual con `python -m pip install -r requirements.txt`.
2. Compartí la planilla con el correo de la cuenta de servicio como **Lector**.
3. Copiá `.env.example` a `.env` y completá la ruta absoluta de la clave JSON en
   `GOOGLE_SERVICE_ACCOUNT_FILE`. Poné la ruta entre comillas si tiene espacios.
4. Desde la carpeta del proyecto, ejecutá:

```sh
set -a
source ./.env
set +a
python main.py --consultar-historial "Empresa" "Puesto" "https://www.linkedin.com/jobs/view/123/"
```

## Registro operativo

Compartí la planilla del agente con la cuenta de servicio como **Editor**.
El historial se consulta con permisos de lectura y sus encabezados se configuran en `Config`.
Cargá las variables de `.env` como arriba y ejecutá:

```sh
.venv/bin/python main.py --listar-registro
.venv/bin/python main.py --registrar-aviso "Empresa" "Puesto" "https://www.linkedin.com/jobs/view/123/"
```

Los avisos nuevos ingresan en `revisar` hasta que exista el análisis de elegibilidad y compatibilidad.
Los parámetros de puntaje, recordatorio y límite diario quedan preparados para las fases que los aplican.

## CV maestro

El borrador privado `datos/cv_maestro.yaml` se armó a partir del CV base en español.
Está escrito en sintaxis JSON, que es válida en YAML y permite leerlo sin dependencias adicionales.
Para verificar empresas, cargos y fechas contra la exportación oficial de LinkedIn:

```sh
.venv/bin/python main.py --validar-cv "/ruta/a/Positions.csv"
```

Cada discrepancia se informa por ID de experiencia. El chequeo de habilidades y logros de
los documentos generados, la redacción y la generación de PDFs quedan pendientes.

## Generar CV y carta

Guardá el texto del aviso en un archivo UTF-8. Instalá las dependencias actualizadas y ejecutá:

```sh
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py --generar "Empresa" "Puesto" "/ruta/aviso.txt"
```

Los dos PDFs se crean juntos en `salida/`, en una carpeta por empresa, puesto y fecha.
Podés usar `--salida` para elegir otro directorio. El generador produce borradores en
español. Prioriza habilidades y logros mediante coincidencias de texto y toma las
afirmaciones sobre tu experiencia directamente del CV maestro. La generación de PDFs
sigue basada en plantillas; Claude se usa en el análisis de compatibilidad descrito más
abajo. Drive y el flujo de aprobación siguen pendientes.

El CV usa el encabezado de contacto, perfil profesional, experiencia principal,
experiencia técnica anterior y habilidades y formación de los ejemplos de Tether.
La carta usa el mismo encabezado y adapta el asunto, el saludo y los ejemplos
de experiencia a cada aviso. Los datos profesionales se toman del CV maestro.

## Buscar avisos y evaluar con Claude

El agente puede buscar avisos en LinkedIn usando palabras clave configuradas por persona,
leerlos, consultar el historial, evaluar compatibilidad con Claude y cargar los nuevos en
la planilla como pendientes de revisión. Todavía no envía postulaciones. Por ahora
LinkedIn es el único portal conectado. Copiá `.env.example` a `.env`, configurá
`ANTHROPIC_API_KEY` y cargá las variables antes de ejecutar. El modelo se puede cambiar
con `ANTHROPIC_MODEL`.

```sh
.venv/bin/python -m pip install -r requirements.txt
set -a
source ./.env
set +a
```

Copiá la plantilla de búsqueda y completá tus términos, ubicación y contexto:

```sh
if [ ! -f datos/busqueda.json ]; then cp configuracion/busqueda.example.json datos/busqueda.json; fi
```

Luego ejecutá la búsqueda. Cada palabra clave realiza una consulta independiente; `--limite`
controla la cantidad máxima de avisos por consulta.

```sh
.venv/bin/python main.py --buscar-config datos/busqueda.json --limite 5
```

Para previsualizar los enlaces sin registrar ni evaluar avisos, agregá `--simular`.
También podés hacer una búsqueda puntual pasando términos por CLI con `--buscar-linkedin`.

```sh
.venv/bin/python main.py --buscar-linkedin "Engineering Manager" \\
  --contexto-archivo datos/contexto_busqueda.txt --limite 10
```

Para volver a leer filas anteriores que hayan quedado sin empresa o puesto, ejecutá:

```sh
.venv/bin/python main.py --reintentar-incompletos
```

La fecha se lee del aviso cuando LinkedIn la expone. Los anuncios de más de siete días
se descartan; si no hay fecha verificable, el agente registra la evaluación como revisión
pendiente y no permite postular automáticamente.

La solicitud envía a Anthropic el contexto, la descripción del aviso y solo los datos
profesionales del CV; excluye datos de contacto y exige citas literales para la evidencia.
El programa verifica esas citas en local y marca la evaluación para revisión si alguna
no se encuentra. Si falta la fecha, el resultado también queda en revisión.

Para evaluar manualmente un archivo de aviso, sin búsqueda, usá:

```sh
set -a
source ./.env
set +a
.venv/bin/python main.py --evaluar-aviso "$HOME/Downloads/aviso.txt" \\
  --contexto-archivo datos/contexto_busqueda.txt
```

El contexto de búsqueda es un archivo de texto opcional. La solicitud envía a Anthropic
el contexto, la descripción del aviso y solo los datos profesionales del CV; excluye
datos de contacto y exige citas literales para la evidencia. El programa verifica esas
citas en local y marca la evaluación para revisión si alguna no se encuentra. Pasá
`--publicado-en` únicamente con la fecha verificada en la fuente; fechas fuera de la
ventana de siete días se bloquean sin llamar al modelo. Sin una fecha verificada, el
resultado queda en revisión. Esta primera etapa no habilita el envío automático.

## Primera versión asistida

Desde la carpeta del proyecto, cargá la configuración con
`set -a; source ./.env; set +a`. Guardá la descripción de un aviso como texto plano
y ejecutá:

```sh
.venv/bin/python main.py --preparar "Empresa" "Puesto" "https://www.linkedin.com/jobs/view/123/" "$HOME/Downloads/aviso.txt"
```

El agente consulta el registro y el historial antes de generar. Un ID repetido
se omite. Para filas históricas sin ID de LinkedIn se compara empresa y puesto.
Un antecedente en la misma empresa para otro aviso pasa a `revisar`.
Si el aviso es nuevo, genera ambos PDFs locales y registra su carpeta en notas.
Revisá la vigencia, la elegibilidad desde Argentina y los documentos, confirmá
en Sheets y completá la postulación en LinkedIn. Después actualizá el estado y
la fecha en Sheets. La ingesta autónoma de Gmail, Drive y los avisos por correo
quedan fuera de esta primera versión manual.

### Carga automática desde Gmail

En el proyecto de Google Cloud habilitá Gmail API y descargá un cliente OAuth
de tipo **Aplicación de escritorio** como `credenciales/gmail-oauth.json`.
Si la audiencia está en modo de prueba, agregá tu cuenta como usuario de prueba.
Autorizá Gmail desde Terminal una vez. Para consultar la última semana:

```sh
.venv/bin/python main.py --autorizar-gmail
set -a
source ./.env
set +a
.venv/bin/python main.py --importar-alertas 7 --simular
.venv/bin/python main.py --importar-alertas 7
```

La importación registra enlaces nuevos como `revisar` y omite los IDs de
LinkedIn que ya existen en el registro o en el historial. El asunto de la
alerta queda en notas. La revisión del anuncio y el envío siguen siendo manuales.

La búsqueda de LinkedIn ahora comprueba la sesión antes de buscar. Cuando requiere
ingresar, recupera el correo y la contraseña del Llavero de macOS y completa el
formulario de LinkedIn. Si aparece una verificación, completala en el navegador
y presioná Enter en Terminal. Una sesión válida se reutiliza en búsquedas posteriores.

## Estado de esta versión

Python 3.12. Búsqueda directa en LinkedIn, sesión con Llavero de macOS,
lectura del aviso, exclusión por historial y carga en Google Sheets con notas breves.
Los PDFs se generan localmente en español. La postulación automática sigue pendiente.

Para instalar en otro equipo, creá un entorno virtual con Python 3.12, instalá
requirements.txt y ejecutá python -m playwright install chromium. Copiá .env.example
a .env y completá los IDs y la ruta de las credenciales de Google. El CV maestro
y las credenciales se configuran localmente.

## Interfaz web local

También podés usar el agente desde una página web local. La interfaz se limita a tu computadora y utiliza las mismas variables de entorno y conexiones de Google Sheets que los comandos existentes.

1. Activá el entorno virtual e instalá las dependencias:

```sh
python -m pip install -r requirements.txt
```

2. Cargá las variables definidas en `.env` y abrí la interfaz:

```sh
set -a
source ./.env
set +a
python main.py --web
```

3. Abrí <http://127.0.0.1:8765> en el navegador. Para cerrar el servidor, presioná `Ctrl+C` en la terminal.

La página permite revisar y registrar avisos en la planilla operativa, consultar las oportunidades recientes y generar borradores de CV y carta en PDF. La instalación de `gspread` habilita Google Sheets y `reportlab` habilita la generación de documentos. Para generar documentos, también necesitás el archivo privado `datos/cv_maestro.yaml`. No ingreses credenciales en la página: se leen desde el archivo `.env` y la clave de cuenta de servicio configurados localmente.

## Interfaz web local

Iniciá la interfaz desde la carpeta del proyecto. Usa la configuración local de Google Sheets; la búsqueda interactiva en LinkedIn y la autorización de Gmail siguen ejecutándose desde Terminal.

```sh
set -a
source ./.env
set +a
.venv/bin/python main.py --web
```

Abrí <http://127.0.0.1:8765>. La interfaz permite registrar oportunidades, consultar el registro y generar borradores de CV y carta. El servidor escucha únicamente en tu computadora. Para generar documentos necesitás el CV maestro privado en `datos/cv_maestro.yaml`.
