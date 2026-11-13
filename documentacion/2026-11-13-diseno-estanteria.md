# Diseño v8 «Estantería» (2026-11-13)

## Por qué

pepe quiere un rediseño de toda la interfaz con más originalidad y personalidad, al nivel de una tienda como Epic Games Store o Instant Gaming, sin copiarlas. Lo que no le convence hoy (v7 «Tienda»): las tarjetas, los colores, los bordes, los sliders y la presentación. Entre tres bocetos eligió **A · Estantería** y dejó los detalles en manos de Claude («se ve bien»).

## La idea

Cada juego es una **caja vertical en una repisa**. Es una tienda de verdad, pero con un objeto propio: Epic e Instant Gaming usan portadas horizontales.

- **Caja:** portada vertical de Steam (600×900), lomo de 7 px a la izquierda con el color de la tienda y esquinas más rectas del lado del lomo (4 px) que del frente (10 px).
- **Sticker de precio:** el descuento va en un sticker torcido (de −6° a 6°, fijo por juego para que no cambie entre visitas) pegado al borde de la caja. Amarillo para descuento, verde para «GRATIS».
- **Personalidad (de la dirección C):** sello rojo «GANGA» solo en las mejores ofertas del día. «Mínimo histórico» como etiqueta negra con letra amarilla.
- **Repisa:** debajo de cada estante, un borde de repisa (6 px, un poco más claro que el fondo). La caja enfocada o con el cursor encima sube 8 px y se enmarca en amarillo.
- **Precio:** pesos primero, con «aprox.» pegado al número (por ejemplo «$8.200 aprox.»); debajo, en pequeño, el precio real de la tienda («US$2.49 en Steam»). En las ofertas que ya vienen en pesos (Epic Colombia) el precio es exacto y no lleva «aprox.».

## Metas

1. Tarjetas de oferta de todo el sitio como cajas en estante (portada, ofertas, gratis, mínimos, favoritos, lista de deseos y demás listas).
2. Portada: la vitrina muestra una caja grande «parada» junto al título, el precio y los botones; debajo, lomos pequeños para cambiar de oferta.
3. Estantes deslizables en la portada (gratis y mejores ofertas) con flechas redondas; en el celular se deslizan con el dedo.
4. Colores y bordes nuevos en todo el sitio, a través de los tokens: las demás páginas (códigos, calendario, guías, fichas) heredan la paleta y los bordes sin rediseñar su estructura.
5. Portadas verticales reales para casi todo el catálogo.

## No metas

- No se rediseña la estructura de las páginas de códigos, calendario, guías, estadísticas ni fichas de juego (solo heredan colores, bordes y tarjetas).
- No hay tema claro. No se quita el menú lateral.
- No se cambian los datos, los textos legales ni el bot de Telegram.

## Anti-metas (sería un fracaso aunque funcione)

- Que se vea como una copia de Epic o de Instant Gaming.
- Cajas vacías o portadas rotas: siempre hay una versión de respaldo con imagen.
- Que se pierda información que hoy está a la vista: tienda, descuento, precio, pesos, vigencia («Sin fecha de fin» incluido), avisos de afiliado.
- Que el celular quede más lento o más largo que hoy.
- Precios en pesos que parezcan exactos cuando son aproximados.

## Restricciones

- CSP estricta: sin estilos ni scripts en línea. Inclinación del sticker y color del lomo por clases (`tilt-1`…`tilt-5`, `store-<id>`), nunca con `style=`.
- Debe funcionar sin JavaScript (los estantes quedan como fila con scroll nativo) y con «menos movimiento» (sin subir cajas ni animar stickers).
- Solo datos reales. Presupuesto $0. Contraste AA.
- Los avisos legales y de afiliado se mantienen visibles en la tarjeta.

## Enfoques considerados

