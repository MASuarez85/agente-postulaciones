# Agente de postulaciones

Primer avance del RFC v1.1. El filtro local consulta un historial en memoria y decide si omitir, revisar o continuar con un aviso. La similitud de roles usa un umbral provisional de 0,8 y solo deriva a revisión. La demo usa datos ficticios y no necesita credenciales ni paquetes externos.

```sh
python3 main.py --demo
```

El RFC propone Python 3.12 para el proyecto. La demo también funciona con Python 3.9.

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
afirmaciones sobre tu experiencia directamente del CV maestro. No requiere una API de
IA. La integración con Claude, Drive y el flujo de aprobación sigue pendiente.

El CV usa el encabezado de contacto, perfil profesional, experiencia principal,
experiencia técnica anterior y habilidades y formación de los ejemplos de Tether.
La carta usa el mismo encabezado y adapta el asunto, el saludo y los ejemplos
de experiencia a cada aviso. Los datos profesionales se toman del CV maestro.

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
