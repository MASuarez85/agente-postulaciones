# Changelog

Cambios relevantes del producto y de su diseño técnico.

## 2026-11-24 — Primera versión del PRD y RFC

- Se definió el objetivo del agente: buscar avisos a diario, detectar duplicados, preparar y enviar postulaciones elegibles, y registrar el proceso.
- Se diseñó el producto para varios usuarios, con perfil, palabras clave y contexto de búsqueda aislados por persona.
- Se estableció el filtro de antigüedad: considerar avisos publicados durante los últimos siete días; no postular automáticamente si no se puede verificar la fecha.
- Se definió como objetivo cubrir todos los portales de empleo identificados, con catálogo visible de portales cubiertos, pendientes de integración o inaccesibles.
- Se documentaron las reglas de postulación automática, veracidad de datos, deduplicación, revisión de casos ambiguos y despliegue incremental.
- Se registraron decisiones pendientes sobre ejecución diaria, conectores iniciales, proveedor de IA, almacenamiento y notificaciones.

## 2026-11-24 — Incorporación al repositorio principal

- Se incorporaron el PRD, el RFC y este changelog al repositorio de Laburo.
- Se enlazaron los documentos desde el README y se aclaró que describen el producto objetivo, mientras que el código actual sigue siendo un prototipo.
