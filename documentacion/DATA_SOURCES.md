# Fuentes de datos

| Fuente | Uso | Límites y términos |
| --- | --- | --- |
| Epic Games Store (`freeGamesPromotions`, país CO) | Juegos gratis y fechas | Endpoint público de la tienda; una consulta cada 4 horas. |
| CheapShark API (`/api/1.0/deals`) | Descuentos en Steam, GOG, Humble, GMG, Fanatical, Epic | API pública; una consulta cada 4 horas. Los precios son de referencia en USD (tienda de EE. UU.). Se acredita en `fuentes.html`. Revisar sus términos antes de aumentar la frecuencia. |
| ExchangeRate-API (`open.er-api.com`) | Tasa USD→COP | Uso gratuito con atribución; si falla, no se muestran pesos. |

Reglas: solo HTTPS, dominios autorizados en `config/stores.json`, reintentos con espera progresiva (2 s, 4 s), sin evadir bloqueos, sin copiar textos protegidos. Cuando una red de afiliados apruebe, preferir sus feeds oficiales.

## Calendario de lanzamientos (Steam)

- `https://store.steampowered.com/api/featuredcategories` (listas `coming_soon` y `new_releases`) y `api/appdetails` para cada juego (máximo 40 por ejecución).
- Solo se guardan juegos (no DLC). La fecha es la que publica Steam: si no trae día exacto se muestra el mes o "Fecha por confirmar"; nunca se inventa.
- Si Steam falla se conserva la última versión válida en `data/lanzamientos.json`.
