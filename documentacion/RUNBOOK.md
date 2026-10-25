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
