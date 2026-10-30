# Design: Ofertas Gamer CO («Tablero», v4)

Mundo elegido por pepe el 2026-10-30. El sitio se lee como el tablero de vuelos de un aeropuerto. Los estilos están en `assets/styles.css`: el bloque «Diseño v4 «Tablero»» del final manda sobre las reglas anteriores. El HTML lo genera `ogc/site.py`.

## Idea

- **Salidas:** ofertas que terminan.
- **Abordando:** juegos gratis de ahora.
- **Última llamada:** lo que termina pronto.
- **Llegadas y Aterrizan hoy:** estrenos.

La metáfora se queda en los títulos de los estantes principales. El resto del texto habla claro.

## Color

| Rol | Valor | Uso |
| --- | --- | --- |
| Fondo | `#0a0b0d` | Página |
| Tablero | `#101215` (`--board`) | Paneles, tablero, buscador |
| Filas | `#14171b` y `#111317` | Filas alternas del tablero |
| Bordes | `#23272d` y `#323840` | Divisores de filas y bordes de paneles |
| Texto | `#f3f0e7`; secundario `#a3a9b1` | |
| Amarillo de señalización | `#ffd200` (`--sign`) | Acción principal, pictogramas, menú activo, fechas, selección |
| Verde | `#3ddc84` | Gratis, reclamar y ahorro |
| Naranja | `#ff9d2e` | Termina pronto |
| Rojo | `#ff5a5f` | Tráiler en vivo |
| Azul | `#5aa9ff` | Foco del teclado |

## Tipografía

- Barlow Condensed (600 y 700) para títulos, precios, horas y botones. Barlow (400 y 600) para el texto. Las dos están alojadas en `assets/fonts` con licencia OFL.
- Las mayúsculas espaciadas solo van en etiquetas de columna, títulos de grupo del menú y botones.
- Números tabulares en precios, horas y contadores.

## Forma y profundidad

- Esquinas de señalización: 6px en paneles y botones, 4px en el interior, 3px en etiquetas.
- El tablero es plano: sin brillos, vidrio, partículas ni degradados de fondo.
- La profundidad sale del contraste entre fondo, tablero y filas.
- La paleta (`--flap`) es un mosaico oscuro con la línea de corte en el centro. Se usa para la hora de fin y para el descuento grande de la portada.

## Componentes

- **Letrero de sección** (`sec_head(..., icon)`): pictograma negro sobre un cuadro amarillo y el título al lado. A la derecha va el texto o el enlace. Sin etiquetas encima del título.
- **Fila del tablero:** toda lista `ul.grid` que no sea `poster`.
  - En computador tiene columnas: carátula, juego (tienda y nota MC), precio (USD, pesos y ahorro), «Termina» (paleta o «Sin fecha de fin») y acciones. Arriba va la cabecera `.board-cols`.
  - En el celular la carátula va a la izquierda, los datos a la derecha y los botones abajo.
- **Pase de abordar** (`poster`, para los gratis): papel claro `#ecebe5` con la carátula como talón, línea perforada y sello «GRATIS» verde.
- **Escena de la portada** (`tide_stage`): pantalla de puerta de embarque, con el descuento en una paleta grande.
- **Pictogramas** (`ICONS`): depart, arrive, ticket, shield, info, speaker, screen y swap, más los anteriores. Todos son SVG de trazo con `currentColor`.

## Movimiento

- La escena por capítulos de la portada se mantiene.
- Las filas del tablero caen una vez como paletas al entrar en pantalla: `rotateX` desde -70°, escalonadas cada 55 ms.
- No hay inclinación 3D ni partículas.
- Con `prefers-reduced-motion`, sin JS o con «Ahorro de datos», todo queda estático.

## Reglas que no se rompen

- Solo datos reales del bot. Si una tienda no publica la fecha de fin, se muestra «Sin fecha de fin».
- El menú lateral se queda.
- Sin estilos ni scripts en línea (CSP).
