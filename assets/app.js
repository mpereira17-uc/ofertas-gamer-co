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

  // Opciones de lectura: letra grande, alto contraste y ahorro de datos (se guardan en este navegador)
  var PREFS = ["big", "contrast", "lite"];
  var prefs = {};
  try { prefs = JSON.parse(store("ogc-prefs") || "{}") || {}; } catch (e) { prefs = {}; }
  PREFS.forEach(function (k) { document.documentElement.classList.toggle("pref-" + k, !!prefs[k]); });
  document.querySelectorAll("[data-pref]").forEach(function (btn) {
    var k = btn.getAttribute("data-pref");
    btn.hidden = false;
    btn.setAttribute("aria-pressed", prefs[k] ? "true" : "false");
    btn.addEventListener("click", function () {
      prefs[k] = !prefs[k];
      document.documentElement.classList.toggle("pref-" + k, prefs[k]);
      btn.setAttribute("aria-pressed", prefs[k] ? "true" : "false");
      store("ogc-prefs", JSON.stringify(prefs));
      if (k === "lite" && prefs[k]) { var c = document.querySelector(".bg-particles"); if (c) c.remove(); }
    });
  });

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
    // Atajos (Solo gratis, Vale la pena…): filtran sin recargar, se marcan y se quitan con otro clic
    var chips = Array.prototype.slice.call(document.querySelectorAll(".quick-chips a.chip"));
    var chipField = { tipo: "type", min: "min", max: "max", orden: "sort", tienda: "store", q: "q" };
    var chipParams = function (a) { return new URLSearchParams((a.getAttribute("href") || "").split("?")[1] || ""); };
    var fieldValue = function (key, value) { return key === "orden" ? (value === "vence" ? "expires" : value === "precio" ? "price" : value) : value; };
    var chipMatches = function (a) {
      var ok = true;
      chipParams(a).forEach(function (v, k) { var f = form[chipField[k]]; if (!f || f.value !== fieldValue(k, v)) ok = false; });
      return ok;
    };
    var markChips = function () {
      chips.forEach(function (a) { var on = chipMatches(a); a.setAttribute("aria-pressed", on ? "true" : "false"); a.classList.toggle("on", on); });
    };
    var syncUrl = function () {
      try {
        var p = new URLSearchParams();
        Object.keys(chipField).forEach(function (k) {
          var f = form[chipField[k]]; if (!f || !f.value) return;
          if (k === "orden" && f.value === "discount") return;
          p.set(k, k === "orden" ? (f.value === "expires" ? "vence" : f.value === "price" ? "precio" : f.value) : f.value);
        });
        var qs = p.toString();
        history.replaceState(null, "", location.pathname + (qs ? "?" + qs : "") + location.hash);
      } catch (err) { /* sin historial: no pasa nada */ }
    };
    chips.forEach(function (a) {
      a.setAttribute("role", "button");
      a.addEventListener("click", function (ev) {
        ev.preventDefault();
        var wasOn = chipMatches(a);
        chips.forEach(function (c) {  // un atajo a la vez: limpia lo que ponen los demás
          chipParams(c).forEach(function (v, k) {
            var f = form[chipField[k]]; if (!f) return;
            f.value = k === "orden" ? (f.querySelector('option[value="discount"]') ? "discount" : f.options[0].value) : "";
          });
        });
        if (!wasOn) chipParams(a).forEach(function (v, k) { setIf(form[chipField[k]], fieldValue(k, v)); });
        applyFilters(); markChips(); syncUrl();
      });
    });
    form.addEventListener("input", function () { applyFilters(); markChips(); syncUrl(); });
    form.addEventListener("submit", function (e) { e.preventDefault(); applyFilters(); });
    if (list && !Array.prototype.some.call(list.children, function (li) { return li.dataset.type !== "gratis"; }))
      chips.forEach(function (a) { if (/tipo=gratis/.test(a.getAttribute("href"))) a.hidden = true; });  // en una lista solo de gratis sobra
    applyFilters(); markChips();
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
    // carga infinita: se muestran los juegos por tandas y llegan más al bajar
    var STEP = 48, limit = STEP, total = 0;
    var more = document.getElementById("rel-more"), moreBtn = document.getElementById("rel-more-btn"), moreTxt = document.getElementById("rel-more-txt");
    var applyRel = function (keep) {
      if (keep !== true) limit = STEP;
      var q = (qInput.value || "").toLowerCase().trim(), plats = pressed(".chip[data-platform]"), gens = pressed(".chip[data-genre]");
      var shown = 0;
      total = 0;
      document.querySelectorAll("#rel-list .rel-card").forEach(function (li) {
        var d = li.dataset, ps = d.platforms.split("|"), gs = d.genres.split("|");
        var ok = inView(d) && (!q || d.title.indexOf(q) >= 0) &&
          plats.every(function (p) { return ps.indexOf(p) >= 0; }) &&
          (!gens.length || gens.some(function (g) { return gs.indexOf(g) >= 0; }));
        if (ok) total++;
        if (ok && total > limit) ok = false;
        li.hidden = !ok;
        if (ok) shown++;
      });
      document.querySelectorAll("#rel-list .rel-day").forEach(function (day) {
        day.hidden = !day.querySelector(".rel-card:not([hidden])");
      });
      document.querySelectorAll("#rel-list .rel-block").forEach(function (blk) {
        blk.hidden = !blk.querySelector(".rel-day:not([hidden])");
      });
      if (relCount) relCount.textContent = total + (total === 1 ? " juego" : " juegos");
      if (relEmpty) relEmpty.hidden = shown > 0;
      if (more) {
        var left = total - shown;
        more.hidden = !(left > 0 || (view !== "all" && view !== "follow" && shown > 0));
        if (left > 0) {
          moreTxt.textContent = "Viendo " + shown + " de " + total + " juegos";
          moreBtn.textContent = "Cargar más juegos";
        } else {
          moreTxt.textContent = "Hay más lanzamientos en las próximas semanas y meses";
          moreBtn.textContent = "Ver todos los lanzamientos";
        }
      }
    };
    var loadMore = function () {
      if (total > limit) { limit += STEP; applyRel(true); return; }
      if (view === "all" || view === "follow") return;
      view = "all";
      relBar.querySelectorAll(".tab").forEach(function (t) { t.setAttribute("aria-pressed", t.getAttribute("data-view") === "all" ? "true" : "false"); });
      applyRel(true);
    };
    if (moreBtn) moreBtn.addEventListener("click", loadMore);
    if (more && "IntersectionObserver" in window) {
      new IntersectionObserver(function (entries) {
        // al llegar al final se carga la siguiente tanda sola (el cambio a «Todo» queda en el botón)
        if (entries[0].isIntersecting && total > limit) { limit += STEP; applyRel(true); }
      }, { rootMargin: "600px 0px" }).observe(more);
    }
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

  // Cuenta regresiva grande en la página de cada juego que todavía no sale
  var launches = document.querySelectorAll("[data-launch]");
  if (launches.length) {
    var launchTick = function () {
      launches.forEach(function (el) {
        var ms = new Date(el.getAttribute("data-launch")) - new Date();
        if (isNaN(ms)) return;
        el.hidden = false;
        if (ms <= 0) { el.querySelector(".launch-label").textContent = el.getAttribute("data-done") || "¡Ya salió!"; ms = 0; }
        var sec = Math.floor(ms / 1000), parts = { d: Math.floor(sec / 86400), h: Math.floor(sec / 3600) % 24, m: Math.floor(sec / 60) % 60, s: sec % 60 };
        el.querySelectorAll("[data-u]").forEach(function (n) { n.textContent = parts[n.getAttribute("data-u")]; });
      });
    };
    launchTick();
    setInterval(launchTick, 1000);
  }

  // Gratis para siempre: filtro por género
  var f2pBar = document.getElementById("f2p-genres"), f2pList = document.getElementById("f2p-list");
  if (f2pBar && f2pList) {
    f2pBar.hidden = false;
    f2pBar.addEventListener("click", function (ev) {
      var btn = ev.target.closest("button[data-g]");
      if (!btn) return;
      var g = btn.getAttribute("data-g");
      f2pBar.querySelectorAll("button").forEach(function (b) { b.setAttribute("aria-pressed", b === btn ? "true" : "false"); });
      Array.prototype.forEach.call(f2pList.children, function (li) {
        li.hidden = !!g && (li.getAttribute("data-genres") || "").split("|").indexOf(g) < 0;
      });
    });
  }

  // Buscador de todo el sitio (ofertas + lanzamientos) y página "Mis seguidos"
  var norm = function (t) { return String(t || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, ""); };
  // "gta" encuentra "Grand Theft Auto VI": también se busca por las iniciales de las palabras
  var initials = function (t) { return norm(t).split(/[^a-z0-9]+/).filter(Boolean).map(function (w) { return w[0]; }).join(""); };
  var row = function (item) {
    var li = document.createElement("li"), a = document.createElement("a");
    a.className = "srow"; a.href = item.page || item.url || "#";
    var img = document.createElement("img");
    img.src = /^https:\/\//.test(item.image || "") ? item.image : "assets/placeholder.svg";
    img.alt = ""; img.loading = "lazy"; img.width = 120; img.height = 56;
    var box = document.createElement("span"), t = document.createElement("strong"), m = document.createElement("span");
    t.textContent = item.title; m.className = "meta"; m.textContent = item.meta || "";
    box.appendChild(t); box.appendChild(m); a.appendChild(img); a.appendChild(box); li.appendChild(a);
    return li;
  };
  var siteData = null;
  var loadSite = function () {
    if (siteData) return Promise.resolve(siteData);
    return Promise.all([fetch("data/offers.json").then(function (r) { return r.json(); }),
      fetch("data/juegos.json").then(function (r) { return r.json(); })]).then(function (d) {
      var offers = (d[0].offers || []).map(function (o) {
        return { title: o.title, page: o.page, image: o.image, k: norm(o.title) + " " + initials(o.title),
          meta: (o.currentPrice === 0 ? "Gratis" : "-" + (o.discountPercentage || 0) + "%") + " · " + o.store };
      });
      var games = (d[1].games || []).map(function (g) {
        return { id: g.id, title: g.title, page: g.page, image: g.image, k: norm(g.title) + " " + initials(g.title), meta: "Lanzamiento · " + (g.when || "") };
      });
      siteData = { offers: offers, games: games };
      return siteData;
    });
  };
  var sRoot = document.getElementById("search-root");
  if (sRoot && window.fetch) {
    sRoot.hidden = false;
    var sInput = document.getElementById("site-q"), sOut = document.getElementById("search-out");
    var run = function () {
      var q = norm(sInput.value).trim();
      loadSite().then(function (d) {
        sOut.textContent = "";
        if (q.length < 2) return;
        [["Ofertas", d.offers], ["Lanzamientos", d.games]].forEach(function (pair) {
          var hits = pair[1].filter(function (x) { return x.k.indexOf(q) >= 0; }).slice(0, 30);
          var h = document.createElement("h2"); h.textContent = pair[0] + " (" + hits.length + ")";
          sOut.appendChild(h);
          var ul = document.createElement("ul"); ul.className = "srows";
          hits.forEach(function (x) { ul.appendChild(row(x)); });
          sOut.appendChild(ul);
        });
      });
    };
    var q0 = new URLSearchParams(location.search).get("q");
    if (q0) sInput.value = q0.slice(0, 80);
    sInput.addEventListener("input", run);
    run();
  }
  var fRoot = document.getElementById("follow-root");
  if (fRoot && window.fetch) {
    var ids = [];
    try { ids = JSON.parse(store("ogc-follow") || "[]"); } catch (e) { ids = []; }
    loadSite().then(function (d) {
      var mine = d.games.filter(function (g) { return ids.indexOf(g.id) >= 0; });
      fRoot.textContent = "";
      if (!mine.length) {
        var p = document.createElement("p"); p.textContent = "Todavía no sigues ningún juego. Toca la campana de un lanzamiento para seguirlo.";
        fRoot.appendChild(p); return;
      }
      var ul = document.createElement("ul"); ul.className = "srows";
      mine.forEach(function (g) { ul.appendChild(row(g)); });
      fRoot.appendChild(ul);
    });
  }

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

  // Avance del tráiler al pasar el cursor (o al tocar ▶ en el celular). Va sin sonido y no descarga nada antes.
  var withHls = function (cb) {
    if (window.Hls) return cb();
    var tag = document.querySelector("script[data-hls-lib]");
    if (!tag) {
      tag = document.createElement("script");
      tag.src = "assets/vendor/hls.light.min.js";
      tag.setAttribute("data-hls-lib", "1");
      document.head.appendChild(tag);
    }
    tag.addEventListener("load", function () { cb(); });
  };
  var startPreview = function (box) {
    if (box.querySelector(".hover-preview")) return;
    var hls = box.getAttribute("data-hls"), mp4 = box.getAttribute("data-video");
    var v = document.createElement("video");
    v.className = "hover-preview";
    v.muted = true; v.loop = true; v.playsInline = true; v.autoplay = true;
    v.setAttribute("muted", ""); v.setAttribute("playsinline", ""); v.setAttribute("aria-hidden", "true");
    v.addEventListener("playing", function () { box.classList.add("previewing"); });
    v.addEventListener("error", function () { stopPreview(box); });
    box.appendChild(v);
    if (mp4 || (hls && v.canPlayType("application/vnd.apple.mpegurl"))) {
      v.src = mp4 || hls;
      var p = v.play(); if (p && p.catch) p.catch(function () {});
    } else if (hls && "MediaSource" in window) {
      withHls(function () {
        if (!v.isConnected || !window.Hls) return;
        var h = new window.Hls({ enableWorker: false, startLevel: 0, capLevelToPlayerSize: true });
        h.on(window.Hls.Events.ERROR, function (e, data) { if (data.fatal) stopPreview(box); });
        h.loadSource(hls);
        h.attachMedia(v);
        v._hls = h;
        var p = v.play(); if (p && p.catch) p.catch(function () {});
      });
    } else {
      v.remove();
    }
  };
  var stopPreview = function (box) {
    box.classList.remove("previewing");
    box.querySelectorAll(".hover-preview").forEach(function (v) {
      if (v._hls) v._hls.destroy();
      v.pause(); v.removeAttribute("src"); v.load(); v.remove();
    });
  };
  if (!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches)) {
    var fine = window.matchMedia && window.matchMedia("(hover: hover) and (pointer: fine)").matches;
    document.querySelectorAll("[data-preview]").forEach(function (box) {
      var timer;
      if (fine) {
        var card = box.closest("li, article") || box;
        card.addEventListener("mouseenter", function () { timer = setTimeout(function () { startPreview(box); }, 350); });
        card.addEventListener("mouseleave", function () { clearTimeout(timer); stopPreview(box); });
      }
      var btn = box.querySelector(".preview-btn");
      if (btn) btn.addEventListener("click", function (ev) {
        ev.preventDefault();
        if (box.querySelector(".hover-preview")) stopPreview(box); else startPreview(box);
      });
    });
  }

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
  // Copiar un código de canje con un toque
  document.querySelectorAll("[data-copy]").forEach(function (btn) {
    if (!navigator.clipboard || !window.isSecureContext) return;
    btn.hidden = false;
    btn.addEventListener("click", function () {
      navigator.clipboard.writeText(btn.dataset.copy).then(function () {
        btn.textContent = "¡Copiado!";
        setTimeout(function () { btn.textContent = "Copiar"; }, 2500);
      });
    });
  });
  // ---------- Efectos visuales (se apagan si el usuario prefiere menos movimiento) ----------
  var calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches || !!prefs.lite;
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

  // Letras gigantes que se deslizan al bajar
  var megas = document.querySelectorAll(".mega");
  if (!calm && megas.length) {
    var megaTick = false;
    var moveMega = function () {
      megaTick = false;
      var vh = window.innerHeight;
      megas.forEach(function (m) {
        var r = m.getBoundingClientRect();
        if (r.bottom < -200 || r.top > vh + 200) return;
        var shift = (r.top - vh) * 0.35;
        m.firstElementChild.style.setProperty("--mx", (m.classList.contains("rev") ? -shift - 400 : shift) + "px");
      });
    };
    window.addEventListener("scroll", function () { if (!megaTick) { megaTick = true; requestAnimationFrame(moveMega); } }, { passive: true });
    moveMega();
  }

  // Carrusel 3D curvo (arrastrar, flechas, teclado y avance solo)
  document.querySelectorAll(".curve-stage").forEach(function (stage) {
    var items = Array.prototype.slice.call(stage.querySelectorAll(".curve-item"));
    if (!items.length) return;
    var cur = 0, n = items.length, drag = null, moved = 0, auto;
    var place = function (offset) {
      var w = items[0].offsetWidth || 300, wide = stage.offsetWidth < 600 ? 0.72 : 0.62;
      items.forEach(function (it, i) {
        var d = i - cur - (offset || 0);
        if (d > n / 2) d -= n;
        if (d < -n / 2) d += n;
        var a = Math.abs(d);
        it.style.transform = "translateX(" + (d * w * wide) + "px) translateZ(" + (-a * 140) + "px) rotateY(" + (-d * 32) + "deg)";
        it.style.opacity = a > 3.2 ? 0 : 1;
        it.style.zIndex = 100 - Math.round(a * 10);
        it.classList.toggle("is-center", a < 0.5);
        var link = it.querySelector("a");
        if (link) link.tabIndex = a < 0.5 ? 0 : -1;
      });
    };
    var go = function (step) { cur = (cur + step + n) % n; place(); };
    var stop = function () { clearInterval(auto); };
    var start = function () { stop(); if (!calm) auto = setInterval(function () { go(1); }, 3800); };
    stage.querySelector(".prev").addEventListener("click", function () { go(-1); start(); });
    stage.querySelector(".next").addEventListener("click", function () { go(1); start(); });
    stage.addEventListener("keydown", function (ev) {
      if (ev.key === "ArrowLeft") { go(-1); start(); }
      if (ev.key === "ArrowRight") { go(1); start(); }
    });
    stage.addEventListener("pointerdown", function (ev) {
      if (ev.target.closest(".curve-nav")) return;
      drag = ev.clientX; moved = 0; stage.classList.add("drag"); stop();
    });
    window.addEventListener("pointermove", function (ev) {
      if (drag === null) return;
      moved = ev.clientX - drag;
      place(-moved / ((items[0].offsetWidth || 300) * 0.62));
    });
    window.addEventListener("pointerup", function () {
      if (drag === null) return;
      stage.classList.remove("drag");
      var steps = Math.round(-moved / ((items[0].offsetWidth || 300) * 0.62));
      drag = null;
      go(steps);
      start();
    });
    items.forEach(function (it, i) {
      it.addEventListener("click", function (ev) {
        // un arrastre no abre el juego; tocar uno de los lados lo trae al centro
        if (Math.abs(moved) > 6 || !it.classList.contains("is-center")) {
          ev.preventDefault();
          if (Math.abs(moved) <= 6) { cur = i; place(); start(); }
        }
        moved = 0;
      });
    });
    stage.addEventListener("mouseenter", stop);
    stage.addEventListener("mouseleave", start);
    window.addEventListener("resize", function () { place(); });
    place();
    start();
  });

  // Cuenta regresiva de la próxima rebaja de Steam (hasta la medianoche del día de inicio, hora Colombia)
  document.querySelectorAll("[data-steam-countdown]").forEach(function (box) {
    var target = new Date(box.getAttribute("data-steam-countdown") + "T00:00:00-05:00").getTime();
    var put = function (k, v) { var el = box.querySelector('[data-cd="' + k + '"]'); if (el) el.textContent = v; };
    var tick = function () {
      var left = Math.max(0, target - Date.now()), sec = Math.floor(left / 1000);
      put("d", Math.floor(sec / 86400)); put("h", Math.floor(sec % 86400 / 3600));
      put("m", Math.floor(sec % 3600 / 60)); put("s", sec % 60);
    };
    tick();
    setInterval(tick, 1000);
  });

  // «Ya lo reclamé»: suma lo que has ahorrado con los juegos gratis (solo en este navegador)
  var claims = {};
  try { claims = JSON.parse(store("ogc-claims") || "{}") || {}; } catch (e) { claims = {}; }
  var showSaved = function () {
    var total = 0, count = 0;
    Object.keys(claims).forEach(function (k) { total += +claims[k] || 0; count++; });
    document.querySelectorAll("#saved-box").forEach(function (box) {
      box.hidden = !count;
      var t = box.querySelector("[data-saved-total]"), c = box.querySelector("[data-saved-count]");
      if (t) t.textContent = "$" + String(Math.round(total / 100) * 100).replace(/\B(?=(\d{3})+(?!\d))/g, ".") + " COP";
      if (c) c.textContent = count;
    });
  };
  document.querySelectorAll("[data-claim]").forEach(function (btn) {
    var id = btn.getAttribute("data-claim");
    btn.hidden = false;
    btn.setAttribute("aria-pressed", claims[id] ? "true" : "false");
    btn.addEventListener("click", function () {
      if (claims[id]) delete claims[id]; else claims[id] = +btn.getAttribute("data-value") || 0;
      store("ogc-claims", JSON.stringify(claims));
      document.querySelectorAll('[data-claim="' + id + '"]').forEach(function (b) { b.setAttribute("aria-pressed", claims[id] ? "true" : "false"); });
      showSaved();
    });
  });
  showSaved();

  // «Sorpréndeme»: abre una página de juego u oferta al azar
  var surprise = function () {
    return fetch("data/sorpresa.json").then(function (r) { return r.json(); }).then(function (list) {
      if (list && list.length) location.href = list[Math.floor(Math.random() * list.length)];
    });
  };
  document.querySelectorAll("[data-surprise]").forEach(function (a) {
    a.addEventListener("click", function (ev) { ev.preventDefault(); surprise().catch(function () { location.href = "ofertas.html"; }); });
  });
  if (document.getElementById("surprise-msg")) surprise().catch(function () {
    document.getElementById("surprise-msg").textContent = "No pudimos elegir uno ahora. Mira todas las ofertas.";
  });

  // Test «¿Qué juego me conviene?»
  var quiz = document.getElementById("quiz");
  if (quiz) {
    var el = function (tag, cls, text) {
      var n = document.createElement(tag);
      if (cls) n.className = cls;
      if (text) n.textContent = text;
      return n;
    };
    var answers = {}, go = document.getElementById("quiz-go"), out = document.getElementById("quiz-out"), again = document.getElementById("quiz-again");
    quiz.querySelectorAll(".quiz-opt").forEach(function (b) {
      b.addEventListener("click", function () {
        var q = b.getAttribute("data-q");
        answers[q] = b.getAttribute("data-v");
        quiz.querySelectorAll('.quiz-opt[data-q="' + q + '"]').forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
        go.disabled = !(answers.p && answers.g && answers.w);
      });
    });
    var pesos = function (v) { return "$" + String(Math.round(v / 100) * 100).replace(/\B(?=(\d{3})+(?!\d))/g, ".") + " COP"; };
    go.addEventListener("click", function () {
      fetch("data/test-juegos.json").then(function (r) { return r.json(); }).then(function (data) {
        var max = answers.p === "any" ? Infinity : +answers.p;
        var list = data.items.filter(function (x) {
          if (answers.w === "now" && x.k === "pronto") return false;
          if (answers.w === "soon" && x.k !== "pronto") return false;
          if (x.k !== "pronto" && x.p > max) return false;
          return answers.g === "any" || x.g.indexOf(answers.g) >= 0;
        });
        var weight = function (x) { return (x.k === "gratis" ? 3 : 0) + (x.d || 0) / 40 + (x.r ? Math.max(0, 3 - x.r / 40) : 0) + Math.random() * 1.5; };
        list.sort(function (a, b) { return weight(b) - weight(a); });
        var seen = {}, pick = [];
        list.forEach(function (x) { if (!seen[x.t] && pick.length < 6) { seen[x.t] = 1; pick.push(x); } });
        out.textContent = "";
        if (!pick.length) {
          out.appendChild(el("p", "notice", "Hoy no hay juegos que cumplan todo. Prueba con «De todo» o «Me da igual»."));
        } else {
          var ul = el("ul", "spot-grid small");
          pick.forEach(function (x) {
            var li = el("li", "spot-card"), box = el("div", "spot-img"), body = el("div", "spot-body");
            if (x.i) { var im = document.createElement("img"); im.src = x.i; im.alt = ""; im.loading = "lazy"; im.className = "spot-fg"; box.appendChild(im); }
            var tag = x.k === "gratis" || x.k === "f2p" ? "GRATIS" : x.k === "pronto" ? "PRONTO" : "-" + x.d + "%";
            box.appendChild(el("span", "badge", tag));
            var h = el("h3", "clamp2"), a = document.createElement("a");
            a.href = x.u; a.textContent = x.t; a.className = "title-link";
            if (/^https?:/.test(x.u)) { a.target = "_blank"; a.rel = "noopener noreferrer"; }
            h.appendChild(a); body.appendChild(h);
            body.appendChild(el("p", "meta", x.k === "pronto" ? "Sale pronto" : x.k === "f2p" ? "Gratis para siempre" : x.p ? pesos(x.p) + " aprox." : "Gratis por tiempo limitado"));
            li.appendChild(box); li.appendChild(body); ul.appendChild(li);
          });
          out.appendChild(el("h2", null, "Te recomendamos"));
          out.appendChild(ul);
        }
        again.hidden = false;
        out.scrollIntoView({ behavior: calm ? "auto" : "smooth", block: "start" });
      }).catch(function () { out.textContent = "No se pudo cargar la lista. Intenta de nuevo."; });
    });
    again.addEventListener("click", function () { go.click(); });
  }

  // Rueda de juegos gratis: cada portada en su lugar del anillo (el giro lo hace el CSS)
  var placeRings = function () {
    document.querySelectorAll(".ring").forEach(function (ring) {
      var tiles = ring.children, n = tiles.length, w = ring.offsetWidth || 190;
      var r = Math.max(w * 1.2, (w / 2) / Math.tan(Math.PI / n) + 24);
      Array.prototype.forEach.call(tiles, function (li, i) {
        li.style.transform = "rotateY(" + (i * 360 / n) + "deg) translateZ(" + Math.round(r) + "px)";
      });
    });
  };
  placeRings();
  window.addEventListener("resize", placeRings);

  // Murciélagos de Halloween (solo en temporada y si la persona no pidió menos movimiento)
  if (!calm && document.body && document.body.classList.contains("halloween")) {
    var bats = document.createElement("div");
    bats.className = "bats";
    bats.setAttribute("aria-hidden", "true");
    for (var b = 0; b < (window.innerWidth < 600 ? 3 : 5); b++) bats.appendChild(document.createElement("i")).className = "bat";
    var spider = bats.appendChild(document.createElement("i"));
    spider.className = "spider";
    spider.textContent = "🕷️";
    document.body.appendChild(bats);
  }

  // Intro con el logo: solo la primera vez que alguien entra
  if (!calm && !store("ogc-intro") && document.body) {
    store("ogc-intro", "1");
    var intro = document.createElement("div");
    intro.className = "intro";
    intro.setAttribute("aria-hidden", "true");
    intro.innerHTML = '<svg viewBox="0 0 600 160"><text x="300" y="80" text-anchor="middle">OFERTAS GAMER</text>' +
      '<text class="sub" x="300" y="128" text-anchor="middle">COLOMBIA</text></svg>';
    var closeIntro = function () { if (intro.parentNode) intro.parentNode.removeChild(intro); };
    intro.addEventListener("click", closeIntro);
    intro.addEventListener("animationend", function (ev) { if (ev.target === intro) closeIntro(); });
    document.body.appendChild(intro);
    setTimeout(closeIntro, 2500);
  }

  // Aparición de secciones y tarjetas
  if (!calm && "IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
    document.querySelectorAll("main h2, main .card, main .rel-card, main .spot-card, .stores li, .faq details, .stats li, .filters, .prose > *").forEach(function (el) {
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
