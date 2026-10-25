"""Única función responsable de construir el enlace de destino de una oferta.

Mientras una tienda no esté aprobada (approved = false o affiliateUrl vacío) se devuelve el
enlace oficial normal y affiliate = False. Cuando Awin o Impact aprueben, el enlace que entregue
la plataforma se pega en config/stores.json (campo affiliateUrl) o en la variable de entorno
indicada en affiliateUrlVar (FANATICAL_AFFILIATE_URL, GMG_AFFILIATE_URL).

Plantilla admitida en affiliateUrl: debe contener {url} (el enlace oficial codificado). Ejemplo
de Impact: https://greenmangaming.sjv.io/c/XXXX/YYYY/ZZZZ?u={url}. Se usa tal como lo entrega la
red; no se añaden parámetros que la red no admita.
"""

import os
import urllib.parse


def affiliate_template(store):
    if not store.get("approved"):
        return ""
    var = store.get("affiliateUrlVar")
    template = (os.environ.get(var, "") if var else "") or store.get("affiliateUrl", "")
    return template if "{url}" in template and template.startswith("https://") else ""


def build_destination(official_url, store):
    """Devuelve (destination_url, affiliate, affiliate_network)."""
    template = affiliate_template(store)
    if not template:
        return official_url, False, None
    return template.replace("{url}", urllib.parse.quote(official_url, safe="")), True, store.get("affiliateNetwork")
