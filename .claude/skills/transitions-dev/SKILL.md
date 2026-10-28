---
name: transitions-dev
description: Use when adding or polishing UI transitions (dropdowns, modals, toasts, tabs, tooltips, accordions, like buttons, skeleton loaders, hover lifts, number pop-ins) on any Ofertas Gamer CO page. Loads the Transitions.dev CSS library on demand.
---

# Transitions.dev (cargada bajo demanda)

Transitions.dev (https://github.com/jakubantalik/transitions.dev) son 35 transiciones CSS listas, sin dependencias y con `prefers-reduced-motion`. Su licencia deja usarlas gratis en la web, pero no permite redistribuir la librería, y este repo es público. Por eso no está copiada aquí: se descarga en la sesión, fuera del repo.

1. Clonar en el scratchpad (nunca dentro del repo):
   `git clone --depth 1 https://github.com/jakubantalik/transitions.dev <scratchpad>/transitions.dev`
2. Leer `<scratchpad>/transitions.dev/skills/transitions-dev/SKILL.md` y seguirlo. Para pulir lo que ya existe, leer también `skills/transitions-polish/SKILL.md`.
3. Copiar a `docs/` solo los snippets que la página usa, conservando el comentario de transitions.dev de cada snippet.
4. Respetar el estilo actual del sitio (CSS plano, diseño oscuro 'Arcade CO') y no añadir frameworks.
