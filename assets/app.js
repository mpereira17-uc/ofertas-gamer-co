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

  // Antes había un tema claro: se borra la preferencia vieja para que todos vean el diseño propio.
  try { localStorage.removeItem("ogc-theme"); } catch (e) { /* sin almacenamiento */ }

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
    var min = parseInt(form.min.value || "0", 10), onlyFavs = form.favs && form.favs.checked, onlyLow = form.low && form.low.checked;
    var max = form.max ? parseInt(form.max.value || "0", 10) : 0;
    var cards = Array.prototype.slice.call(list.children);
    var shown = 0;
    cards.forEach(function (li) {
      var d = li.dataset;
      var ok = (!q || d.title.indexOf(q) >= 0) && (!st || d.store === st) &&
        (!type || d.type === type) && (parseInt(d.discount || "0", 10) >= min) &&
        (!max || (d.cop !== undefined && parseInt(d.cop || "0", 10) < max && (d.type === "gratis" || parseInt(d.cop || "0", 10) > 0))) &&
        (!onlyFavs || favs.indexOf(d.id) >= 0) && (!onlyLow || d.low === "1");
      li.hidden = !ok;
      if (ok) shown++;
    });
    cards.sort(function (a, b) {
      if (sort === "expires") return (a.dataset.expires || "9999") < (b.dataset.expires || "9999") ? -1 : 1;
      if (sort === "price") return parseFloat(a.dataset.price) - parseFloat(b.dataset.price);
      if (sort === "title") return a.dataset.title < b.dataset.title ? -1 : 1;
      if (sort === "score") return parseInt(b.dataset.score || "0", 10) - parseInt(a.dataset.score || "0", 10);
      if (sort === "saved") return parseInt(b.dataset.saved || "0", 10) - parseInt(a.dataset.saved || "0", 10);
      return parseInt(b.dataset.discount || "0", 10) - parseInt(a.dataset.discount || "0", 10);
    }).forEach(function (li) { list.appendChild(li); });
    if (countEl) countEl.textContent = shown + (shown === 1 ? " oferta" : " ofertas");
  }
  if (form) {
    form.hidden = false;
    // Filtros desde la dirección (enlaces rápidos de la portada): ?q= ?tipo= ?min= ?max= ?orden= ?tienda=
    var params = new URLSearchParams(location.search);
    var setIf = function (field, value) {
      if (!field || value === null) return;
      var clean = String(value).replace(/[^a-z0-9 \-áéíóúñü]/gi, "");
      if (field.tagName === "SELECT") { if (field.querySelector('option[value="' + clean + '"]')) field.value = clean; }
      else field.value = String(value).slice(0, 80);
    };
    setIf(form.q, params.get("q"));
    setIf(form.store, params.get("tienda"));
    setIf(form.type, params.get("tipo"));
    setIf(form.min, params.get("min"));
    setIf(form.max, params.get("max"));
    var orden = params.get("orden");
    setIf(form.sort, orden === "vence" ? "expires" : orden === "precio" ? "price" : orden);
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

  // Cuenta regresiva en vivo (hora del navegador; el servidor ya la escribió en hora Colombia)
  var MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
  function leftText(iso) {
    var end = new Date(iso), ms = end - new Date();
    if (isNaN(ms)) return null;
    if (ms <= 0) return "Terminó";
    var min = Math.floor(ms / 60000), h = Math.floor(min / 60), d = Math.floor(h / 24);
    if (d > 30) {
      var co = new Date(end.getTime() - 5 * 3600000);
      return "Disponible hasta el " + co.getUTCDate() + " de " + MESES[co.getUTCMonth()];
    }
    if (d >= 1) return "Termina en " + d + (d === 1 ? " día" : " días") + ", " + (h % 24) + " h";
    if (h >= 1) return "Termina en " + h + " h " + (min % 60) + " min";
    return "Termina en " + Math.max(1, min) + " min";
  }
  function tick() {
    document.querySelectorAll("[data-countdown]").forEach(function (el) {
      var iso = el.getAttribute("data-countdown"), txt = leftText(iso), span = el.querySelector("span");
      if (!txt || !span) return;
      span.textContent = txt;
      var ms = new Date(iso) - new Date();
      el.classList.toggle("urgent", ms < 86400000);
      el.classList.toggle("ended", ms <= 0);
    });
  }
  tick();
  setInterval(tick, 60000);

  // Página "Mis favoritos": arma las tarjetas con los datos públicos de las ofertas
  var favRoot = document.getElementById("fav-root");
  if (favRoot && window.fetch) {
    var el = function (tag, cls, text) {
      var n = document.createElement(tag);
      if (cls) n.className = cls;
      if (text) n.textContent = text;
      return n;
    };
    var empty = function () {
      favRoot.textContent = "";
      var box = el("div", "fav-empty");
      box.appendChild(el("p", "", "Todavía no tienes favoritos. Toca la estrella de una oferta para guardarla aquí."));
      var a = el("a", "btn btn-primary", "Ver ofertas");
      a.href = "ofertas.html";
      box.appendChild(a);
      favRoot.appendChild(box);
    };
    var money = function (v, cur) {
      if (cur === "COP") return "$" + Math.round(v).toLocaleString("es-CO") + " COP";
      return "US$" + Number(v).toFixed(2);
    };
    if (!favs.length) empty();
    else fetch(favRoot.getAttribute("data-src")).then(function (r) { return r.json(); }).then(function (data) {
      var mine = (data.offers || []).filter(function (o) { return favs.indexOf(o.id) >= 0; });
      if (!mine.length) return empty();
      favRoot.textContent = "";
      favRoot.appendChild(el("p", "count", mine.length + (mine.length === 1 ? " oferta guardada" : " ofertas guardadas")));
      var ul = el("ul", "grid");
      mine.forEach(function (o) {
        var free = o.currentPrice === 0, li = el("li", "card" + (free ? " is-free" : ""));
        var media = el("a", "media");
        media.href = o.page || o.destinationUrl;
        var img = el("img");
        img.src = /^https:\/\//.test(o.image || "") ? o.image : "assets/placeholder.svg";
        img.alt = "Imagen de " + o.title;
        img.loading = "lazy";
        media.appendChild(img);
        media.appendChild(el("span", "badge" + (free ? " free" : ""), free ? "GRATIS" : "-" + (o.discountPercentage || 0) + "%"));
        li.appendChild(media);
        var body = el("div", "body");
        body.appendChild(el("span", "store-chip", o.store));
        var h = el("h3", "clamp2"), link = el("a", "", o.title);
        link.href = o.page || o.destinationUrl;
        h.appendChild(link);
        body.appendChild(h);
        var box = el("div", "pricebox");
        box.appendChild(el("span", "now" + (free ? " free" : ""), free ? "Gratis" : money(o.currentPrice, o.currency)));
        if (o.originalPrice) box.appendChild(el("s", "", "Antes " + money(o.originalPrice, o.currency)));
        body.appendChild(box);
        if (o.saving) body.appendChild(el("p", "save", o.saving));
        if (o.expiresAt) {
          var left = el("p", "left");
          left.setAttribute("data-countdown", o.expiresAt);
          left.appendChild(el("span", "", leftText(o.expiresAt) || ""));
          body.appendChild(left);
        }
        var acts = el("div", "actions"), go = el("a", "btn btn-primary" + (free && o.action !== "Buscar en la tienda" ? " btn-free" : ""), o.action || "Ver oferta");
        go.href = o.destinationUrl;
        go.target = "_blank";
        go.rel = o.affiliate ? "sponsored nofollow noopener noreferrer" : "noopener noreferrer";
        acts.appendChild(go);
        var rm = el("button", "btn", "Quitar");
        rm.type = "button";
        rm.addEventListener("click", function () {
          var i = favs.indexOf(o.id);
          if (i >= 0) favs.splice(i, 1);
          store("ogc-favs", JSON.stringify(favs));
          li.remove();
          if (!ul.children.length) empty();
        });
        acts.appendChild(rm);
        body.appendChild(acts);
        li.appendChild(body);
        ul.appendChild(li);
      });
      favRoot.appendChild(ul);
      tick();
    }).catch(function () {
      favRoot.textContent = "";
      favRoot.appendChild(el("p", "notice", "No se pudieron cargar tus favoritos. Intenta de nuevo en un momento."));
    });
  }

  // Tráiler: se carga solo cuando la persona toca play (no gasta datos antes)
  document.querySelectorAll(".play-btn").forEach(function (btn) {
    btn.addEventListener("click", function (ev) {
      var box = btn.parentElement, video = btn.getAttribute("data-video"), hls = btn.getAttribute("data-hls");
      var yt = btn.getAttribute("data-yt"), player;
      if (yt && /^[A-Za-z0-9_-]{11}$/.test(yt)) {
        player = document.createElement("iframe");
        player.src = "https://www.youtube-nocookie.com/embed/" + yt + "?autoplay=1&rel=0";
        player.title = btn.getAttribute("aria-label") || "Tráiler";
        player.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen";
        player.setAttribute("allowfullscreen", "");
        player.referrerPolicy = "strict-origin-when-cross-origin";
      } else {
        player = document.createElement("video");
        var native = hls && player.canPlayType("application/vnd.apple.mpegurl");
        var useLib = !video && hls && !native && "MediaSource" in window;
        if (!video && !native && !useLib) return; // sin formato compatible: se abre el enlace normal (Steam)
        if (useLib) {
          // hls.js (copia local, licencia Apache 2.0) para los tráileres de Steam en Chrome, Edge y Firefox
          var startLib = function () {
            var h = new window.Hls({ enableWorker: false });
            h.on(window.Hls.Events.ERROR, function (e, data) {
              if (!data.fatal) return;
              h.destroy();  // si Steam no deja reproducirlo aquí, se ofrece verlo allá
              box.textContent = "";
              var a = document.createElement("a");
              a.className = "btn btn-primary trailer-fallback";
              a.href = btn.getAttribute("href");
              a.target = "_blank";
              a.rel = "noopener noreferrer";
              a.textContent = "Ver el tráiler en Steam";
              box.appendChild(a);
            });
            h.loadSource(hls);
            h.attachMedia(player);
          };
          if (window.Hls) startLib();
          else {
            var tag = document.createElement("script");
            tag.src = "assets/vendor/hls.light.min.js";
            tag.onload = startLib;
            document.head.appendChild(tag);
          }
        } else {
          player.src = video || hls;
        }
        player.controls = true;
        player.autoplay = true;
        player.playsInline = true;
        if (btn.getAttribute("data-poster")) player.poster = btn.getAttribute("data-poster");
      }
      ev.preventDefault();
      player.className = "trailer-player";
      box.textContent = "";
      box.classList.add("playing");
      box.appendChild(player);
      if (player.focus) player.focus();
    });
  });

  // App instalable (PWA): guarda una copia para abrir sin internet y ofrece instalarla
  if ("serviceWorker" in navigator && location.protocol === "https:") {
    navigator.serviceWorker.register("sw.js").catch(function () {});
  }
  var installBox = document.getElementById("install-box"), installBtn = document.getElementById("install-app"), deferred = null;
  window.addEventListener("beforeinstallprompt", function (ev) {
    ev.preventDefault();
    deferred = ev;
    if (installBox) installBox.hidden = false;
  });
  if (installBtn) {
    installBtn.addEventListener("click", function () {
      if (!deferred) return;
      deferred.prompt();
      deferred.userChoice.finally(function () { deferred = null; installBox.hidden = true; });
    });
  }

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
    document.querySelectorAll("main h2, main .card, main .rel-card, .stores li, .faq details, .stats li, .filters, .prose > *").forEach(function (el) {
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
    var colors = ["255,200,61", "255,61,129", "77,124,255"];
    function resize() {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      W = window.innerWidth; H = window.innerHeight;
      canvas.width = W * dpr; canvas.height = H * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      var n = W < 760 ? Math.max(10, Math.round(W * H / 40000)) : Math.max(24, Math.min(90, Math.round(W * H / 16000)));
      dots = [];
      for (var i = 0; i < n; i++) {
        dots.push({ x: Math.random() * W, y: Math.random() * H, vx: (Math.random() - 0.5) * 0.35,
          vy: (Math.random() - 0.5) * 0.35, r: Math.random() * 1.8 + 0.6, c: colors[i % 3] });
      }
    }
    function frame() {
      if (!running) return;
      var alpha = 0.8;
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
