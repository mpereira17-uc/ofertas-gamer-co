"""Textos originales del sitio: guías, preguntas frecuentes y páginas informativas.

Los textos legales son una base de trabajo y deben revisarse con un profesional antes de
considerarlos definitivos.
"""

LEGAL_UPDATED = "24 de octubre de 2026"
LEGAL_REVIEW = ("<p class=\"notice\">Este texto es una base de trabajo redactada para un proyecto pequeño. "
                "Recomendamos una revisión jurídica profesional antes de considerarlo definitivo.</p>")

GUIDES = [
    {
        "slug": "guia-tienda-oficial",
        "title": "Cómo reconocer una tienda oficial de videojuegos",
        "description": "Señales para saber si una tienda de juegos para PC vende licencias oficiales y cómo evitar revendedores no autorizados.",
        "date": "2026-10-24",
        "body": """
<p>Una tienda oficial vende claves o licencias que recibe directamente de la editorial o de un distribuidor autorizado. Comprar ahí protege tu cuenta: la clave no se revoca después y tienes a quién reclamar.</p>
<h2>Señales de una tienda oficial</h2>
<ul>
<li>La propia editorial la menciona como punto de venta, o el juego aparece en la tienda de la plataforma (Steam, Epic Games Store, GOG).</li>
<li>Vende juegos nuevos el día de lanzamiento, con precios similares a los de la plataforma.</li>
<li>Tiene políticas claras de reembolso, soporte y datos de la empresa.</li>
<li>No funciona como un mercado donde cualquier persona revende claves.</li>
</ul>
<h2>Señales de alerta</h2>
<ul>
<li>Precios muy por debajo del resto del mercado en juegos recién lanzados.</li>
<li>Vendedores particulares con calificaciones y nombres genéricos.</li>
<li>Avisos de que la clave es de otra región o que "puede requerir VPN".</li>
<li>Cobros extra por una "protección del comprador" que en una tienda oficial no hace falta.</li>
</ul>
<h2>Qué hacemos en Ofertas Gamer CO</h2>
<p>Solo mostramos tiendas de una lista autorizada que puedes ver en la página <a href="tiendas.html">Tiendas</a>. Si una tienda no está en esa lista, sus ofertas no se publican.</p>
""",
    },
    {
        "slug": "guia-clave-regional-global",
        "title": "Diferencia entre una clave regional y una global",
        "description": "Qué significa que una clave de juego tenga restricción regional y qué revisar antes de comprarla desde Colombia.",
        "date": "2026-10-24",
        "body": """
<p>Una clave global se puede activar desde cualquier país. Una clave regional solo funciona en ciertos países o zonas, por ejemplo "Latinoamérica" o "Europa". Si compras una clave de otra región, es posible que la plataforma no te deje activarla.</p>
<h2>Antes de comprar desde Colombia</h2>
<ol>
<li>Busca en la página del producto la sección de activación o región ("Region", "Activation", "Restricciones").</li>
<li>Comprueba que diga global, Latinoamérica o que incluya a Colombia.</li>
<li>Revisa en qué plataforma se activa (Steam, GOG, Epic, etc.) y que tengas una cuenta ahí.</li>
<li>Si la tienda no informa la región, pregunta al soporte antes de pagar.</li>
</ol>
<h2>Sobre los precios que mostramos</h2>
<p>Algunas de nuestras fuentes informan el precio de referencia de la tienda en dólares de Estados Unidos. En Colombia el precio puede ser distinto por los precios regionales de cada plataforma. Por eso indicamos la región cuando la conocemos y marcamos el valor en pesos como aproximado.</p>
""",
    },
    {
        "slug": "guia-juegos-gratis-temporales",
        "title": "Cómo funcionan los juegos gratuitos temporales",
        "description": "Cómo reclamar un juego gratis por tiempo limitado, por qué queda en tu biblioteca y qué condiciones revisar.",
        "date": "2026-10-24",
        "body": """
<p>Algunas tiendas regalan juegos durante unos días para atraer usuarios. Lo habitual es que, si lo reclamas dentro del plazo, el juego quede en tu biblioteca aunque la promoción termine. Las condiciones exactas las pone cada tienda.</p>
<h2>Cómo reclamar correctamente</h2>
<ol>
<li>Entra a la página oficial del juego en la tienda desde nuestro botón "Ver oferta".</li>
<li>Inicia sesión con tu cuenta de la tienda.</li>
<li>Confirma que el precio final sea 0 antes de aceptar. No deberías tener que poner datos de tarjeta para un juego gratis.</li>
<li>Pulsa el botón de obtener o añadir a la biblioteca y espera la confirmación.</li>
</ol>
<h2>Qué revisar</h2>
<ul>
<li>La fecha de fin de la promoción. La mostramos cuando la tienda la publica.</li>
<li>Si el juego es gratis para siempre o solo un fin de semana de prueba ("free weekend").</li>
<li>Los requisitos de tu computador, antes de descargar varios gigas.</li>
</ul>
""",
    },
    {
        "slug": "guia-enlaces-afiliados",
        "title": "Cómo funcionan los enlaces de afiliados",
        "description": "Qué es un enlace de afiliado, por qué no cambia el precio que pagas y cómo los identificamos en Ofertas Gamer CO.",
        "date": "2026-10-24",
        "body": """
<p>Un enlace de afiliado lleva a la misma página oficial de la tienda, pero con un identificador que le indica a la tienda que la visita llegó desde un sitio colaborador. Si compras, la tienda puede pagarle una comisión a ese sitio. El precio que pagas es el mismo.</p>
<h2>Cómo lo manejamos</h2>
<ul>
<li>Solo usamos enlaces de afiliado de programas que nos hayan aprobado. Mientras no exista aprobación, el enlace es el normal de la tienda.</li>
<li>Cada oferta con enlace de afiliado muestra la etiqueta <strong>Enlace de afiliado</strong>.</li>
<li>La posible comisión no decide qué ofertas aparecen. Las ofertas se eligen por descuento, precio y vigencia.</li>
</ul>
<p>Puedes leer más en nuestro <a href="afiliados.html">aviso de afiliados</a>.</p>
""",
    },
    {
        "slug": "guia-que-es-drm",
        "title": "Qué significa DRM en un juego de PC",
        "description": "Qué es el DRM, qué cambia entre un juego con DRM y uno sin DRM, y dónde revisarlo antes de comprar.",
        "date": "2026-10-24",
        "body": """
<p>DRM (gestión de derechos digitales) es el sistema que controla cómo usas una licencia. En PC, lo más común es que el juego quede ligado a una cuenta de una plataforma como Steam o Epic Games Store, y que necesites esa aplicación para jugar.</p>
<h2>Con DRM y sin DRM</h2>
<ul>
<li><strong>Con DRM de plataforma:</strong> el juego se activa en tu cuenta y se descarga desde la aplicación de la plataforma.</li>
<li><strong>Sin DRM:</strong> recibes un instalador que puedes guardar y usar sin una aplicación obligatoria. GOG ofrece muchos juegos así, aunque conviene revisarlo en cada ficha.</li>
<li>Algunos juegos piden además una cuenta de la editorial o conexión permanente a internet.</li>
</ul>
<h2>Dónde revisarlo</h2>
<p>En la ficha oficial del juego busca la sección de activación, requisitos o "DRM". Si en una tarjeta de Ofertas Gamer CO no indicamos el DRM es porque la fuente no lo informó.</p>
""",
    },
]

FAQ = [
    ("¿Ofertas Gamer CO vende juegos?",
     "No. Mostramos ofertas de tiendas oficiales y te enviamos a su página. La compra, el pago, la garantía y la licencia son responsabilidad de la tienda."),
    ("¿Cada cuánto se actualizan las ofertas?",
     "Cada cuatro horas de forma automática. En cada tarjeta mostramos la fecha y hora en que la verificamos."),
    ("¿Por qué el precio en pesos dice aproximado?",
     "Porque es una conversión desde la moneda de la tienda con la tasa del día. Tu banco, los impuestos y los precios regionales pueden cambiar el valor final."),
    ("¿Los juegos gratis quedan para siempre?",
     "Normalmente sí, si los reclamas antes de que termine la promoción. Revisa las condiciones de cada tienda; lo explicamos en la guía de juegos gratuitos temporales."),
    ("¿Ganan dinero con los enlaces?",
     "Algunos enlaces pueden ser de afiliado. Cuando lo son, la oferta muestra la etiqueta Enlace de afiliado; los demás son enlaces normales de la tienda."),
    ("¿Cómo reporto una oferta vencida o un precio incorrecto?",
     "Escríbenos por Telegram o abre un reporte en GitHub desde la página de contacto."),
]
