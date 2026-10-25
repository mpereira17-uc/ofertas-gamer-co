"""Historial de precios propio: en cada revisión se guarda el precio de cada juego en cada tienda.

Solo usa precios que el bot vio de verdad. "Mínimo histórico" significa el más bajo que hemos visto
desde que empezamos a seguir ese juego, y siempre se dice desde cuándo.
"""

from datetime import timedelta

from .model import slugify

KEEP_DAYS = 400
MIN_DAYS_FOR_LOW = 14  # no se habla de "mínimo" con menos de dos semanas de datos


def key(o):
    return f"{slugify(o['title'])}|{o['storeId']}|{o['currency']}"


def record(hist, offers, now):
    """Agrega el precio de hoy (el menor del día) de cada oferta y de sus otras tiendas."""
    day = now.strftime("%Y-%m-%d")
    for o in offers:
        for item in [o] + list(o.get("otherStores") or []):
            price = item.get("currentPrice")
            if price is None or not item.get("title") or not item.get("storeId") or not item.get("currency"):
                continue
            entry = hist.setdefault(key(item), {"title": item["title"], "points": []})
            entry["title"] = item["title"]
            if item.get("originalPrice"):
                entry["regular"] = item["originalPrice"]
            points = entry["points"]
            if points and points[-1][0] == day:
                points[-1][1] = min(points[-1][1], price)
            elif not points or points[-1][0] < day:
                points.append([day, price])
    return prune(hist, now)


def prune(hist, now):
    oldest = (now - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
    out = {}
    for k, entry in hist.items():
        points = [p for p in entry["points"] if p[0] >= oldest]
        if points:
            out[k] = dict(entry, points=points)
    return out


def days_between(a, b):
    from datetime import date
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def stats(hist, o, now):
    """Resumen del historial de una oferta: desde cuándo se sigue, el mínimo visto y si hoy es el mínimo."""
    entry = hist.get(key(o))
    if not entry or not entry["points"]:
        return None
    points = entry["points"]
    low = min(points, key=lambda p: (p[1], p[0]))
    first = points[0][0]
    tracked = days_between(first, now.strftime("%Y-%m-%d"))
    current = o.get("currentPrice")
    prices = {p[1] for p in points}
    is_low = (tracked >= MIN_DAYS_FOR_LOW and current is not None and current <= low[1] and len(prices) > 1)
    return {"first": first, "days": tracked, "low": low[1], "lowDate": low[0], "isLow": is_low,
            "points": points, "regular": entry.get("regular"), "count": len(points)}


def chart_svg(points, currency, fmt, width=640, height=180):
    """Gráfica de escalones (el precio se mantiene hasta que cambia) en SVG, sin JavaScript."""
    if len(points) < 2:
        return ""
    pad_l, pad_r, pad_t, pad_b = 8, 8, 16, 26
    first, last = points[0][0], points[-1][0]
    span = max(days_between(first, last), 1)
    values = [p[1] for p in points]
    lo, hi = min(values), max(values)
    if hi == lo:
        hi = lo + 1
    w, h = width - pad_l - pad_r, height - pad_t - pad_b
    x = lambda d: pad_l + w * days_between(first, d) / span
    y = lambda v: pad_t + h * (1 - (v - lo) / (hi - lo)) if values.count(values[0]) != len(values) else pad_t + h / 2
    path = f"M{x(points[0][0]):.1f},{y(points[0][1]):.1f}"
    for (d0, v0), (d1, v1) in zip(points, points[1:]):
        path += f" H{x(d1):.1f} V{y(v1):.1f}"
    low = min(points, key=lambda p: p[1])
    area = path + f" V{pad_t + h:.1f} H{pad_l:.1f} Z"
    return (f'<svg class="price-chart" viewBox="0 0 {width} {height}" role="img" '
            f'aria-label="Historial de precio desde {first} hasta {last}: mínimo {fmt(low[1], currency)}">'
            f'<path class="pc-area" d="{area}"/><path class="pc-line" d="{path}"/>'
            f'<circle class="pc-low" cx="{x(low[0]):.1f}" cy="{y(low[1]):.1f}" r="5"/>'
            f'<text class="pc-label" x="{pad_l}" y="{height - 6}">{first[8:10]}/{first[5:7]}</text>'
            f'<text class="pc-label" x="{width - pad_r}" y="{height - 6}" text-anchor="end">{last[8:10]}/{last[5:7]}</text>'
            f'</svg>')
