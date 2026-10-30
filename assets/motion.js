// Movimiento con GSAP (guardado en assets/vendor, sin cargar nada de otras páginas).
// Herramientas del video de pepe (2026-10-30): GSAP + SplitText + ScrollTrigger y efectos al estilo Skiper UI.
// Todo se apaga con «menos movimiento» del sistema o con «Ahorro de datos».
(function () {
  var gsap = window.gsap;
  if (!gsap || !window.ScrollTrigger || !window.SplitText) return;
  var root = document.documentElement;
  var calm = (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) ||
    root.classList.contains("pref-lite");
  if (calm) return;
  gsap.registerPlugin(window.ScrollTrigger, window.SplitText);
  var fine = window.matchMedia && window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  root.classList.add("gsap-on");

  // 1. Título principal: las letras suben una por una detrás de una máscara (SplitText)
  var h1 = document.querySelector("main h1");
  if (h1 && !h1.closest(".show")) {
    var playH1 = function () {
      window.SplitText.create(h1, {
        type: "lines,chars", mask: "lines", autoSplit: true,
        onSplit: function (self) {
          return gsap.from(self.chars, { yPercent: 110, rotate: 6, duration: 0.7, ease: "power4.out", stagger: 0.018 });
        }
      });
    };
    // espera a las fuentes para que las líneas se corten donde de verdad terminan
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(playH1); else playH1();
  }

  // 2. Títulos de bloque (los que no son letreros del tablero): las palabras entran al bajar
  document.querySelectorAll("main .sec-head h2").forEach(function (h) {
    if (h.closest(".sign")) return;  // esos ya se arman como el tablero (flipText en app.js)
    window.SplitText.create(h, {
      type: "words", autoSplit: true,
      onSplit: function (self) {
        return gsap.from(self.words, {
          y: 24, opacity: 0, skewX: -12, duration: 0.6, ease: "power3.out", stagger: 0.06,
          scrollTrigger: { trigger: h, start: "top 88%", once: true }
        });
      }
    });
  });

  // 3. Letrero gigante del pie que corre y se acelera según la velocidad del scroll (estilo Skiper «scroll velocity»)
  var giant = document.querySelector(".foot-giant");
  if (giant) {
    var text = giant.textContent.trim();
    giant.textContent = "";
    var track = document.createElement("span");
    track.className = "giant-track";
    for (var i = 0; i < 4; i++) {
      var part = document.createElement("span");
      part.textContent = text + " · ";
      track.appendChild(part);
    }
    giant.appendChild(track);
    var loop = gsap.to(track, { xPercent: -25, duration: 18, ease: "none", repeat: -1, paused: true });
    window.ScrollTrigger.create({
      trigger: giant, start: "top bottom", end: "bottom top",
      onToggle: function (self) { if (self.isActive) loop.play(); else loop.pause(); },
      onUpdate: function (self) {
        loop.timeScale(gsap.utils.clamp(1, 6, Math.abs(self.getVelocity()) / 250));
        gsap.to(loop, { timeScale: 1, duration: 0.8, ease: "power2.out", overwrite: true });  // vuelve a su paso normal
      }
    });
  }

  if (!fine) return;  // lo que sigue solo tiene sentido con mouse

  // 4. Botones magnéticos: el botón principal se deja jalar un poco por el cursor
  document.querySelectorAll("main .btn-primary, main .btn-ig").forEach(function (btn) {
    var toX = gsap.quickTo(btn, "x", { duration: 0.4, ease: "power3.out" });
    var toY = gsap.quickTo(btn, "y", { duration: 0.4, ease: "power3.out" });
    btn.addEventListener("pointermove", function (ev) {
      var r = btn.getBoundingClientRect();
      toX((ev.clientX - r.left - r.width / 2) * 0.3);
      toY((ev.clientY - r.top - r.height / 2) * 0.4);
    });
    btn.addEventListener("pointerleave", function () { toX(0); toY(0); });
  });

  // 5. Menú lateral con texto que rueda al pasar el cursor (estilo Skiper «text roll»)
  document.querySelectorAll("nav.side li > a:not(.btn)").forEach(function (a) {
    var node = a.lastChild;
    if (!node || node.nodeType !== 3 || !node.textContent.trim()) return;
    var label = node.textContent.trim();
    var wrap = document.createElement("span");
    wrap.className = "roll";
    var top = document.createElement("span");
    top.className = "roll-a";
    top.textContent = label;
    var copy = document.createElement("span");
    copy.className = "roll-b";
    copy.textContent = label;
    wrap.appendChild(top);
    wrap.appendChild(copy);
    wrap.setAttribute("aria-hidden", "true");
    a.setAttribute("aria-label", label);
    a.replaceChild(wrap, node);
    var sa = new window.SplitText(top, { type: "chars", aria: "none" });
    var sb = new window.SplitText(copy, { type: "chars", aria: "none" });
    gsap.set(sb.chars, { yPercent: 100 });
    var tl = gsap.timeline({ paused: true, defaults: { duration: 0.35, ease: "power3.inOut", stagger: 0.015 } })
      .to(sa.chars, { yPercent: -100 }, 0)
      .to(sb.chars, { yPercent: 0 }, 0);
    a.addEventListener("pointerenter", function () { tl.play(); });
    a.addEventListener("pointerleave", function () { tl.reverse(); });
  });
})();
