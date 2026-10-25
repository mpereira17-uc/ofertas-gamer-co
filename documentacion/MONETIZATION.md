# Plan de financiación de Ofertas Gamer CO

Ninguna cifra de este documento es una ganancia garantizada. GitHub Pages no se usa para cobros, registros ni datos sensibles: cualquier pago futuro irá por un proveedor especializado.

## Fase 1: afiliados (en curso)

| Programa | Red | Estado (25/10/2026) | Dónde se configura |
| --- | --- | --- | --- |
| Green Man Gaming | Impact | Solicitud en revisión | `config/stores.json` → `gmg`, o variable `GMG_AFFILIATE_URL` |
| Fanatical | Awin | Registro en curso | `config/stores.json` → `fanatical`, o variable `FANATICAL_AFFILIATE_URL` |
| Otras tiendas oficiales | Según la tienda | Pendiente | Nuevo registro en `config/stores.json` |

Cuando una red apruebe:
1. Copia el enlace de seguimiento que te da el panel (Impact: *Create Tracking Link*; Awin: *Link Builder*). Debe llevar el enlace de la tienda en un parámetro; en la plantilla ese lugar se marca con `{url}`.
2. Guárdalo en **Settings → Secrets and variables → Actions → Variables** como `GMG_AFFILIATE_URL` o `FANATICAL_AFFILIATE_URL`, o en `affiliateUrl` de `config/stores.json`.
3. Cambia `"approved": false` a `true` en esa tienda. La única función que arma enlaces es `ogc/affiliates.py::build_destination`.
4. Los subidentificadores por canal (website, telegram, whatsapp…) se agregarán solo si la red los admite; no se inventan parámetros.
5. Mide clics, conversiones y comisiones en los paneles oficiales de Impact y Awin.

## Fase 2: publicidad

- Espacios definidos y desactivados en `config/ads.json` (`ads_enabled: false`). Un espacio desactivado no genera HTML.
- AdSense solo cuando: haya contenido original suficiente, páginas legales completas, dominio propio con HTTPS, aprobación de Google, plataforma de consentimiento certificada si se muestran anuncios personalizados en el EEE, Reino Unido o Suiza, e identificador oficial entregado por el dueño.
- Al aprobarse: pegar el código oficial sin modificarlo, crear `ads.txt` con la línea exacta de Google, actualizar privacidad y cookies antes de publicar.
- Prohibido: hacer clic en anuncios propios, comprar visitas, incentivar clics, ocultar anuncios, titulares engañosos o anuncios junto a botones de compra.

## Fase 3: patrocinadores

Tiendas de videojuegos, marcas de periféricos y servicios legales relacionados. Toda campaña con fecha de inicio, fecha de fin y etiqueta "Patrocinado" (ver `publicidad.html` y `anunciate.html`). No se publican cifras de audiencia inventadas.

## Fase 4: productos propios

Guías digitales, alertas premium, boletín especializado, informes de precios y herramientas de comparación. Requieren proveedor de pagos, consentimiento y política de privacidad actualizada.

## Publicidad pagada externa

`paid_ads_enabled: false` en `config/ads.json`. GitHub Actions nunca lanza campañas ni aumenta presupuestos. Cualquier integración futura (Google Ads, Meta Ads) empieza con presupuesto 0, límite máximo, países y fechas autorizadas, creativos aprobados, registro de cada lanzamiento, aprobación humana expresa y un interruptor de emergencia.

## Control financiero

Plantilla vacía en `finanzas/plantilla-finanzas.csv` y métricas en `finanzas/LEEME.md`. Los datos reales nunca se suben.
