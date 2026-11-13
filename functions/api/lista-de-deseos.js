// Función de Cloudflare Pages: GET /api/lista-de-deseos?perfil=<enlace, SteamID64 o nombre personalizado>
// Devuelve los appid de la lista de deseos PÚBLICA de un perfil de Steam, para cruzarlos con las ofertas.
// Steam no permite pedir esa lista desde el navegador (sin CORS), por eso pasa por aquí.
// Seguridad: solo habla con dos direcciones fijas de Steam (no es un proxy abierto), valida la entrada,
// no guarda nada y deja la respuesta en la caché de Cloudflare 1 hora para no repetir consultas.

const STEAMID = /^7656119\d{10}$/;
const VANITY = /^[A-Za-z0-9_-]{2,32}$/;
const MAX_ITEMS = 2000;

export function parseProfile(raw) {
  const text = String(raw || "").trim().slice(0, 200);
  if (!text) return null;
  if (STEAMID.test(text)) return { steamid: text };
  let m = text.match(/steamcommunity\.com\/profiles\/(7656119\d{10})/i);
  if (m) return { steamid: m[1] };
  m = text.match(/steamcommunity\.com\/id\/([A-Za-z0-9_-]{2,32})/i);
  if (m) return { vanity: m[1] };
  if (VANITY.test(text)) return { vanity: text };
  return null;
}

function json(body, status = 200, maxAge = 0) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": maxAge ? `public, max-age=${maxAge}` : "no-store",
      "X-Content-Type-Options": "nosniff",
    },
  });
}

async function steamFetch(url, fetcher) {
  const res = await fetcher(url, {
    headers: { "User-Agent": "OfertasGamerCO/1.0", Accept: "application/json, text/xml" },
    signal: AbortSignal.timeout(8000),
  });
  if (!res.ok) throw new Error("steam " + res.status);
  return res;
}

export async function resolveVanity(vanity, fetcher = fetch) {
  const res = await steamFetch(`https://steamcommunity.com/id/${encodeURIComponent(vanity)}/?xml=1`, fetcher);
  const xml = (await res.text()).slice(0, 20000);
  const m = xml.match(/<steamID64>(7656119\d{10})<\/steamID64>/);
  return m ? m[1] : null;
}

export async function wishlistAppids(steamid, fetcher = fetch) {
  const res = await steamFetch(`https://api.steampowered.com/IWishlistService/GetWishlist/v1/?steamid=${steamid}`, fetcher);
  const data = await res.json();
  const items = (data && data.response && Array.isArray(data.response.items)) ? data.response.items : [];
  return items.map((it) => Number(it && it.appid)).filter((n) => Number.isInteger(n) && n > 0).slice(0, MAX_ITEMS);
}

export async function onRequestGet({ request }, fetcher = fetch) {
  const url = new URL(request.url);
  const who = parseProfile(url.searchParams.get("perfil"));
  if (!who) return json({ error: "Escribe el enlace de tu perfil de Steam, tu SteamID64 o tu nombre personalizado." }, 400);

  const cache = typeof caches !== "undefined" ? caches.default : null;
  const key = new Request(`https://cache.ofertas-gamer-co/lista-de-deseos/${who.steamid || "id-" + who.vanity.toLowerCase()}`);
  if (cache) {
    const hit = await cache.match(key);
    if (hit) return hit;
  }
  try {
    const steamid = who.steamid || (await resolveVanity(who.vanity, fetcher));
    if (!steamid) return json({ error: "No encontramos ese perfil de Steam. Revisa el enlace." }, 404, 600);
    const appids = await wishlistAppids(steamid, fetcher);
    const out = appids.length
      ? json({ steamid, appids }, 200, 3600)
      : json({ steamid, appids: [], error: "La lista de deseos está vacía o es privada. En Steam, ve a Editar perfil → Privacidad y pon «Detalles del juego» en Público." }, 200, 600);
    if (cache) await cache.put(key, out.clone());
    return out;
  } catch (err) {
    return json({ error: "Steam no respondió. Intenta de nuevo en unos minutos." }, 502);
  }
}
