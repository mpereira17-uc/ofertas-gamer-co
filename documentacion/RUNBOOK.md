# Operación diaria y recuperación

## Cómo funciona
`.github/workflows/actualizar-y-publicar.yml` corre cada 4 horas (minuto 17 UTC), al cambiar `main` y a mano. Ejecuta pruebas, `python bot.py`, `scripts/check_site.py`, guarda `data/` y `docs/` solo si cambiaron (`chore: actualizar ofertas automáticamente`) y despliega.

## Ejecutar a mano
Pestaña **Actions → Actualizar y publicar ofertas → Run workflow**.

## Si algo falla
- **Una fuente cae**: el bot conserva sus ofertas anteriores hasta 24 horas (`horas_retener_oferta_sin_confirmar`). La página `estado.html` lo muestra.
- **Todas las fuentes caen**: se conserva la versión anterior; nunca se publica una página vacía.
- **Fallan las comprobaciones**: no se guarda ni se despliega; queda la última versión buena.
- **Monitoreo**: `monitoreo.yml` revisa el sitio cada 6 horas y abre una incidencia con la etiqueta `monitoreo`.

## Volver a una versión anterior
La rama `backup-pre-monetizacion` guarda el estado previo a esta reestructuración. Para revertir un cambio puntual: `git revert <commit>` y push a `main`.

## Telegram
`data/telegram_publicados.json` guarda los identificadores ya enviados (máximo 3000). No lo borres o se repetirán publicaciones.

## Rotar el token del bot
En @BotFather: `/revoke` → nuevo token → actualízalo en **Settings → Secrets and variables → Actions**.

## Promoción automática

- **IndexNow** (Bing, Yandex y otros buscadores): está activo. En cada ejecución se avisa de las páginas nuevas. La clave pública está en `config/site.json` (`indexnow_key`) y se publica como `docs/<clave>.txt`.
- **Bluesky** (opcional): en Bluesky ve a Configuración → Privacidad y seguridad → Contraseñas de app y crea una. Luego, en GitHub, ve a Settings → Secrets and variables → Actions:
  - Variable `BLUESKY_HANDLE`, por ejemplo `ofertasgamerco.bsky.social`.
  - Secreto `BLUESKY_APP_PASSWORD`, con la contraseña de app que creaste.
- **Mastodon** (opcional): variable `MASTODON_URL` (ej. `https://mastodon.social`) y secreto `MASTODON_TOKEN`, con un token de app con permiso `write:statuses`.
- **Discord** (opcional): en el canal, Editar canal → Integraciones → Webhooks → Nuevo webhook → Copiar URL. Guárdala como secreto `DISCORD_WEBHOOK_URL` (nunca en el repositorio: quien la tenga puede escribir en el canal).
- En cada red se publican como máximo 3 ofertas por ejecución, solo las mejores (gratis, o 60 % de descuento con Metacritic de 70 o más). Cada post enlaza a la página propia de la oferta.
