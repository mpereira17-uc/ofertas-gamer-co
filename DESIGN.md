# Design: Ofertas Gamer CO («Tablero» v4 + estilo «Jordan» v5)

**v5 «Jordan» (2026-10-30), a partir del diseño de Figma «Jordan Shoes Website Concept» que mandó pepe:**
- El bloque «Diseño v5 «Jordan»» va al final de `assets/styles.css` y manda sobre v4.
- **Colores:** negro `#070708`, rojo `#ff2a3d` (`--sign`) y blanco. Enlaces en `#ff6b78`.
- **Títulos:** grandes en cursiva, con la primera letra en rojo.
- **Botones:** blanco sólido para la acción principal y borde blanco para lo demás, con esquinas casi rectas.
- **Fondo y paneles:** líneas rojas finas detrás. Paneles negros con esquinas de 14px y sombra suave. Portadas un poco inclinadas.
- **Portada** (`showcase`): reemplaza la escena por capítulos y tiene:
  - tarjeta negra con el título partido en rojo y blanco y la palabra gigante de fondo;
  - portada inclinada encima y precio grande;
  - puntos verticales y miniaturas «Elige otra»;
  - avance automático cada 6 s, con botón de pausa.
- **Juegos gratis:** tarjetas negras con la portada inclinada. Ya no son pases de abordar claros.
- Los nombres de sección (Salidas, Abordando…) siguen igual.


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
- **Tablero de salidas** (`departures_ticker`): va arriba de cada página. Pasa una oferta real cada 5 s y el título se arma letra por letra. Tiene botón de pausa y se detiene al pasar el cursor o al enfocar.
- **Estantes que se deslizan** (`offer_list(slider=True)`, `ul[data-slider]`): tienen flechas, pausa y avance solo cada 5 s, y solo se mueven si están en pantalla. Sin JS quedan en cuadrícula.
- **Letreros:** al aparecer, el cuadro amarillo se enciende y el título se arma como en un tablero.
- **Paletas:** cada 7 s la paleta «Termina» de una fila visible vuelve a girar. Es solo el giro; el dato no cambia.
- **Transiciones entre páginas:** CSS `@view-transition`. El contenido nuevo cae como una paleta.
- No hay inclinación 3D ni partículas.
- Con `prefers-reduced-motion`, sin JS o con «Ahorro de datos», todo queda estático.

## Modo terror (15 de octubre al 2 de noviembre, se activa y se quita solo)

- El amarillo pasa a naranja calabaza `#ff7a1a`, con rojo sangre `#b3122b`.
- **Decorado:**
  - niebla que se arrastra por el piso;
  - sangre que chorrea bajo la cabecera;
  - telarañas en los letreros, que parpadean de vez en cuando;
  - murciélagos y una araña (oculta en el celular).
- **Sustos:** cada 16 a 30 s hay un susto suave. Puede ser un par de ojos que se abren en una esquina o un apagón de 1,2 s, con dos bajadas de luz y nunca destellos claros.
- **Especial de terror:** «Puerta 13 · vuelo nocturno», con la cuenta regresiva hasta el fin del especial.
- **Transición entre páginas:** sale de la niebla (desenfoque).
- Todo se apaga con «menos movimiento» y con «Ahorro de datos».

## Reglas que no se rompen

- Solo datos reales del bot. Si una tienda no publica la fecha de fin, se muestra «Sin fecha de fin».
- El menú lateral se queda.
- Sin estilos ni scripts en línea (CSP).
