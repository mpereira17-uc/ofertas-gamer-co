# Seguridad

Si encuentras un problema de seguridad (por ejemplo, un secreto expuesto o un enlace malicioso), no abras una incidencia pública: escribe por Telegram a https://t.me/ofertasgamerco o usa **Security → Report a vulnerability** en GitHub.

- Los tokens viven solo en **Settings → Secrets and variables → Actions**.
- Nunca se guardan contraseñas, datos bancarios ni archivos `.env` en el repositorio.
- `scripts/check_site.py` busca patrones de secretos en cada ejecución.
