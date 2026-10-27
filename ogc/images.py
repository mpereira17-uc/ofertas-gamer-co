"""Imagen automática para compartir (1200x630): portada del juego, precio en pesos y descuento.

Usa Pillow si está instalado (en GitHub Actions se instala gratis). Si no está, simplemente no se genera
la imagen y todo lo demás sigue igual. Solo usa datos reales de la oferta.
"""

import io
import sys
from pathlib import Path

FONT = Path(__file__).resolve().parent.parent / "assets" / "fonts" / "bricolage-grotesque.woff2"
W, H = 1200, 630
GOLD, PINK, BLUE, RED = (255, 200, 61), (255, 61, 129), (77, 124, 255), (255, 61, 90)
INK, NIGHT, GREEN = (26, 16, 48), (10, 7, 22), (37, 224, 154)


def available():
    try:
        import PIL  # noqa: F401
        return True
    except ImportError:
        return False


def _font(size, weight="ExtraBold"):
    from PIL import ImageFont
    try:
        f = ImageFont.truetype(str(FONT), size)
        f.set_variation_by_name(weight)
        return f
    except Exception:
        for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf"):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
        return ImageFont.load_default()


def _wrap(draw, text, font, width, lines=2):
    words, out, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= width:
            cur = test
        else:
            if cur:
                out.append(cur)
            cur = w
        if len(out) == lines:
            break
    if cur and len(out) < lines:
        out.append(cur)
    if len(out) == lines and " ".join(out) != text:
        while out[-1] and draw.textlength(out[-1] + "…", font=font) > width:
            out[-1] = out[-1][:-1]
        out[-1] = out[-1].rstrip() + "…"
    return out