1. **Una capa v8 encima del CSS actual** (solo agregar): rápido, pero suma una quinta capa a v4, v5 y v7, que ya se pisan entre sí.
2. **Reescribir `styles.css` desde cero:** lo más limpio, pero toca más de 125 tipos de página y el riesgo de romper algo es alto.
3. **Capa v8 que reemplaza los componentes que cambian (elegido):** se escribe el bloque v8 para tarjetas, estantes, vitrina, colores y bordes, y **se borran las reglas viejas de esos mismos componentes** (v4, v5 y v7). Lo demás se queda. Es la mezcla que deja el CSS más limpio sin arriesgar las páginas que no cambian. Lo eligió Claude (pepe dejó el cómo en sus manos).

## Cómo se construye

### Datos: portadas verticales

- Módulo nuevo `ogc/capsules.py`, con el mismo patrón que `ogc/trailers.py`: pide a `IStoreBrowseService/GetItems` de Steam (público, sin clave) la portada `library_capsule` de cada `steamAppID`, en lotes de 50, y la guarda en `data/portadas.json` (`{appid: {url, revisado}}`).
- Solo se piden los que faltan o tienen más de 14 días. Si Steam falla, se sigue con lo guardado (nunca rompe la ejecución). Se prueba con un fixture en `tests/fixtures/`, sin internet.
- Hoy: 40 de 40 juegos de una muestra al azar tienen portada vertical y cargan.

### Tarjeta (`Site.card` en `ogc/site.py`)

- La imagen es la portada vertical si existe; si no, la horizontal recortada al centro con el título encima (clase `no-capsule`). `data-fallback` apunta a la horizontal.
- Se mantienen los atributos `data-*` que usan los filtros y el orden de `app.js`.
- Precio: pesos primero según la regla de arriba. Se mantienen el ahorro, la vigencia, «Sin fecha de fin», las etiquetas y los botones.
- «GANGA»: las 10 ofertas con mayor `value_score` del día que además tengan al menos 75 % de descuento (cálculo propio, solo datos reales). Decisión de Claude.
- Color del lomo por tienda: Steam azul, Epic gris claro, GOG morado, Humble rojo anaranjado, Fanatical naranja, Green Man Gaming verde y GamersGate amarillo. Son tonos propios, no los colores exactos de cada marca.
- `app.js` arma tarjetas en favoritos y en la lista de deseos: se actualizan igual.

### Estantes y vitrina

- `offer_list(..., slider=True)` y la vitrina (`showcase`) cambian de marcado y clases. El JavaScript de flechas, pausa y avance automático se reutiliza.
- Las pruebas de `tests/browser_check.js` deben seguir pasando: vitrina `.on`, puntos o lomos que cambian de oferta y nada que avance solo con «menos movimiento».

### CSS

- Bloque «Diseño v8 «Estantería»» al final de `assets/styles.css`, con tokens nuevos en `:root` (fondo, superficie, repisa, sticker, ganga, colores por tienda).
- Se borran las reglas de tarjetas, estantes y vitrina de v4, v5 y v7 que el v8 reemplaza.
- `DESIGN.md` se reescribe con v8 arriba y el historial resumido.

## Cómo se comprueba

- Pruebas de Python (más las nuevas de portadas y tarjeta), `check_site.py`, la prueba de Node de la lista de deseos y `browser_check.js` en local.
- Revisión visual en 375 px y 1280 px de: portada, ofertas, juegos gratis, mínimos, favoritos, lista de deseos, ficha de oferta, códigos y calendario. También sin JavaScript y con «menos movimiento».
- Peso: la portada en el celular no debe quedar más pesada ni más larga que hoy (unos 10.700 px).
- Revisión de seguridad de 20 puntos antes de publicar.

## Lo que queda en manos de quien construye

Espaciados exactos, tamaños de letra dentro de la escala actual (Bricolage Grotesque, Barlow y Barlow Condensed), cuántas cajas por fila en cada ancho (orientativo: 6 en escritorio, 3 en tableta y 2 en celular) y los textos de apoyo, siempre en la voz del sitio.
