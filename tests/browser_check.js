// Prueba en navegador (Playwright): node tests/browser_check.js http://127.0.0.1:8765/
const { chromium } = require("playwright");
const base = process.argv[2] || "http://127.0.0.1:8765/";
const pages = ["index.html", "juegos-gratis.html", "ofertas.html", "tiendas.html", "guias.html", "contacto.html",
  "privacidad.html", "afiliados.html", "whatsapp.html", "404.html", "estado.html", "guia-que-es-drm.html"];

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
    if (width === 360) {
      if (await page.isVisible("#main-nav")) errors.push("360px: el menú debería estar plegado");
      await page.click("#menu-toggle");
      if (!(await page.isVisible("#main-nav"))) errors.push("360px: el menú no se abre");
    }
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
    await page.goto(base + "whatsapp.html");
    await page.click("#copy-wa");
    const copied = await page.evaluate(() => navigator.clipboard.readText());
    if (!copied.startsWith("*") || /&(lt|gt|amp|quot);|<\/?(a|b|br|p)\b/.test(copied)) errors.push(`${width}px: texto de WhatsApp no limpio`);
    await ctx.close();
  }
  await browser.close();
  if (errors.length) { console.log(errors.join("\n")); process.exit(1); }
  console.log("Prueba de navegador OK (360px y 1280px)");
})();
