# Ofertas Gamer CO

Juegos gratis y ofertas de PC de tiendas oficiales para Colombia y Latinoamérica.

- Sitio: https://ofertas-gamer-co.pages.dev/
- Telegram: https://t.me/ofertasgamerco

## Cómo funciona

```
GitHub Actions (cada 4 h, al cambiar main o a mano)
  → bot.py: Epic + CheapShark → validación → data/offers.json
  → Telegram (solo ofertas nuevas) y Discord opcional
  → ogc/site.py genera docs/: páginas, feeds, sitemap, whatsapp.html
  → scripts/check_site.py → commit si hay cambios → despliegue
```

| Carpeta / archivo | Qué contiene |
| --- | --- |
| `bot.py` | Orquestador (no necesita dependencias externas) |
| `ogc/` | Fuentes, modelo y validación, afiliados, canales, generador del sitio, textos |
| `config/site.json` | Nombre, URL, canales, filtros de ofertas, verificación de Google e Impact |
| `config/stores.json` | Tiendas autorizadas, dominios y estado de afiliación |
| `config/ads.json` | Espacios publicitarios (todos desactivados) |
| `data/offers.json` | Ofertas vigentes con todos sus campos |
| `data/telegram_publicados.json` | Registro para no repetir publicaciones |
| `docs/` | Sitio generado (no editar a mano) |
| `documentacion/` | Monetización, Cloudflare, operación y fuentes |

## Secretos (Settings → Secrets and variables → Actions)

| Nombre | Tipo | Obligatorio |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | Secret | Sí |
| `TELEGRAM_CHAT_ID` | Secret | Sí (`@ofertasgamerco`) |
| `TELEGRAM_ALERT_CHAT_ID` | Secret | No: chat privado para alertas del monitoreo |
| `DISCORD_WEBHOOK_URL` | Secret | No |
| `GMG_AFFILIATE_URL`, `FANATICAL_AFFILIATE_URL` | Variable | Solo cuando la red apruebe |

## Pruebas locales

```
python -m unittest discover -s tests -t .
python bot.py --fixtures tests/fixtures --no-send
python scripts/check_site.py
```

Para restaurar los datos reales después de una prueba local: `git checkout -- data docs`.
