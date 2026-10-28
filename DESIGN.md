# Design: Ofertas Gamer CO («Arcade CO», v3)

Documentado desde el sitio construido el 2026-10-28. Los estilos viven en `assets/styles.css` (el bloque «Rediseño v3» al final manda sobre las reglas anteriores) y el HTML lo genera `ogc/site.py`.

## Mundo

Vitrina de tienda gamer de noche. Un solo tema oscuro (pepe no quiere tema claro). Cada sección es un estante con ofertas reales; nada de cifras inventadas.

## Color

| Rol | Valor | Uso |
| --- | --- | --- |
| Fondo | `#0a0716` | Página |
| Superficie | `#150f26` (`--surface-solid`) | Tarjetas, paneles, buscador |
| Menú lateral | `#0d0a1d` | Fondo del menú en computador |
| Borde | `#2a2146` | Solo estructura: divisores y bordes de tarjeta |
| Texto | `#fbf8ff` / secundario `#aba2c8` | |
| Oro | `#ffc83d` (`--gold`) | Precio, botón principal, enlace de sección, elemento activo del menú, selección de texto, cursor |
| Gratis | `#25e09a` (`--free`) | Precio «Gratis», botón de reclamar, ahorro |
| Fucsia | `#ff3d81` | Solo urgencia y tráiler |
| Bandera | `--flag` (oro, azul, rojo) | Único adorno: marca el inicio de cada estante |

Temporada de Halloween (15 oct a 2 nov): la acción pasa a naranja `#ff8a1f` con texto oscuro y la franja a naranja, morado y verde. Mismo sistema, otro tono.

## Tipografía

- Títulos, precios y números grandes: Bricolage Grotesque (alojada en `assets/fonts`), 800, tracking de -0.02em a -0.035em.
- Texto: pila del sistema (Segoe UI Variable, system-ui).
- Títulos con `text-wrap: balance`; párrafos con `pretty`; precios, contadores y cuentas regresivas con `tabular-nums`.
- Sin monoespaciada de adorno.

## Profundidad y forma

- Sin vidrio ni desenfoque decorativo (solo la cabecera fija lo usa, porque el contenido pasa por debajo).
- `--elev-1` para reposo y `--elev-2` al pasar el ratón (sombra con desplazamiento, más un anillo dorado fino). Nada de halos de color con desplazamiento cero.
- Radios concéntricos: tarjeta 16px con 6px de relleno e imagen de 10px. Botones de 12px. Botones de icono de 10px dentro de la tarjeta.
- Imágenes con contorno `oklch(1 0 0 / .1)`.

## Componentes

- **Título de estante** (`sec_head`, `.sec-big`, `.sec-head`): título grande a la izquierda, texto o enlace dorado a la derecha, línea superior de 1px con la franja de la bandera. Sin etiqueta encima, sin icono y sin barra de colores debajo.
- **Tarjeta de oferta** (`card`): imagen encajada con el descuento (oro) o «GRATIS» (verde), la tienda y la cinta solo si es real («Últimas horas», «Mínimo histórico»). Debajo: título, nota de Metacritic si existe, precio grande, pesos aproximados, ahorro, cuenta regresiva y una sola etiqueta de región. Botón principal a todo el ancho y, debajo, los botones de icono (visto, favorito, compartir) en SVG.
- **Estantes de la portada**: `bento` para las mejores ofertas y `poster` para las gratis. En el celular se deslizan de lado con imán (`scroll-snap`).
- **Paneles dobles** (`.duo`): oferta del día junto a «Terminan pronto»; cómo verificamos junto a las herramientas (lista de enlaces, no tarjetas iguales).
- **Botones**: principal en oro con texto oscuro, gratis en verde, canales con su color de marca y contraste AA. Al presionar, `scale(.96)`; sin brillo que recorre el botón.
- **Iconos**: un solo juego de SVG de trazo (`ICONS` en `ogc/site.py`) con `currentColor`. Nada de emojis como iconos.

## Movimiento

- Un solo momento con autor: la escena por capítulos de la portada (`tide_stage`, JS propio, sin GSAP por la CSP `script-src 'self'`).
- Lo demás son transiciones cortas de propiedades concretas (nunca `transition: all`).
- Con `prefers-reduced-motion`, sin JS o con «Ahorro de datos», todo queda estático.

## Reglas que no se rompen

- Solo datos reales del bot: precios, fechas, tiendas y notas. No se inventan cifras, rankings ni testimonios.
- El menú lateral se queda.
- Sin estilos ni scripts en línea (CSP).
