# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
Gamers de PC en Colombia, en su mayoría jóvenes y con poco presupuesto, que buscan juegos gratis y descuentos reales antes de comprar. Llegan desde el celular (Telegram, Discord, Bluesky, Google) o desde el computador. Su trabajo: saber en segundos qué está gratis o barato hoy, cuánto cuesta en pesos y hasta cuándo dura.

## Product Purpose
Ofertas Gamer CO junta juegos gratis y ofertas de tiendas oficiales (Steam, Epic, GOG, Humble, Green Man Gaming, Fanatical), los verifica de forma automática cada 4 horas, muestra el valor aproximado en pesos colombianos y avisa por canales. Éxito: que el visitante encuentre una oferta que le sirve, la reclame en la tienda oficial y siga un canal. El dueño (pepe) quiere que crezca solo y, más adelante, gane algo con afiliados aprobados y Ko-fi.

## Positioning
Precios de tiendas oficiales verificados para Colombia, pasados a pesos, con vigencia y avisos automáticos. No es un revendedor de claves y no inventa precios.

## Operating Context
Sitio estático generado por un bot en Python (bot.py + ogc/) que corre en GitHub Actions cada 4 horas y publica docs/ en Cloudflare Pages. CSP estricta: sin estilos en línea ni scripts externos. Las imágenes vienen de las CDN de las tiendas.

## Capabilities and Constraints
- Datos reales de CheapShark, Epic, Steam, GamerPower y Wikidata. Nunca inventar ofertas, precios, descuentos, fechas, estadísticas ni afiliaciones.
- Afiliados solo cuando estén aprobados (Instant Gaming está activo; los demás, no).
- Sin presupuesto: nada que cueste dinero.
- El menú lateral se mantiene (pepe, 2026-10-28).
- Debe funcionar sin JavaScript y con movimiento reducido.

## Brand Commitments
- Nombre: Ofertas Gamer CO. Logo existente en assets/logo-72.png.
- Mundo visual propio oscuro "Arcade CO": oro #ffc83d, fucsia #ff3d81 y azul #4d7cff, con la franja de bandera de Colombia y la letra Bricolage Grotesque. pepe pidió un solo diseño, sin tema claro.
- Voz en español colombiano, cercana y directa.
- Referencias que pepe dio: plantillas gamer de tienda y esports (GameX, MYKD, Galactic), Brivon, Automark, Scrolltide. Pide su estructura y tarjetas, pero con la personalidad propia.
- Temporada de Halloween automática (del 15 de octubre al 2 de noviembre).

## Evidence on Hand
Ofertas reales en data/offers.json, calendario en data/lanzamientos.json, tráileres y capturas de Steam, logo e imágenes de marca de Instant Gaming en assets/brands/. No hay testimonios, cifras de usuarios ni prensa: no inventarlos.

## Product Principles
1. La oferta real va primero: precio, pesos, vigencia y tienda, siempre a la vista.
2. Confianza antes que bombo: solo tiendas oficiales y datos verificados.
3. Rápido en el celular: la mayoría llega desde un enlace en una app.
4. Que crezca solo: todo se actualiza sin trabajo manual.

## Accessibility & Inclusion
Contraste AA, navegación con teclado, foco visible, opciones de letra grande, alto contraste y ahorro de datos, y respeto de prefers-reduced-motion.

<!-- Inferido de la memoria del proyecto y del repo el 2026-10-28; pepe confirma la prioridad de la portada en el hilo. -->
