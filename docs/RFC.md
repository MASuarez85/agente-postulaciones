# RFC: Arquitectura del agente autónomo de postulaciones

**Estado:** borrador para revisión  
**Fecha:** 24 de noviembre de 2026  
**Relacionado:** [PRD](PRD.md)

## 1. Resumen

Evolucionar la aplicación local actual hacia un agente configurable por usuario que ejecute un flujo diario de búsqueda en portales de empleo, análisis, deduplicación, preparación, postulación y registro. Buscar avisos publicados en los últimos siete días. Combinar reglas determinísticas para políticas y datos estructurados con un modelo de lenguaje para interpretar el contexto escrito por cada persona, avisos y formularios no estructurados. El modelo decide entre herramientas permitidas y el flujo valida cada acción antes de ejecutarla.

## 2. Estado actual

El proyecto contiene interfaz local, flujos para buscar en LinkedIn e importar alertas de Gmail, conexión de lectura/escritura con Google Sheets, deduplicación y generación de PDFs por coincidencia de palabras clave. Antes de incorporar este RFC, el README mencionaba una versión v1.1. La búsqueda diaria en varios portales, la evaluación integral de elegibilidad y compatibilidad y el envío automático siguen pendientes. La generación actual no usa un modelo de IA.

## 3. Arquitectura propuesta

### Componentes

- **Programador:** inicia una ejecución diaria y permite lanzamientos manuales y pausa/reanudación.
- **Catálogo de portales y adaptadores:** un registro extensible de todos los portales de empleo identificados, con su estado (cubierto, pendiente de integración o inaccesible). Cada adaptador obtiene avisos, fecha de publicación y datos de postulación, y los convierte a un formato común; declara cobertura, método de acceso, límites y errores. El objetivo es integrar todos los portales; una búsqueda solo puede cubrir automáticamente los que tengan un conector operativo y acceso permitido.
- **Perfil por usuario:** almacena de forma aislada perfil profesional, CV, respuestas aprobadas y contexto de búsqueda ingresado como palabras clave y texto libre.
- **Expansor de búsqueda:** propone sinónimos y títulos relacionados a partir del contexto del usuario para ampliar consultas sin alterar sus preferencias. Conserva los términos originales para explicar coincidencias.
- **Coordinador/agente:** recibe el objetivo y contexto de búsqueda, consulta herramientas y avanza aviso por aviso hasta un resultado terminal o un bloqueo.
- **Modelo:** extrae requisitos y datos del aviso, clasifica compatibilidad, prepara respuestas y devuelve resultados estructurados con evidencia. No tiene acceso directo a credenciales ni ejecuta acciones externas sin pasar por herramientas validadas.
- **Herramientas:** buscar/leer aviso, consultar CV y perfil aprobado, consultar historial, generar documentos, completar formularios, enviar postulación y actualizar planilla.
- **Perfil y políticas:** fuente versionada de hechos del candidato, preferencias, filtros y respuestas aprobadas para formularios.
- **Registro de ejecución:** mantiene estado, trazas resumidas, evidencia y resultados para poder reanudar sin duplicar acciones.
- **Google Sheets:** conserva la planilla operativa visible para el usuario y refleja cada estado importante.
- **Interfaz:** permite configurar el perfil y contexto, ver la cobertura y estado de portales, horario y planilla; revisar pendientes; ver resultados; pausar el agente.

### Flujo

`programar → buscar en portales → normalizar → validar antigüedad → deduplicar → evaluar con contexto de usuario → preparar → validar → postular → registrar resultado`

Las herramientas pueden ejecutarse en etapas, pero las transiciones de estado y reglas de seguridad son determinísticas. El modelo puede pedir herramientas o derivar a revisión, pero no saltarse esas transiciones.

## 4. Estado de cada aviso

Estados recomendados: `detectado`, `duplicado`, `posible_duplicado`, `no_elegible`, `requiere_revision`, `listo_para_postular`, `enviando`, `postulado`, `error`.

- Duplicado exacto: no enviar otra postulación.
- Coincidencia aproximada: no descartar ni postular automáticamente hasta resolverla.
- Elegibilidad incumplida: registrar motivo y no continuar.
- Todos los datos verificados: permitir envío automático según la autorización del usuario.
- Respuesta desconocida, captcha, MFA, campo legal no aprobado o error ambiguo: detener, guardar el estado y solicitar intervención.

## 5. Antigüedad y búsqueda contextual

- Usar la fecha de publicación indicada por el portal cuando sea verificable; normalizarla a fecha y hora con zona horaria conocida.
- Considerar elegible para búsqueda solo el aviso publicado entre el momento de ejecución y los siete días anteriores, inclusive.
- Si falta la fecha o hay fechas contradictorias, marcar `requiere_revision` y no enviar una postulación automática.
- Ejecutar consultas con las palabras clave y el contexto de cada usuario. El modelo puede proponer sinónimos/títulos cercanos, guardar qué consulta encontró el aviso y explicar la correspondencia.
- Mantener visible la cobertura por portal; el sistema no debe presentar como búsqueda exhaustiva una ejecución que omitió portales por falta de conector o acceso.
- No convertir la falta de resultados en autorización para relajar filtros. Ofrecer la expansión como resultado del análisis o aplicar solo expansiones semánticas que respeten el contexto escrito.
- Ejecutar la búsqueda diaria en la zona horaria configurada por cada usuario.

