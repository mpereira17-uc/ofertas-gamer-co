// Pruebas de la función /api/lista-de-deseos (Cloudflare Pages) sin internet: se simula Steam.
// Correr: node --test tests/
import test from "node:test";
import assert from "node:assert/strict";
import { parseProfile, onRequestGet } from "../functions/api/lista-de-deseos.js";

const ID = "76561197960434622";

function fakeSteam(routes, calls = []) {
  return async (url) => {
    calls.push(url);
    for (const [part, body, status = 200] of routes) {
      if (url.includes(part)) {
        return new Response(typeof body === "string" ? body : JSON.stringify(body), { status });
      }
    }
    throw new Error("URL no esperada: " + url);
  };
}

const get = (perfil, fetcher) =>
  onRequestGet({ request: new Request("https://x.dev/api/lista-de-deseos?perfil=" + encodeURIComponent(perfil)) }, fetcher);

test("entiende enlaces, SteamID64 y nombres personalizados", () => {
  assert.deepEqual(parseProfile(ID), { steamid: ID });
  assert.deepEqual(parseProfile(`https://steamcommunity.com/profiles/${ID}/`), { steamid: ID });
  assert.deepEqual(parseProfile("https://steamcommunity.com/id/pepe_gamer/"), { vanity: "pepe_gamer" });
  assert.deepEqual(parseProfile("pepe-gamer"), { vanity: "pepe-gamer" });
});

test("rechaza entradas raras sin llamar a Steam", async () => {
  for (const bad of ["", "a", "https://evil.com/../x", "<script>", "../../etc/passwd", "x".repeat(40)]) {
    assert.equal(parseProfile(bad), null, bad);
  }
  const calls = [];
  const res = await get("<script>", fakeSteam([], calls));
  assert.equal(res.status, 400);
  assert.equal(calls.length, 0);
});

test("devuelve los appid de una lista pública", async () => {
  const res = await get(ID, fakeSteam([["IWishlistService", { response: { items: [{ appid: 50650 }, { appid: 215824 }, { appid: "x" }] } }]]));
  assert.equal(res.status, 200);
  assert.match(res.headers.get("Cache-Control"), /max-age=3600/);
  assert.deepEqual(await res.json(), { steamid: ID, appids: [50650, 215824] });
});

test("resuelve el nombre personalizado con el XML público del perfil", async () => {
  const calls = [];
  const res = await get("https://steamcommunity.com/id/pepe/", fakeSteam([
    ["steamcommunity.com/id/pepe/?xml=1", `<profile><steamID64>${ID}</steamID64></profile>`],
    ["IWishlistService", { response: { items: [{ appid: 10 }] } }],
  ], calls));
  assert.deepEqual((await res.json()).appids, [10]);
  assert.ok(calls.every((u) => u.startsWith("https://steamcommunity.com/") || u.startsWith("https://api.steampowered.com/")));
});

test("lista privada o vacía: mensaje claro", async () => {
  const body = await (await get(ID, fakeSteam([["IWishlistService", { response: {} }]]))).json();
  assert.deepEqual(body.appids, []);
  assert.match(body.error, /privada/);
});

test("perfil inexistente y Steam caído", async () => {
  const notFound = await get("nadie", fakeSteam([["steamcommunity.com", "<response><error>No se encontró</error></response>"]]));
  assert.equal(notFound.status, 404);
  const down = await get(ID, fakeSteam([["IWishlistService", "error", 503]]));
  assert.equal(down.status, 502);
});