def card(title, cover_bytes, big, price, sub, kicker, footer="ofertas-gamer-co.pages.dev"):
    """Devuelve los bytes JPEG de la tarjeta. big: "GRATIS" o "-90%"; price: "$3.800 COP aprox."."""
    from PIL import Image, ImageDraw, ImageFilter
    img = Image.new("RGB", (W, H), NIGHT)
    cover = None
    if cover_bytes:
        try:
            cover = Image.open(io.BytesIO(cover_bytes)).convert("RGB")
        except Exception:
            cover = None
    if cover:
        bg = cover.copy()
        scale = max(W / bg.width, H / bg.height)
        bg = bg.resize((int(bg.width * scale) + 1, int(bg.height * scale) + 1)).crop((0, 0, W, H))
        bg = bg.filter(ImageFilter.GaussianBlur(28))
        img = Image.blend(img, bg, 0.55)
    shade = Image.new("RGB", (W, H), NIGHT)
    mask = Image.linear_gradient("L").rotate(90).resize((W, H))  # más oscuro a la derecha, para el texto
    img = Image.composite(shade, img, mask.point(lambda v: int(v * 0.85)))
    d = ImageDraw.Draw(img)
    # portada nítida a la izquierda
    if cover:
        cw = 560
        ch = int(cover.height * cw / cover.width)
        if ch > 420:
            ch = 420
            cw = int(cover.width * ch / cover.height)
        fg = cover.resize((cw, ch))
        x, y = 50, (H - ch) // 2 - 10
        d.rounded_rectangle((x - 6, y - 6, x + cw + 6, y + ch + 6), 22, fill=(255, 255, 255))
        img.paste(fg, (x, y))
        tx = x + cw + 46
    else:
        tx = 60
    tw = W - tx - 50
    d.text((tx, 70), kicker.upper(), font=_font(28, "Bold"), fill=GOLD)
    y = 116
    for line in _wrap(d, title, _font(54), tw, 3):
        d.text((tx, y), line, font=_font(54), fill=(255, 255, 255))
        y += 62
    y += 14
    bf = _font(64)
    bw = d.textlength(big, font=bf) + 44
    color = GREEN if big.upper() == "GRATIS" else GOLD
    d.rounded_rectangle((tx, y, tx + bw, y + 86), 18, fill=color)
    d.text((tx + 22, y + 6), big, font=bf, fill=INK)
    y += 108
    if price:
        d.text((tx, y), price, font=_font(40), fill=GOLD if big.upper() != "GRATIS" else GREEN)
        y += 52
    if sub:
        for line in _wrap(d, sub, _font(28, "SemiBold"), tw, 2):
            d.text((tx, y), line, font=_font(28, "SemiBold"), fill=(205, 198, 230))
            y += 36
    # franja con los colores de la bandera y la marca
    d.rectangle((0, H - 14, W // 2, H), fill=GOLD)
    d.rectangle((W // 2, H - 14, W * 3 // 4, H), fill=BLUE)
    d.rectangle((W * 3 // 4, H - 14, W, H), fill=RED)
    d.text((W - 50, H - 34), "Ofertas Gamer CO · " + footer, font=_font(24, "Bold"), fill=(230, 225, 245), anchor="rs")
    out = io.BytesIO()
    img.save(out, "JPEG", quality=84, optimize=True)
    return out.getvalue()


def offer_card(o, cover_bytes, pesos, kicker="Oferta del día"):
    free = o.get("currentPrice") == 0
    big = "GRATIS" if free else f"-{o.get('discountPercentage') or 0}%"
    if free:
        price = ""
    elif o.get("currency") == "COP":
        price = pesos(o["currentPrice"]) + " COP"
    elif o.get("copApproximation"):
        price = f"{pesos(o['copApproximation'])} COP aprox."
    else:
        price = f"US${o['currentPrice']:.2f}"
    try:
        return card(o["title"], cover_bytes, big, price, f"en {o['store']} · confirma el precio en la tienda", kicker)
    except Exception as exc:
        print(f"Imagen automática falló: {type(exc).__name__}", file=sys.stderr)
        return None


def top10(offers, covers, pesos, label):
    """Imagen vertical (1080x1350) con el top 10 de descuentos de la semana, para Telegram e Instagram.
    offers: las 10 ofertas; covers: bytes de cada portada (o None). Solo datos reales de las ofertas."""
    try:
        from PIL import Image, ImageDraw
        w, h = 1080, 1350
        img = Image.new("RGB", (w, h), NIGHT)
        d = ImageDraw.Draw(img)
        d.text((60, 54), "TOP 10 DE LA SEMANA", font=_font(30, "Bold"), fill=GOLD)
        d.text((60, 92), "Los mayores descuentos", font=_font(60), fill=(255, 255, 255))
        d.text((60, 166), label, font=_font(28, "SemiBold"), fill=(205, 198, 230))
        y, row = 222, 104
        for i, o in enumerate(offers[:10]):
            d.rounded_rectangle((40, y, w - 40, y + row - 12), 18, fill=(26, 20, 48))
            d.text((70, y + 22), f"{i + 1}", font=_font(48), fill=GOLD if i < 3 else (205, 198, 230))
            x = 140
            raw = covers[i] if i < len(covers) else None
            if raw:
                try:
                    c = Image.open(io.BytesIO(raw)).convert("RGB")
                    ch = row - 32
                    cw = int(c.width * ch / c.height)
                    img.paste(c.resize((cw, ch)), (x, y + 10))
                    x += cw + 22
                except Exception:
                    pass
            big = f"-{o.get('discountPercentage') or 0}%"
            bf = _font(40)
            bw = d.textlength(big, font=bf) + 28
            d.rounded_rectangle((w - 70 - bw, y + 22, w - 70, y + 74), 12, fill=GOLD)
            d.text((w - 70 - bw + 14, y + 24), big, font=bf, fill=INK)
            tw = w - 100 - bw - x
            name = _wrap(d, o["title"], _font(32), tw, 1)
            d.text((x, y + 14), name[0] if name else "", font=_font(32), fill=(255, 255, 255))
            if o.get("currency") == "COP":
                price = pesos(o["currentPrice"]) + " COP"
            elif o.get("copApproximation"):
                price = f"{pesos(o['copApproximation'])} COP aprox."
            else:
                price = f"US${o['currentPrice']:.2f}"
            d.text((x, y + 54), f"{price} · {o['store']}", font=_font(24, "SemiBold"), fill=GREEN)
            y += row
        d.text((60, h - 66), "Precios verificados al publicar. Confirma en la tienda.", font=_font(22, "SemiBold"), fill=(170, 160, 200))
        d.rectangle((0, h - 14, w // 2, h), fill=GOLD)
        d.rectangle((w // 2, h - 14, w * 3 // 4, h), fill=BLUE)
        d.rectangle((w * 3 // 4, h - 14, w, h), fill=RED)
        d.text((w - 50, h - 34), "ofertas-gamer-co.pages.dev", font=_font(24, "Bold"), fill=(230, 225, 245), anchor="rs")
        out = io.BytesIO()
        img.save(out, "JPEG", quality=86, optimize=True)
        return out.getvalue()
    except Exception as exc:
        print(f"Imagen del top 10 falló: {type(exc).__name__}", file=sys.stderr)
        return None
