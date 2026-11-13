# Plan de implementación v8 «Estantería»

> Diseño aprobado: `documentacion/2026-11-13-diseno-estanteria.md`. Ejecución inline y publicación directa en `main` (pedido de pepe).

## Tareas

1. **Portadas verticales** — `ogc/capsules.py` con `update(offers, cache, now, fetch) -> (cache, estado)` y `attach(offers, cache)` (pone `o["capsule"]`), mismo patrón que `ogc/trailers.py`. Lotes de 50 a `https://api.steampowered.com/IStoreBrowseService/GetItems/v1/?input_json=...` con `include_assets`; URL = `https://shared.fastly.steamstatic.com/store_item_assets/` + `asset_url_format` con `library_capsule`. Caché `data/portadas.json` (14 días). En `bot.py`, justo después de `trailers.attach`. Fixture `tests/fixtures/steam_getitems.json` y `tests/test_portadas.py` (lote, caché vigente, fallo de Steam no rompe).
2. **Tarjeta caja** — `Site.card`: `.box store-<id> tilt-<1..5>` con la portada vertical o la horizontal con `no-capsule`. Sticker de descuento o «GRATIS», sello «GANGA» (top 10 por `value_score` con ≥75 %) y «Mínimo histórico». Precio en pesos primero («$8.200 aprox.», «US$2.49 en Steam»). Se mantienen los `data-*`, «Sin fecha de fin», las etiquetas y los botones. Mismo cambio en las tarjetas de `app.js` (favoritos y lista de deseos). Prueba en `tests/test_ofertas.py`.
3. **Estantes y vitrina** — `offer_list(slider=True)` con repisa y flechas redondas; `showcase` con caja grande y lomos (`data-go` se mantiene). `browser_check.js` debe pasar.
4. **CSS v8** — tokens en `:root`, bloque final y borrado de las reglas v4, v5 y v7 de tarjetas, estantes y vitrina. «Menos movimiento» y sin JavaScript.
5. **Verificar y publicar** — pruebas de Python y Node, `check_site.py`, `browser_check.js`, revisión visual en 375 y 1280 px, seguridad de 20 puntos, `DESIGN.md`, push a `main`.

## Lo que hay que vigilar

- Ofertas sin `steamAppID` (Epic, algunas de GOG): siempre con el respaldo `no-capsule`.
- Títulos largos dentro de la caja: cortar en 2 líneas.
- 540 portadas en ofertas.html: todas con `loading="lazy"`.
- El sticker no puede tapar el descuento ni el título en 375 px.
- Etiquetas de afiliado o patrocinio siempre visibles.
