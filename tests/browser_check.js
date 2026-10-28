// Prueba en navegador (Playwright): node tests/browser_check.js http://127.0.0.1:8765/
const { chromium } = require("playwright");
const base = process.argv[2] || "http://127.0.0.1:8765/";
const pages = ["index.html", "juegos-gratis.html", "ofertas.html", "tiendas.html", "guias.html", "contacto.html",
  "privacidad.html", "afiliados.html", "404.html", "estado.html", "guia-que-es-drm.html", "favoritos.html",
  "resumen-semanal.html", "juegos-baratos.html", "lanzamientos-playstation.html", "juegos-gratis-para-siempre.html", "alertas.html",
  "oferta-del-dia.html", "minimos-historicos.html", "buscar.html", "glosario.html", "estadisticas.html", "todos-los-juegos-gratis-de-epic.html", "juegos-menos-de-10000-pesos.html", "ofertas-mejor-valoradas.html", "juegos-gratis-en-todas-las-tiendas.html", "noticias.html"];

(async () => {
  const browser = await chromium.launch();
  const errors = [];
  for (const width of [360, 1280]) {
    const ctx = await browser.newContext({ viewport: { width, height: 800 } });
    await ctx.grantPermissions(["clipboard-read", "clipboard-write"], { origin: new URL(base).origin });
    const page = await ctx.newPage();
    page.on("console", (m) => { if (m.type() === "error") errors.push(`${width}px ${page.url()}: ${m.text()}`); });
    page.on("pageerror", (e) => errors.push(`${width}px ${page.url()}: ${e.message}`));
    for (const p of pages) {
      await page.route(/^https:\/\//, (r) => r.fulfill({ status: 200, contentType: "image/svg+xml", body: "<svg xmlns='http://www.w3.org/2000/svg'/>" }));
      await page.goto(base + p, { waitUntil: "load" });
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      if (overflow > 0) errors.push(`${width}px ${p}: desplazamiento horizontal de ${overflow}px`);
      const small = await page.evaluate(() => parseFloat(getComputedStyle(document.body).fontSize));
      if (small < 16) errors.push(`${width}px ${p}: letra base ${small}px`);
    }
    await page.goto(base + "index.html");
    if (width === 360 && !(await page.isVisible("nav.bottom-nav"))) errors.push("360px: falta el menú inferior");
    if (width === 1280 && (await page.isVisible("nav.bottom-nav"))) errors.push("1280px: el menú inferior no debería verse");
    // portada por capítulos: la escena se fija y los botones llevan a cada oferta destacada
    if (await page.$(".tide")) {
      const tide = await page.evaluate(() => { const t = document.querySelector(".tide"); return { on: t.classList.contains("on"), n: t.querySelectorAll(".td-ch").length }; });
      if (tide.n > 1 && !tide.on) errors.push(`${width}px: la portada animada no se activó`);
      if (tide.on) {
        await page.click(".td-rail [data-go='1']");
        await page.waitForTimeout(1500);
        const cur = await page.getAttribute(".td-rail [data-go='1']", "aria-current");
        if (cur !== "true") errors.push(`${width}px: el botón 2 de la portada no lleva a la segunda oferta`);
        await page.evaluate(() => window.scrollTo(0, 0));
      }
      const calm = await browser.newContext({ viewport: { width, height: 800 }, reducedMotion: "reduce" });
      const cp = await calm.newPage();
      await cp.route(/^https:\/\//, (r) => r.fulfill({ status: 200, contentType: "image/svg+xml", body: "<svg xmlns='http://www.w3.org/2000/svg'/>" }));
      await cp.goto(base + "index.html");
      if (await cp.$eval(".tide", (t) => t.classList.contains("on"))) errors.push(`${width}px: con «menos movimiento» la portada no debería animarse`);
      await calm.close();
    }
    if (width === 360) {
      if (await page.isVisible("#main-nav")) errors.push("360px: el menú debería estar plegado");
      await page.click("#menu-toggle");
      if (!(await page.isVisible("#main-nav"))) errors.push("360px: el menú no se abre");
    }
    await page.goto(base + "ofertas.html");
    const total = await page.$$eval("#offers > li", (els) => els.length);
    await page.fill("#filters input[name=q]", "hollow");
    const visible = await page.$$eval("#offers > li:not([hidden])", (els) => els.length);
    if (!(visible >= 1 && visible < total)) errors.push(`${width}px: el buscador no filtra (${visible}/${total})`);
    await page.fill("#filters input[name=q]", "");
    await page.selectOption("#filters select[name=type]", "gratis");
    const free = await page.$$eval("#offers > li:not([hidden])", (els) => els.map((e) => e.dataset.type));
    if (!free.length || free.some((t) => t !== "gratis")) errors.push(`${width}px: el filtro gratis falla`);
    await page.selectOption("#filters select[name=type]", "");
    await page.selectOption("#filters select[name=sort]", "discount");
    const discounts = await page.$$eval("#offers > li", (els) => els.map((e) => +e.dataset.discount));
    if (discounts.join() !== [...discounts].sort((a, b) => b - a).join()) errors.push(`${width}px: orden por descuento falla`);
    await page.goto(base + "ofertas.html?max=20000&orden=vence");
    const cheap = await page.$$eval("#offers > li:not([hidden])", (els) => els.map((e) => +e.dataset.cop));
    if (await page.inputValue("#filters select[name=sort]") !== "expires") errors.push(`${width}px: ?orden=vence no aplica`);
    if (cheap.some((c) => c >= 20000)) errors.push(`${width}px: filtro de precio máximo falla`);
    await page.goto(base + "ofertas.html");
    const before = page.url();
    await page.click('.quick-chips a[href="?orden=score"]');
    if (await page.inputValue("#filters select[name=sort]") !== "score") errors.push(`${width}px: el atajo Vale la pena no ordena`);
    if (await page.getAttribute('.quick-chips a[href="?orden=score"]', "aria-pressed") !== "true") errors.push(`${width}px: el atajo no se marca`);
    await page.click('.quick-chips a[href="?tipo=gratis"]');
    const onlyFree = await page.$$eval("#offers > li:not([hidden])", (els) => els.every((e) => e.dataset.type === "gratis"));
    if (!onlyFree || await page.getAttribute('.quick-chips a[href="?orden=score"]', "aria-pressed") !== "false") errors.push(`${width}px: cambiar de atajo falla`);
    await page.click('.quick-chips a[href="?tipo=gratis"]');
    if (await page.inputValue("#filters select[name=type]") !== "") errors.push(`${width}px: el atajo no se quita con otro clic`);
    if (new URL(page.url()).pathname !== new URL(before).pathname) errors.push(`${width}px: el atajo recargó la página`);
    await page.goto(base + "favoritos.html");
    await page.waitForSelector("#fav-root .fav-empty");
    await page.goto(base + "ofertas.html");
    await page.click("#offers > li:first-child [data-fav]");
    await page.goto(base + "favoritos.html");
    await page.waitForSelector("#fav-root .card");
    const favCount = await page.$$eval("#fav-root .card", (els) => els.length);
    if (favCount !== 1) errors.push(`${width}px: favoritos muestra ${favCount} tarjetas`);
    const cd = await page.$$eval("[data-countdown] span", (els) => els.map((e) => e.textContent));
    if (cd.some((t) => !/^(Termina en|Disponible hasta|Terminó)/.test(t))) errors.push(`${width}px: contador con texto raro`);
    await page.goto(base + "juego-nave-estelar.html");
    await page.route(/\.mp4$/, (r) => r.fulfill({ status: 200, contentType: "video/mp4", body: "" }));
    if (!(await page.isVisible(".play-btn"))) errors.push(`${width}px: falta el botón de tráiler`);
    await page.click(".play-btn");
    if (!(await page.$("#trailer video.trailer-player"))) errors.push(`${width}px: el tráiler no se abre`);
    await ctx.close();
  }
  await browser.close();
  if (errors.length) { console.log(errors.join("\n")); process.exit(1); }
  console.log("Prueba de navegador OK (360px y 1280px)");
})();
