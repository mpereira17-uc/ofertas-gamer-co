# Ofertas gamer Colombia

Bot que cada 4 horas busca juegos gratis (Epic Games) y ofertas fuertes (Steam, GOG, Humble,
Green Man Gaming) con el precio en pesos colombianos. Hace dos cosas:

1. Publica las novedades en un canal de Telegram.
2. Actualiza una página web (GitHub Pages) para que la gente llegue desde Google.

Corre gratis en GitHub Actions. No hace falta tener el computador prendido.

## Puesta en marcha (una sola vez)

1. **Canal de Telegram**: crea un canal público (por ejemplo `@ofertasgamerco`).
2. **Bot**: en Telegram abre `@BotFather`, envía `/newbot` y guarda el *token* que te da.
   Agrega el bot como administrador del canal.
3. **Secretos en GitHub**: en el repositorio, ve a *Settings → Secrets and variables → Actions → New repository secret*:
   - `TELEGRAM_BOT_TOKEN`: el token del bot (no lo compartas con nadie).
   - `TELEGRAM_CHAT_ID`: el nombre del canal con `@`, por ejemplo `@ofertasgamerco`.
4. **Página web**: *Settings → Pages → Branch: `main`, carpeta `/docs`*.
5. **Probar**: pestaña *Actions → Buscar y publicar ofertas → Run workflow*.

## Ajustes (`config.json`)

- `precio_maximo_usd`, `descuento_minimo`, `metacritic_minimo`: qué ofertas cuentan.
- `maximo_mensajes_por_ejecucion`: para no llenar el canal.
- `enlace_canal_telegram`: pon `https://t.me/tucanal` y aparece un botón en la web.
- `pie_de_mensaje`: texto al final de cada mensaje (por ejemplo, un enlace a Ko-fi).
- `afiliados`: cuando te aprueben en un programa de afiliados, aquí van tus enlaces por tienda.
  Mientras tanto, los enlaces pasan por CheapShark.

Fuentes: [CheapShark API](https://apidocs.cheapshark.com/), tienda de Epic Games y
[ExchangeRate-API](https://www.exchangerate-api.com/) para la tasa del dólar.
