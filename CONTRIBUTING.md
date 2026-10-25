# Cómo contribuir

1. Crea una rama desde `main`.
2. Haz cambios pequeños y prueba:
   ```
   python -m unittest discover -s tests -t .
   python bot.py --fixtures tests/fixtures --no-send
   python scripts/check_site.py
   ```
3. Abre un pull request con la plantilla. El flujo **Calidad** debe quedar en verde.

Reglas de contenido: no inventar ofertas, precios, fechas ni afiliaciones; textos originales; toda publicidad identificada. Las guías nuevas van en `ogc/content.py` y llegan por pull request para revisión humana.
