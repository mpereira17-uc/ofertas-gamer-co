---
name: seguridad-antes-de-lanzar
description: Use before publishing or changing any page, script, bot or workflow of pepe's projects (Ofertas Gamer CO, Renal COIL). Runs the 20-point security checklist and reports what applies.
---

# Revisión de seguridad antes de lanzar (20 puntos)

pepe pidió (2026-10-28) que esta lista se tenga en cuenta siempre, en cada página. Antes de dar por terminado un cambio, revisar los puntos que apliquen y decir en una línea cuáles se comprobaron. Si un punto no aplica (por ejemplo, el sitio es estático y no tiene base de datos), no inventar trabajo: basta con saberlo.

1. **Permisos**: cada token, secret y GitHub Action tiene solo los permisos que necesita (`permissions:` mínimos en los workflows).
2. **Panel admin**: no hay páginas de administración ni de estado públicas que expongan datos internos o errores con detalles sensibles.
3. **Datos entre clientes**: los datos de un visitante (localStorage, seguimiento en Renal COIL) nunca se mezclan ni se envían a otros.
4. **Base de datos blindada**: si existe (KV, D1), sin acceso público y con consultas parametrizadas.
5. **Claves privadas**: ninguna clave, token ni contraseña en el código, el HTML, los commits o los logs. Siempre en GitHub Secrets. Revisar el diff antes de cada push.
6. **Inicio de sesión seguro**: si hay login, por un proveedor confiable; nunca guardar contraseñas propias.
7. **Sesiones que caducan**: tokens y sesiones con expiración.
8. **Doble factor**: recordar a pepe tener 2FA en GitHub, Cloudflare, Ko-fi, PayPal, Discord, Telegram y correo.
9. **Inyecciones (SQL/HTML)**: escapar todo texto que venga de APIs externas (nombres de juegos, descripciones, títulos) antes de meterlo en el HTML. Nada de `innerHTML` con datos sin limpiar.
10. **Código malicioso**: no cargar scripts de dominios desconocidos; fijar versiones exactas de CDN y usar `integrity` cuando se pueda. Revisar todo plugin o skill externo antes de instalarlo.
11. **Acciones sensibles**: publicar en redes, borrar o cobrar requiere confirmación o un paso explícito.
12. **Archivos subidos**: si una página acepta archivos (importar en Renal COIL), validar tipo y tamaño y no ejecutar su contenido.
13. **Accesos internos bloqueados**: no exponer endpoints internos, carpetas de datos privados ni archivos de configuración en `docs/`.
14. **Webhooks verificados**: todo webhook entrante (Ko-fi, Discord, etc.) comprueba su firma o token.
15. **Pagos duplicados**: si hay pagos (Ko-fi), no procesar dos veces el mismo evento.
16. **Limitar solicitudes**: respetar los límites de las APIs (Steam, CheapShark, GamerPower, Tumblr, Bluesky) y no permitir abusos de formularios.
17. **Dependencias al día**: versiones fijadas en `requirements` y CDN, actualizadas cuando hay fallos de seguridad conocidos.
18. **Paneles expuestos**: ningún panel de Cloudflare, analítica o bot accesible sin login.
19. **Accesos sospechosos**: revisar de vez en cuando los avisos de seguridad de GitHub y los logs de las Actions.
20. **Probar restaurar backups**: el historial de git es el backup; para datos (`data/*.json`, export de Renal COIL) comprobar que se pueden restaurar.

Enlaces externos a sitios de terceros (tiendas, afiliados): usar `rel="noopener"` y, en afiliados, `rel="sponsored"`.
