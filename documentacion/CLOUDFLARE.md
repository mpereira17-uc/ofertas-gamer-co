# Migración a Cloudflare Pages (preparada, no activada)

El sitio ya se genera en `docs/` y trae `docs/_headers` con los encabezados de seguridad que Cloudflare aplica. No borres GitHub Pages hasta comprobar que la nueva dirección funciona.

1. Crea una cuenta gratis en https://dash.cloudflare.com/sign-up y activa la verificación en dos pasos.
2. En el panel: **Workers & Pages → Create → Pages → Connect to Git**.
3. Autoriza GitHub y elige solo el repositorio `mpereira17-uc/ofertas-gamer-co`.
4. **Production branch**: `main`.
5. **Framework preset**: None. **Build command**: vacío (GitHub Actions ya genera el sitio). **Build output directory**: `docs`.
6. Guarda. Cada commit en `main` (incluidos los automáticos cada 4 horas) desplegará solo.
7. En **Settings → Builds & deployments** deja activadas las vistas previas de ramas (*Preview deployments: All non-production branches*).
8. HTTPS viene activado en la dirección `*.pages.dev`.
9. **Analytics → Web Analytics**: actívalo para el proyecto. Es analítica sin cookies; antes de activarlo actualiza `privacidad.html` (ver `ogc/site.py`).
10. Dominio propio (fase posterior, con tu autorización): **Custom domains → Set up a domain**, configura DNS, redirige `www`, cambia `url_web` en `config/site.json` (canónicas y sitemap se regeneran) y agrega la nueva propiedad en Search Console.

Cuando la nueva dirección funcione, cambia `url_web` en `config/site.json` a la dirección de Cloudflare para que la URL canónica apunte allí.

## Función de la lista de deseos (activa desde el 13/11/2026)

`functions/api/lista-de-deseos.js` es una Pages Function: Cloudflare la publica sola en `/api/lista-de-deseos` porque la carpeta `functions/` está en la raíz del repositorio. Solo consulta dos direcciones fijas de Steam (el XML público del perfil y `IWishlistService/GetWishlist`), valida la entrada, no guarda nada y deja cada respuesta 1 hora en la caché de Cloudflare. El plan gratis permite 100.000 llamadas al día. Pruebas sin internet: `node --test tests/lista_deseos.test.mjs`. En GitHub Pages la función no existe y la página muestra un aviso de error.

## Web Analytics (activa desde el 13/11/2026)

La CSP (`config/_headers` y `CSP` en `ogc/site.py`) permite `static.cloudflareinsights.com` y `cloudflareinsights.com` para el contador sin cookies. La política de privacidad ya lo explica.
