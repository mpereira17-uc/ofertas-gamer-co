// Mejoras opcionales: la página funciona sin JavaScript. Sin eval, sin scripts externos.
(function () {
  "use strict";
  document.documentElement.classList.add("js");

  function store(key, value) {
    try {
      if (value === undefined) return localStorage.getItem(key);
      localStorage.setItem(key, value);
    } catch (e) { return null; }
  }

  // Tema claro / oscuro
  var saved = store("ogc-theme");
  if (saved === "light" || saved === "dark") document.documentElement.setAttribute("data-theme", saved);
  var themeBtn = document.getElementById("theme-toggle");
  if (themeBtn) {
    themeBtn.addEventListener("click", function () {
      var current = document.documentElement.getAttribute("data-theme") || "dark";
      var next = current === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      store("ogc-theme", next);
    });
  }

  // Menú móvil
  var menuBtn = document.getElementById("menu-toggle");
  var nav = document.getElementById("main-nav");
  if (menuBtn && nav) {
    menuBtn.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      menuBtn.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  // Favoritos guardados en el navegador
  var favs = [];
  try { favs = JSON.parse(store("ogc-favs") || "[]"); } catch (e) { favs = []; }
  document.querySelectorAll("[data-fav]").forEach(function (btn) {
    var id = btn.getAttribute("data-fav");
    btn.hidden = false;
    btn.setAttribute("aria-pressed", favs.indexOf(id) >= 0 ? "true" : "false");
    btn.addEventListener("click", function () {
      var i = favs.indexOf(id);
      if (i >= 0) favs.splice(i, 1); else favs.push(id);
      btn.setAttribute("aria-pressed", i >= 0 ? "false" : "true");
      store("ogc-favs", JSON.stringify(favs));
      applyFilters();
    });
  });

  // Compartir o copiar enlace
  document.querySelectorAll("[data-share]").forEach(function (btn) {
    btn.hidden = false;
    btn.addEventListener("click", function () {
      var url = btn.getAttribute("data-share");
      var title = btn.getAttribute("data-title") || document.title;
      if (navigator.share) {
        navigator.share({ title: title, url: url }).catch(function () {});
      } else if (navigator.clipboard) {
        navigator.clipboard.writeText(url).then(function () { btn.textContent = "Copiado"; });
      }
    });
  });

  // Buscador, filtros y orden
  var list = document.getElementById("offers");
  var form = document.getElementById("filters");
  var countEl = document.getElementById("count");
  function applyFilters() {
    if (!list || !form) return;
    var q = (form.q.value || "").toLowerCase().trim();
    var st = form.store.value, type = form.type.value, sort = form.sort.value;
    var min = parseInt(form.min.value || "0", 10), onlyFavs = form.favs && form.favs.checked;
    var cards = Array.prototype.slice.call(list.children);
    var shown = 0;
    cards.forEach(function (li) {
      var d = li.dataset;
      var ok = (!q || d.title.indexOf(q) >= 0) && (!st || d.store === st) &&
        (!type || d.type === type) && (parseInt(d.discount || "0", 10) >= min) &&
        (!onlyFavs || favs.indexOf(d.id) >= 0);
      li.hidden = !ok;
      if (ok) shown++;
    });
    cards.sort(function (a, b) {
      if (sort === "expires") return (a.dataset.expires || "9999") < (b.dataset.expires || "9999") ? -1 : 1;
      if (sort === "price") return parseFloat(a.dataset.price) - parseFloat(b.dataset.price);
      if (sort === "title") return a.dataset.title < b.dataset.title ? -1 : 1;
      return parseInt(b.dataset.discount || "0", 10) - parseInt(a.dataset.discount || "0", 10);
    }).forEach(function (li) { list.appendChild(li); });
    if (countEl) countEl.textContent = shown + (shown === 1 ? " oferta" : " ofertas");
  }
  if (form) {
    form.hidden = false;
    var wanted = new URLSearchParams(location.search).get("tienda");
    if (wanted && form.store.querySelector('option[value="' + wanted.replace(/[^a-z0-9-]/gi, "") + '"]')) form.store.value = wanted;
    form.addEventListener("input", applyFilters);
    form.addEventListener("submit", function (e) { e.preventDefault(); applyFilters(); });
    applyFilters();
  }

  // Calendario de lanzamientos: pestañas de periodo, chips de sistema y género, seguir juegos
  var relBar = document.getElementById("rel-toolbar");
  if (relBar) {
    relBar.hidden = false;
    var relCount = document.getElementById("rel-count"), relEmpty = document.getElementById("rel-empty");
    var follows = [];
    try { follows = JSON.parse(store("ogc-follow") || "[]"); } catch (e) { follows = []; }
    var view = "hot", qInput = document.getElementById("rel-q");
    var pad = function (n) { return (n < 10 ? "0" : "") + n; };
    var dayStr = function (d) { return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()); };
    var now = new Date(), today = dayStr(now);
    var plus = function (days) { var d = new Date(now); d.setDate(d.getDate() + days); return dayStr(d); };
    var pressed = function (sel) {
      return Array.prototype.map.call(relBar.querySelectorAll(sel + '[aria-pressed="true"]'), function (b) {
        return b.getAttribute(sel === ".chip[data-platform]" ? "data-platform" : "data-genre");
      });
    };
    var inView = function (d) {
      var date = d.date, exact = d.precision === "day";
      if (view === "all") return true;
      if (view === "follow") return follows.indexOf(d.id) >= 0;
      if (!date) return false;
      if (view === "week") return exact && date >= today && date <= plus(7);
      if (view === "month") return date.slice(0, 7) === today.slice(0, 7) && (!exact || date >= today);
      return date >= plus(-7) && date <= plus(30);
    };
    var applyRel = function () {
      var q = (qInput.value || "").toLowerCase().trim(), plats = pressed(".chip[data-platform]"), gens = pressed(".chip[data-genre]");
      var shown = 0;
      document.querySelectorAll("#rel-list .rel-card").forEach(function (li) {
        var d = li.dataset, ps = d.platforms.split("|"), gs = d.genres.split("|");
        var ok = inView(d) && (!q || d.title.indexOf(q) >= 0) &&
          plats.every(function (p) { return ps.indexOf(p) >= 0; }) &&
          (!gens.length || gens.some(function (g) { return gs.indexOf(g) >= 0; }));
        li.hidden = !ok;
        if (ok) shown++;
      });
      document.querySelectorAll("#rel-list .rel-day").forEach(function (day) {
        day.hidden = !day.querySelector(".rel-card:not([hidden])");
      });
      document.querySelectorAll("#rel-list .rel-block").forEach(function (blk) {
        blk.hidden = !blk.querySelector(".rel-day:not([hidden])");
      });
      if (relCount) relCount.textContent = shown + (shown === 1 ? " juego" : " juegos");
      if (relEmpty) relEmpty.hidden = shown > 0;
    };
    relBar.querySelectorAll(".tab").forEach(function (tab) {
      tab.addEventListener("click", function () {
        view = tab.getAttribute("data-view");
        relBar.querySelectorAll(".tab").forEach(function (t) { t.setAttribute("aria-pressed", t === tab ? "true" : "false"); });
        applyRel();
      });
    });
    relBar.querySelectorAll(".chip").forEach(function (chip) {
      chip.addEventListener("click", function () {
        chip.setAttribute("aria-pressed", chip.getAttribute("aria-pressed") === "true" ? "false" : "true");
        applyRel();
      });
    });
    qInput.addEventListener("input", applyRel);
    if (location.hash) {
      view = "all";
      relBar.querySelectorAll(".tab").forEach(function (t) { t.setAttribute("aria-pressed", t.getAttribute("data-view") === "all" ? "true" : "false"); });
    }
    applyRel();
    window.__applyRel = applyRel;
  }
  // Seguir lanzamientos (se guarda solo en este navegador)
  document.querySelectorAll("[data-follow]").forEach(function (btn) {
    var id = btn.getAttribute("data-follow"), list = [];
    try { list = JSON.parse(store("ogc-follow") || "[]"); } catch (e) { list = []; }
    btn.hidden = false;
    btn.setAttribute("aria-pressed", list.indexOf(id) >= 0 ? "true" : "false");
    btn.addEventListener("click", function () {
      try { list = JSON.parse(store("ogc-follow") || "[]"); } catch (e) { list = []; }
      var i = list.indexOf(id);
      if (i >= 0) list.splice(i, 1); else list.push(id);
      store("ogc-follow", JSON.stringify(list));
      document.querySelectorAll('[data-follow="' + id + '"]').forEach(function (b) { b.setAttribute("aria-pressed", i >= 0 ? "false" : "true"); });
      if (relBar && typeof follows !== "undefined") { follows = list; }
    });
  });

  // Copiar el resumen de WhatsApp como texto limpio
  var copyBtn = document.getElementById("copy-wa");
  var waText = document.getElementById("wa-text");
  if (copyBtn && waText) {
    copyBtn.addEventListener("click", function () {
      var text = waText.value;
      function done() { copyBtn.textContent = "¡Copiado!"; setTimeout(function () { copyBtn.textContent = "Copiar texto"; }, 2500); }
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(done, function () { waText.select(); });
      } else {
        waText.select();
      }
    });
  }
  // ---------- Efectos visuales (se apagan si el usuario prefiere menos movimiento) ----------
  var calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var root = document.documentElement;

  // Carrusel de ofertas destacadas: pasa solo, con flechas, puntos y deslizamiento
  var slider = document.querySelector(".slider");
  if (slider) {
    var track = slider.querySelector(".slides");
    var slides = Array.prototype.slice.call(track.children);
    var dotsEls = Array.prototype.slice.call(slider.querySelectorAll(".s-dots a"));
    var bar = slider.querySelector(".s-bar span");
    var prev = slider.querySelector(".prev"), next = slider.querySelector(".next");
    var current = 0, timer = null, paused = false, DELAY = 6000;
    prev.hidden = next.hidden = slides.length < 2;
    function mark(i) {
      current = i;
      slides.forEach(function (s, k) { s.classList.toggle("active", k === i); });
      dotsEls.forEach(function (d, k) { if (k === i) d.setAttribute("aria-current", "true"); else d.removeAttribute("aria-current"); });
      if (bar && !calm) {
        bar.classList.remove("run");
        void bar.offsetWidth;
        if (!paused) bar.classList.add("run");
      }
    }
    function go(i) {
      var n = (i + slides.length) % slides.length;
      track.scrollTo({ left: slides[n].offsetLeft, behavior: calm ? "auto" : "smooth" });
      mark(n);
      restart();
    }
    function restart() {
      clearTimeout(timer);
      if (!calm && !paused && slides.length > 1) timer = setTimeout(function () { go(current + 1); }, DELAY);
    }
    prev.addEventListener("click", function () { go(current - 1); });
    next.addEventListener("click", function () { go(current + 1); });
    dotsEls.forEach(function (d, k) {
      d.addEventListener("click", function (ev) { ev.preventDefault(); go(k); });
    });
    track.addEventListener("keydown", function (ev) {
      if (ev.key === "ArrowRight") { ev.preventDefault(); go(current + 1); }
      if (ev.key === "ArrowLeft") { ev.preventDefault(); go(current - 1); }
    });
    var scrollEnd = null;
    track.addEventListener("scroll", function () {
      clearTimeout(scrollEnd);
      scrollEnd = setTimeout(function () {
        var i = Math.round(track.scrollLeft / track.clientWidth);
        if (i !== current && slides[i]) { mark(i); restart(); }
      }, 120);
    }, { passive: true });
    function pause(on) { paused = on; if (on) { clearTimeout(timer); if (bar) bar.classList.remove("run"); } else mark(current), restart(); }
    slider.addEventListener("mouseenter", function () { pause(true); });
    slider.addEventListener("mouseleave", function () { pause(false); });
    slider.addEventListener("focusin", function () { pause(true); });
    slider.addEventListener("focusout", function () { pause(false); });
    document.addEventListener("visibilitychange", function () { pause(document.hidden); });
    mark(0);
    restart();
  }

  // Barra de progreso y cabecera al bajar
  var progress = document.createElement("div");
  progress.className = "scroll-progress";
  progress.setAttribute("aria-hidden", "true");
  document.body.appendChild(progress);
  var header = document.querySelector("header.site");
  var ticking = false;
  function onScroll() {
    var max = root.scrollHeight - window.innerHeight;
    var y = window.scrollY || window.pageYOffset;
    progress.style.transform = "scaleX(" + (max > 0 ? Math.min(1, y / max) : 0) + ")";
    if (header) header.classList.toggle("scrolled", y > 8);
    if (!calm) root.style.setProperty("--grid-shift", (y * 0.15).toFixed(1) + "px");
    ticking = false;
  }
  window.addEventListener("scroll", function () {
    if (!ticking) { ticking = true; window.requestAnimationFrame(onScroll); }
  }, { passive: true });
  onScroll();

  // Aparición de secciones y tarjetas
  if (!calm && "IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
    document.querySelectorAll("main h2, main .card, main .rel-card, .stores li, .faq details, .stats li, .ticker, .filters, .prose > *").forEach(function (el) {
      var siblings = el.parentElement ? Array.prototype.indexOf.call(el.parentElement.children, el) : 0;
      el.classList.add("reveal");
      el.style.transitionDelay = Math.min(siblings % 6, 5) * 70 + "ms";
      io.observe(el);
    });
  }

  // Contadores animados (con los números reales de la página)
  if (!calm) {
    document.querySelectorAll("[data-count]").forEach(function (el) {
      var end = parseInt(el.getAttribute("data-count"), 10) || 0;
      var suffix = el.getAttribute("data-suffix") || "";
      var start = null;
      function step(ts) {
        if (start === null) start = ts;
        var t = Math.min(1, (ts - start) / 1200);
        el.textContent = Math.round(end * (1 - Math.pow(1 - t, 3))) + suffix;
        if (t < 1) window.requestAnimationFrame(step);
      }
      window.requestAnimationFrame(step);
    });
  }

  // Inclinación 3D de las tarjetas con el puntero
  if (!calm && window.matchMedia("(hover: hover)").matches) {
    document.querySelectorAll(".card").forEach(function (card) {
      card.addEventListener("pointermove", function (ev) {
        var r = card.getBoundingClientRect();
        var x = (ev.clientX - r.left) / r.width - 0.5, y = (ev.clientY - r.top) / r.height - 0.5;
        card.style.setProperty("--rx", (-y * 6).toFixed(2) + "deg");
        card.style.setProperty("--ry", (x * 8).toFixed(2) + "deg");
      });
      card.addEventListener("pointerleave", function () {
        card.style.setProperty("--rx", "0deg");
        card.style.setProperty("--ry", "0deg");
      });
    });
  }

  // Partículas de fondo conectadas
  var canvas = document.createElement("canvas");
  if (!calm && canvas.getContext) {
    canvas.className = "bg-particles";
    canvas.setAttribute("aria-hidden", "true");
    document.body.insertBefore(canvas, document.body.firstChild);
    var ctx = canvas.getContext("2d");
    var dots = [], W = 0, H = 0, dpr = 1, mouse = { x: -9999, y: -9999 }, running = true;
    var colors = ["139,92,246", "6,182,212", "34,197,94"];
    function resize() {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      W = window.innerWidth; H = window.innerHeight;
      canvas.width = W * dpr; canvas.height = H * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      var n = Math.max(24, Math.min(90, Math.round(W * H / 16000)));
      dots = [];
      for (var i = 0; i < n; i++) {
        dots.push({ x: Math.random() * W, y: Math.random() * H, vx: (Math.random() - 0.5) * 0.35,
          vy: (Math.random() - 0.5) * 0.35, r: Math.random() * 1.8 + 0.6, c: colors[i % 3] });
      }
    }
    function frame() {
      if (!running) return;
      var light = root.getAttribute("data-theme") === "light";
      var alpha = light ? 0.5 : 0.8;
      ctx.clearRect(0, 0, W, H);
      for (var i = 0; i < dots.length; i++) {
        var d = dots[i];
        var mx = d.x - mouse.x, my = d.y - mouse.y, md = mx * mx + my * my;
        if (md < 14400) { d.x += mx / 60; d.y += my / 60; }
        d.x += d.vx; d.y += d.vy;
        if (d.x < 0 || d.x > W) d.vx *= -1;
        if (d.y < 0 || d.y > H) d.vy *= -1;
        ctx.beginPath();
        ctx.arc(d.x, d.y, d.r, 0, 6.283);
        ctx.fillStyle = "rgba(" + d.c + "," + alpha + ")";
        ctx.fill();
        for (var j = i + 1; j < dots.length; j++) {
          var o = dots[j], dx = d.x - o.x, dy = d.y - o.y, dist = dx * dx + dy * dy;
          if (dist < 15000) {
            ctx.strokeStyle = "rgba(" + d.c + "," + (alpha * 0.35 * (1 - dist / 15000)).toFixed(3) + ")";
            ctx.lineWidth = 1;
            ctx.beginPath(); ctx.moveTo(d.x, d.y); ctx.lineTo(o.x, o.y); ctx.stroke();
          }
        }
      }
      window.requestAnimationFrame(frame);
    }
    window.addEventListener("resize", resize);
    window.addEventListener("pointermove", function (ev) { mouse.x = ev.clientX; mouse.y = ev.clientY; }, { passive: true });
    document.addEventListener("visibilitychange", function () {
      running = !document.hidden;
      if (running) window.requestAnimationFrame(frame);
    });
    resize();
    window.requestAnimationFrame(frame);
  }
})();

// Si la portada grande de una oferta no existe, se usa la miniatura original de la tienda.
document.addEventListener("error", function (ev) {
  var img = ev.target;
  if (img && img.tagName === "IMG" && img.dataset.fallback && img.src !== img.dataset.fallback) {
    img.src = img.dataset.fallback;
    img.removeAttribute("data-fallback");
  }
}, true);
