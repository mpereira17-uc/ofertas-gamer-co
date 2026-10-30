---
version: 1
slug: "docs-index-html"
primary_target: "docs/index.html"
related_targets: ["ogc/site.py","assets/styles.css"]
---

# Portada y sitio (index.html y todas las páginas generadas por ogc/site.py)

Modo: Persuade en la portada; Operate en ofertas.html y las listas con filtros.
Visitante: gamer de PC en Colombia, casi siempre desde el celular. Tarea: ver qué está gratis o barato hoy, en pesos, y reclamarlo en la tienda oficial. Prueba: solo datos reales del bot.
Restricciones: el menú lateral se queda; CSP sin estilos ni scripts externos; sin JS debe funcionar; prefers-reduced-motion.

## Direction contract

THESIS: El sitio es el tablero de vuelos de un aeropuerto: cada oferta es una salida con su hora de fin, cada estreno una llegada, cada juego gratis un pase de abordar. Rechaza la vitrina gamer de neón con tarjetas iguales.
OWN-WORLD: Tablero negro #0a0b0d con filas alternas, amarillo de señalización #ffd200 para acción y pictogramas, verde para gratis, naranja para última llamada. Barlow Condensed para títulos, precios y horas; Barlow para texto. Paletas oscuras con línea de corte para la hora de fin. Pase de abordar en papel claro con perforación para lo gratis.
STORY: ve lo destacado (escena por capítulos), lee en una frase cuánto hay hoy, busca, aborda lo gratis, recorre las salidas, ve la oferta del día y la última llamada, compara en pesos, mira las llegadas, confía en el control y sigue un canal.
FIRST VIEWPORT: escena fija por capítulos como pantalla de puerta de embarque, junto al menú lateral; título del juego grande, descuento en una paleta amarilla, precio en pesos, hora de fin y botón amarillo de acción abajo a la izquierda.
FORM: Tablero de salidas (posición 6 de la lista; asignado por el sorteo y elegido por pepe). seed:c8ee7caeb298c021
FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
