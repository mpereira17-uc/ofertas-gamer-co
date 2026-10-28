---
version: 1
slug: "docs-index-html"
primary_target: "docs/index.html"
related_targets: ["ogc/site.py","assets/styles.css"]
---

# Portada y sitio (index.html y todas las páginas generadas por ogc/site.py)

Modo: Persuade en la portada; Operate en ofertas.html y las listas con filtros.
Visitante: gamer de PC en Colombia, casi siempre desde el celular. Tarea: ver qué está gratis o barato hoy, en pesos, y reclamarlo en la tienda oficial. Prueba: solo datos reales del bot (precios, fechas, tiendas).
Restricciones: el menú lateral se queda; CSP sin estilos ni scripts externos; sin JS debe funcionar; prefers-reduced-motion.

## Direction contract

THESIS: La portada es la vitrina de una tienda gamer donde cada estante es una oferta real. Rechaza el montaje de landing SaaS: etiquetas sobre los títulos, cifras gigantes, tarjetas iguales de icono y texto, barras de colores bajo cada título.
OWN-WORLD: «Arcade CO»: fondo noche violeta #0a0716, superficies sólidas #150f26 con sombra para la profundidad, oro #ffc83d como color del precio y de la acción, verde #25e09a para lo gratis, fucsia solo para urgencia. La franja de la bandera de Colombia es el único adorno y marca el inicio de cada estante. Bricolage Grotesque para títulos y precios; números tabulares. Tarjetas con la imagen encajada (radio 16 por fuera, 10 por dentro).
STORY: ve lo gratis y lo destacado (escena por capítulos), entiende en una frase cuánto hay hoy, busca, recorre estantes (gratis, mejores ofertas, oferta del día y lo que termina, ahorro y duelos, estrenos), confía (cómo verificamos) y sigue un canal.
FIRST VIEWPORT: la escena fija por capítulos (tide_stage) a todo el ancho del contenido, junto al menú lateral; título del juego grande, precio en pesos, cuenta regresiva y botón de reclamar abajo a la izquierda.
FORM: Estantes de tienda (posición 1 de mi lista; carta repartida #4). seed:97d1e04b453b10df
FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
