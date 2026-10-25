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
      var dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      var current = document.documentElement.getAttribute("data-theme") || (dark ? "dark" : "light");
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
    form.addEventListener("input", applyFilters);
    form.addEventListener("submit", function (e) { e.preventDefault(); applyFilters(); });
    applyFilters();
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
})();
