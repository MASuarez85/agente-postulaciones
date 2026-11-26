# PRD: Agente autónomo de búsqueda laboral

**Estado:** borrador para revisión  
**Fecha:** 24 de noviembre de 2026

## 1. Resumen

Construir un agente configurable por persona que busque oportunidades laborales a diario en portales de empleo, evalúe cuáles encajan con el perfil y el contexto de búsqueda que ingresó cada usuario, evite postulaciones duplicadas, prepare los materiales necesarios, complete y envíe las postulaciones elegibles, y mantenga actualizada la planilla de seguimiento.

Cada usuario puede habilitar que el agente se postule en su nombre. Cuando lo habilita, la postulación automática es el comportamiento esperado si el aviso y el formulario pueden resolverse con información verificada. El agente debe detenerse y pedir intervención ante datos ambiguos, declaraciones no verificadas o verificaciones que no pueda completar.

## 2. Problema

La búsqueda diaria, la revisión de avisos, la adaptación de documentos y la carga de resultados son tareas repetitivas. Hoy el proyecto permite configurar palabras clave y contexto para buscar en LinkedIn, evaluar avisos nuevos con Claude, consultar duplicados y registrar los resultados para revisión. Todavía no ejecuta búsquedas diarias programadas ni cubre varios portales; tampoco completa y envía postulaciones automáticamente.

## 3. Usuarios y objetivo

- **Usuarios:** personas que buscan empleo y configuran su propio perfil y contexto de búsqueda.
- **Objetivo:** reducir el trabajo manual de búsqueda y postulación, manteniendo exactitud en los datos presentados y visibilidad sobre cada acción.

## 4. Perfil y contexto de búsqueda

Cada persona configura un perfil separado. El agente debe recibir palabras clave y contexto libre para entender qué posiciones buscar. Puede incluir, por ejemplo:

- Títulos o tipos de puesto buscados, seniority, áreas, industrias, tecnologías o capacidades relevantes.
- Preferencias y exclusiones, como ubicación, modalidad, jornada, idioma o tipo de rol.
- Contexto libre para resolver ambigüedades y distinguir puestos parecidos.
- Hechos profesionales verificados y respuestas aprobadas para formularios.

El agente puede ampliar términos con sinónimos y títulos relacionados para descubrir avisos pertinentes, pero debe conservar el contexto del usuario y mostrar por qué considera relevante cada resultado. No debe añadir criterios excluyentes que el usuario no configuró.

## 5. Alcance funcional

1. Ejecutar una búsqueda diaria con cobertura objetivo de todos los portales de empleo identificados. Mantener un catálogo visible de portales cubiertos, pendientes de integración o inaccesibles; recoger avisos nuevos de los que tengan conectores operativos.
2. Incluir únicamente avisos publicados durante los últimos siete días. Si no se puede verificar la fecha de publicación, no postular automáticamente.
3. Extraer empresa, puesto, ubicación/modalidad, requisitos, compensación si figura, fuente, enlace y fecha.
4. Detectar duplicados exactos por ID/enlace y posibles duplicados por empresa y puesto. Los posibles duplicados se marcan para revisión; no se descartan silenciosamente.
5. Aplicar los criterios configurados por cada usuario y evaluar compatibilidad explicando los requisitos que respaldan la decisión.
6. Generar o adaptar CV, carta y respuestas de formulario usando el CV y los datos aprobados del usuario.
7. Completar y enviar automáticamente las postulaciones que superen las reglas de elegibilidad y cuyos campos tengan respuestas verificadas.
8. Registrar cada aviso, evaluación, documentos, fecha y resultado en la planilla de seguimiento de ese usuario.
9. Informar fallas, solicitudes de intervención y postulaciones completadas.

## 6. Fuera de alcance inicial

- Contactar recruiters por correo, LinkedIn u otros canales.
- Inventar o inferir hechos profesionales para completar formularios.
- Sortear CAPTCHA, autenticación multifactor u otros controles de acceso.
- Postularse a avisos cuya fecha supere los siete días, sea desconocida o cuya fuente o flujo no permita una interacción estable y autorizada.
- Reemplazar el criterio del usuario sobre preferencias sensibles o respuestas legales no preaprobadas.

## 7. Requisitos de confianza y control

- La postulación automática está habilitada para los casos que cumplen las reglas configuradas.
- Si falta un dato, una respuesta requiere una afirmación no aprobada o el resultado del envío es incierto, el estado pasa a `requiere revisión`; no se reintenta un envío incierto a ciegas.
- Conservar evidencia del aviso y una explicación breve de la decisión.
- Proteger CV, datos personales, credenciales y respuestas; no incluir secretos ni contenido sensible en logs.
- Aislar perfil, credenciales, CV, planilla e historial por usuario.
- El usuario puede pausar el agente, cambiar contexto y criterios, y revisar el historial de acciones.

## 8. Métricas de éxito

- Búsquedas diarias ejecutadas y avisos nuevos detectados por fuente.
- Cobertura de portales habilitados y proporción de avisos con fecha de publicación verificable.
- Porcentaje de resultados dentro de la ventana de siete días.
- Duplicados evitados y posibles duplicados enviados a revisión.
- Proporción de postulaciones enviadas sin corrección de datos por parte del usuario.
- Errores de postulación, formularios incompletos y casos que requieren intervención.
- Tiempo ahorrado frente al flujo manual.

El objetivo de calidad más importante es **cero afirmaciones falsas en postulaciones**; las métricas de volumen no deben incentivar envíos de baja calidad.

## 9. Decisiones pendientes para cerrar el PRD

- Catálogo y orden de incorporación de portales, según disponibilidad de interfaces de acceso estables y autorizadas.
- Dónde se ejecutará el proceso diario y cómo operará cuando el dispositivo del usuario esté apagado.
- Datos de perfil y respuestas preaprobadas que necesita cada usuario antes de permitir postulaciones automáticas.
- Qué formularios y tipos de declaración requieren revisión obligatoria.
- Canal y frecuencia de notificaciones sobre resultados o bloqueos.