## 6. Reglas de deduplicación e idempotencia

Aplicar en orden: ID externo estable, URL canónica, luego empresa y puesto normalizados. Las coincidencias aproximadas producen `posible_duplicado` y nunca provocan descarte silencioso. Antes de enviar, escribir un estado de intención en el registro. Reintentar automáticamente solo si se puede demostrar que el sitio no recibió la postulación; un resultado incierto requiere conciliación manual.

## 7. Envío y límites de automatización

- La cuenta y la sesión del usuario se gestionan localmente; no guardar contraseñas en la planilla ni en logs.
- Usar interfaces o integraciones permitidas por cada fuente. No eludir CAPTCHA, MFA, controles antiabuso ni restricciones de acceso.
- Enviar solo con respuestas sustentadas por el perfil aprobado o por el propio aviso. Nunca fabricar experiencia, educación, permiso laboral, salario u otras declaraciones.
- Tratar consentimientos, declaraciones legales y preguntas no contempladas como bloqueo de revisión, salvo que exista una respuesta explícitamente preaprobada.
- Registrar enlace, fecha, documentos utilizados, respuesta del sitio y motivo de cualquier bloqueo.

## 8. Evaluación del puesto

Usar dos capas:

1. **Filtros determinísticos:** preferencias explícitas, restricciones laborales y condiciones configuradas.
2. **Evaluación del modelo:** resumir requisitos, comparar evidencias del perfil, señalar brechas y devolver una recomendación estructurada con confianza y citas al texto del aviso.

La confianza no reemplaza reglas duras. Una evaluación con datos incompletos debe ir a revisión, no convertirse automáticamente en postulación.

## 9. Privacidad, seguridad y observabilidad

- Mantener credenciales fuera del código y de Google Sheets.
- Limitar acceso de cada cuenta de Sheets al documento del usuario correspondiente.
- Aislar por usuario todas las credenciales, perfiles, documentos, historial, ejecuciones y resultados.
- Guardar logs operativos mínimos; no almacenar páginas completas con información personal si basta con URL, extracto y decisión.
- Proteger secretos en configuración local y evitar exponer la interfaz fuera de localhost en el modo local.
- Registrar por ejecución: fuente, etapa, herramienta, resultado, motivo y duración; redactar datos personales y secretos.
- Permitir detener una ejecución entre avisos y evitar acciones paralelas sobre el mismo aviso.

## 10. Despliegue incremental

1. **Observación:** búsqueda diaria, extracción y deduplicación; el agente recomienda y actualiza la planilla sin enviar postulaciones.
2. **Preparación:** genera documentos y completa formularios hasta el último paso, verificando datos y guardando el estado.
3. **Envío automático acotado:** habilitar envío para fuentes y tipos de formulario validados; los demás quedan en revisión.
4. **Ampliación:** incorporar fuentes solo tras medir calidad de extracción, deduplicación, formularios y recuperación ante fallas.

Este despliegue gradual no cambia el objetivo final de postular automáticamente; reduce el riesgo mientras se valida cada integración.

## 11. Decisiones técnicas abiertas

- Catálogo inicial y orden de incorporación de portales; método de acceso por API, feeds públicos, alertas o automatización de navegador por portal.
- Tratamiento de publicaciones con fecha relativa ambigua o zonas horarias no informadas.
- Ejecución local diaria frente a un servicio siempre activo.
- Biblioteca/modelo y proveedor de IA, considerando costo, privacidad y salida estructurada.
- Almacenamiento de estado durable y estrategia de sincronización con Google Sheets.
- Navegador automatizado y manejo de sesiones por usuario sin almacenar contraseñas.
- Esquema de planilla por usuario y mecanismo de notificación.

## 12. Criterios de aceptación del RFC

- Las consultas de un usuario usan su contexto y no mezclan datos de otras personas.
- Ninguna postulación automática usa un aviso con más de siete días o fecha no verificable.
- Cada aviso registra qué portal y consulta lo encontraron.
- Cada aviso conserva procedencia, evidencia de evaluación y estado recuperable.
- Un aviso ya postulado no puede enviarse otra vez por reejecución normal.
- Los duplicados aproximados y los formularios ambiguos se bloquean para revisión.
- El sistema no envía postulaciones con afirmaciones no verificadas.
- Un fallo de fuente o de conexión no borra ni duplica el estado existente.
- Cada usuario puede pausar el proceso y consultar qué buscó, qué envió y qué quedó pendiente.
