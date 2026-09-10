# -*- coding: utf-8 -*-
import os
import re
import shutil
import urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, "dist")
WHATSAPP_NUMBER = "5491149287469"  # +54 9 11 4928-7469
EMAIL = "ventas@ayhsrl.com.ar"
ADDRESS = "Río Cuarto 1636, C1292 — Ciudad Autónoma de Buenos Aires"
HOURS = "Lunes a viernes de 8 a 17 hs"
MAPS_EMBED_SRC = "https://www.google.com/maps?q=-34.6486792,-58.3715902(ACCESORIOS+Y+HERRAMIENTAS+SRL)&z=16&output=embed"
MAPS_LINK = "https://maps.app.goo.gl/GENGg2YMNFfKcSaY7"
REVIEWS_URL = "https://www.google.com/search?q=Accesorios+y+Herramientas+SRL+opiniones"

# Reseñas reales de Google de Accesorios y Herramientas SRL (quienes traen Britzen a
# Argentina) — 4.9/5, 109 opiniones al momento de la consulta.
REVIEWS = [
    {"author": "Rosario Melgarejo", "text": "Excelente atención y servicio. Responden rápido aunque sea su horario de almuerzo. Los precios también son para destacar, ¡más barato que Mercado Libre! Muchas gracias por la atención."},
    {"author": "David Terra", "text": "Atención muy buena, cordiales, se toman el tiempo para atenderte correctamente. Muy recomendable, productos buenos y buenos precios."},
    {"author": "Mauricio Chavez", "text": "Excelente atención. Y los productos cumplen con todas las especificaciones técnicas y de calidad."},
    {"author": "Sabrus B.", "text": "Excelente atención y atentos, muy recomendable. El producto de buena calidad."},
]
REVIEWS_SCORE = "4.9"
REVIEWS_COUNT = "109"

# Precios reales cruzados por SKU desde Contabilium (columna "Precio en AR$").
CONTENT_DIR = os.path.join(ROOT, "content", "productos")

def wa_link(message):
    return "https://wa.me/{}?text={}".format(WHATSAPP_NUMBER, urllib.parse.quote(message))

def slugify(text):
    text = text.lower()
    replacements = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n", "ü": "u"}
    for a, b in replacements.items():
        text = text.replace(a, b)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text


def smart_title(raw):
    """Convierte texto en MAYÚSCULAS a un título legible, preservando siglas,
    medidas y tokens con números tal cual vienen (PSI, TDI, 0-1000, 1/2, etc.),
    bajando conectores en minúscula y corrigiendo tildes de uso frecuente que
    faltan en el Excel de origen."""
    KEEP_AS_IS = {
        "PSI", "TDI", "TSI", "FSI", "MPI", "VW", "K4M", "SIGMA", "LTS", "MM", "CM",
        "KGF", "NM", "N.M", "U$S", "MSI", "16V", "TFSI", "TDCI",
    }
    STOPWORDS = {"de", "del", "y", "o", "a", "el", "la", "los", "las", "en", "al", "con", "para", "por"}
    ACCENT_FIX = {
        "Torquimetro": "Torquímetro", "Compresometro": "Compresómetro", "Valvula": "Válvula",
        "Valvulas": "Válvulas", "Piston": "Pistón", "Electricos": "Eléctricos",
        "Plasticos": "Plásticos", "Presion": "Presión", "Admision": "Admisión",
        "Refrigeracion": "Refrigeración", "Vacio": "Vacío", "Deteccion": "Detección",
        "Sincronizar": "Sincronizar", "Automotriz": "Automotriz", "Mecanico": "Mecánico",
    }
    TITLE_FIX = {"Vw": "VW", "Audi": "Audi", "Ford": "Ford", "Renault": "Renault", "Chevrolet": "Chevrolet"}
    words = raw.strip().split(" ")
    out = []
    for i, w in enumerate(words):
        if not w:
            continue
        core = w.strip(".,")
        if core.upper() in KEEP_AS_IS or any(ch.isdigit() for ch in w) or "/" in w:
            out.append(w)
        elif core.lower() in STOPWORDS and i != 0:
            out.append(core.lower())
        else:
            fixed = w.capitalize()
            fixed = ACCENT_FIX.get(fixed, fixed)
            out.append(TITLE_FIX.get(fixed, fixed))
    return " ".join(out)


CATEGORY_FIX = {
    "Compresometro": "Compresómetro", "Suspension": "Suspensión", "Refrigeracion": "Refrigeración",
    "Vacuometro": "Vacuómetro", "Prensa Valvula": "Prensa Válvula", "Torquimetro": "Torquímetro",
}


def load_master_products(content_dir):
    import yaml
    records = []
    for fname in sorted(os.listdir(content_dir)):
        if not fname.endswith(".md"):
            continue
        path = os.path.join(content_dir, fname)
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        if not raw.startswith("---"):
            continue
        _, fm_text, body = raw.split("---", 2)
        front = yaml.safe_load(fm_text) or {}
        sku = str(front.get("sku") or "").strip()
        nombre = front.get("title") or ""
        if not sku or not nombre:
            continue
        cat_raw = str(front.get("category") or "Sin categoría").strip()
        photos = front.get("photos") or []
        records.append({
            "sku": sku,
            "name_raw": str(nombre).strip(),
            "category": CATEGORY_FIX.get(cat_raw, cat_raw),
            "desc_raw": body.strip() or None,
            "price": front.get("price") or None,
            "mla": str(front["mla"]).strip() if front.get("mla") else None,
            "photos": photos,
        })
    return records


# ---------------------------------------------------------------------------
# Parser de descripciones completas (columna "Descripcion" del Excel).
# Separa el texto en: resumen corto (para la ficha, arriba) + secciones
# estructuradas (características técnicas, contenido del kit, aplicaciones,
# advertencias, etc.) para el bloque "Descripción completa", abajo.
# No inventa nada: si el texto no trae una sección, esa sección no se muestra.
# ---------------------------------------------------------------------------

SECTION_KEYWORDS = [
    ("caracteristicas", r'caracter[ií]sticas(?:\s+t[eé]cnicas)?', "Características técnicas"),
    ("contenido_kit", r'contenido del kit', "Contenido del kit"),
    ("accesorios", r'accesorios', "Accesorios"),
    ("presentacion", r'presentaci[oó]n', "Presentación"),
    ("ventajas", r'principales ventajas', "Principales ventajas"),
    ("posiciones", r'posiciones? de armado', "Posiciones de armado"),
    ("aplicaciones", r'aplicaciones', "Aplicaciones"),
    ("importante", r'importante', None),
    ("puntos_clave", r'puntos clave a saber', "Puntos clave a saber"),
    ("recomendaciones", r'recomendaciones', "Recomendaciones"),
    ("usos", r'\busos\b', "Usos"),
]

UPPER_KEEP = {
    "BRITZEN", "PSI", "BAR", "KPA", "MM", "CM", "NM", "BSP", "CR-V", "TDI", "TSI",
    "VW", "SSP", "ABS", "PP", "SS", "201SS",
}


def fix_allcaps(text):
    """Si el texto viene casi todo en mayúsculas (formato de origen distinto),
    lo pasa a formato oración conservando siglas y unidades reconocidas."""
    letters = [c for c in text if c.isalpha()]
    if not letters or sum(1 for c in letters if c.isupper()) / len(letters) < 0.6:
        return text
    words = text.split(" ")
    out = []
    capitalize_next = True
    for w in words:
        core = w.strip(".,:;()\"")
        if core.upper() in UPPER_KEEP or any(ch.isdigit() for ch in w):
            out.append(w)
            capitalize_next = w.rstrip().endswith((".", ":"))
            continue
        lw = w.lower()
        if capitalize_next:
            for i, ch in enumerate(lw):
                if ch.isalpha():
                    lw = lw[:i] + ch.upper() + lw[i + 1:]
                    break
        out.append(lw)
        capitalize_next = w.rstrip().endswith((".", ":", "!", "?"))
    return " ".join(out)


def find_sections(text):
    matches = []
    for stype, phrase, _label in SECTION_KEYWORDS:
        for m in re.finditer(r'\b(?:' + phrase + r')\b[^:]{0,60}:', text, re.IGNORECASE):
            matches.append((m.start(), m.end(), stype))
    matches.sort()
    filtered = []
    last_end = -1
    for start, end, stype in matches:
        if start < last_end:
            continue
        filtered.append((start, end, stype))
        last_end = end
    intro = text[:filtered[0][0]].strip() if filtered else text.strip()
    segments = []
    for i, (start, end, stype) in enumerate(filtered):
        c_end = filtered[i + 1][0] if i + 1 < len(filtered) else len(text)
        content = text[end:c_end].strip()
        if content:
            segments.append((stype, content))
    return intro, segments


SECTION_LABELS = {k: v for k, _p, v in SECTION_KEYWORDS}


def parse_specs(text):
    pattern = re.compile(r'([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑ]*(?:\s[a-záéíóúñ][\wáéíóúñ°/\.\-]*){0,4}):\s')
    matches = list(pattern.finditer(text))
    pairs = []
    for i, m in enumerate(matches):
        label = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        value = text[start:end].strip().rstrip(".")
        if label and value and len(label) <= 45:
            pairs.append((label, value))
    # Corrige el caso "Marca: BRITZEN Modelo:" cuando la marca queda pegada
    # a la etiqueta siguiente (valores de una sola palabra tipo BRITZEN/AYHSRL).
    KNOWN_BRANDS = ("Britzen", "Ayhsrl")
    fixed = []
    for label, value in pairs:
        for brand in KNOWN_BRANDS:
            if label.startswith(brand + " "):
                fixed.append(("Marca", brand.upper()))
                label = label[len(brand) + 1:].strip()
                break
        fixed.append((label, value))
    return fixed


def split_intro_paragraphs(intro):
    sentences = re.split(r'(?<=[.!?])\s+', intro)
    paragraphs = []
    current = ""
    for s in sentences:
        if current and len(current) + len(s) > 260:
            paragraphs.append(current.strip())
            current = s
        else:
            current = (current + " " + s).strip()
    if current:
        paragraphs.append(current.strip())
    return paragraphs[:4]


def make_short(paragraphs):
    text = " ".join(paragraphs)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    out = ""
    for s in sentences:
        if out and len(out) + len(s) > 280:
            break
        out = (out + " " + s).strip()
    return out or text[:260]


def parse_positions(content):
    matches = re.findall(r'Posici[oó]n\s*#?\s*\d+\s*:\s*(.*?)(?=(?:Posici[oó]n\s*#?\s*\d+\s*:)|$)', content, re.IGNORECASE | re.DOTALL)
    items = [m.strip().rstrip(".") for m in matches if m.strip()]
    return items


def parse_description(raw_text, sku):
    text = fix_allcaps(raw_text)
    intro, segments = find_sections(text)
    paragraphs = split_intro_paragraphs(intro)
    short = make_short(paragraphs)

    blocks = []
    important = None
    for stype, content in segments:
        if stype == "importante":
            important = content
            continue
        if stype == "posiciones":
            items = parse_positions(content)
            if len(items) >= 2:
                blocks.append({"type": "numbered", "heading": SECTION_LABELS[stype], "items": items})
            else:
                blocks.append({"type": "paragraph", "heading": SECTION_LABELS[stype], "text": content})
            continue
        if stype in ("caracteristicas", "contenido_kit", "accesorios", "presentacion", "ventajas", "puntos_clave", "recomendaciones", "usos"):
            specs = parse_specs(content)
            # Salvaguarda: si el "parseo" da pocos pares o valores sospechosamente
            # largos (texto corrido sin etiquetas reales), se muestra como párrafo.
            good = [(l, v) for l, v in specs if len(v) <= 200 and len(l) <= 30]
            if len(good) >= 3 and len(good) == len(specs):
                blocks.append({"type": "specs", "heading": SECTION_LABELS[stype], "rows": good})
            else:
                blocks.append({"type": "paragraph", "heading": SECTION_LABELS[stype], "text": content})
            continue
        blocks.append({"type": "paragraph", "heading": SECTION_LABELS.get(stype, stype.title()), "text": content})

    if not paragraphs and not blocks and not important:
        return None

    return {
        "short": short,
        "paragraphs": paragraphs,
        "blocks": blocks,
        "important": important,
    }


MASTER_RECORDS = load_master_products(CONTENT_DIR)

PRODUCTS = []
LONG_DESCRIPTIONS = {}
for rec in MASTER_RECORDS:
    sku = rec["sku"]
    title = rec["name_raw"].strip()

    long_desc = None
    if rec["desc_raw"]:
        long_desc = parse_description(rec["desc_raw"], sku)

    if long_desc:
        lead = long_desc["short"]
        desc = long_desc["short"]
        features = []
        LONG_DESCRIPTIONS[sku] = long_desc
    else:
        lead = title
        desc = title + "."
        features = []

    p = {
        "sku": sku,
        "title": title,
        "category": rec["category"],
        "lead": lead,
        "desc": desc,
        "features": features,
        "price": rec["price"],
        "mla": rec["mla"],
        "photos": rec.get("photos") or [],
    }
    PRODUCTS.append(p)

for p in PRODUCTS:
    p["slug"] = slugify(p["title"]) + "-" + p["sku"].lower().replace("-", "")
    p["ml_url"] = "https://articulo.mercadolibre.com.ar/{}".format(p["mla"]) if p["mla"] else None

CATEGORIES = []
seen = set()
for p in PRODUCTS:
    if p["category"] not in seen:
        seen.add(p["category"])
        CATEGORIES.append(p["category"])
# ---------------------------------------------------------------------------
# Partials
# ---------------------------------------------------------------------------

WHATSAPP_ICON = """<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M16.03 2.67C8.65 2.67 2.67 8.65 2.67 16.03c0 2.44.65 4.72 1.78 6.69L2.67 29.33l6.79-1.75a13.3 13.3 0 0 0 6.57 1.74h.01c7.38 0 13.36-5.98 13.36-13.36S23.42 2.67 16.03 2.67Zm0 24.4h-.01a11.1 11.1 0 0 1-5.66-1.55l-.4-.24-4.03 1.04 1.07-3.93-.26-.4a11.05 11.05 0 0 1-1.7-5.9c0-6.13 4.99-11.12 11.13-11.12 2.97 0 5.76 1.16 7.86 3.26a11.04 11.04 0 0 1 3.26 7.86c0 6.14-4.99 11.13-11.13 11.13Zm6.1-8.34c-.33-.17-1.98-.98-2.29-1.09-.31-.11-.53-.17-.76.17-.22.33-.87 1.09-1.07 1.31-.2.22-.39.25-.72.08-.33-.17-1.4-.52-2.67-1.66-.99-.88-1.65-1.97-1.85-2.3-.2-.33-.02-.5.15-.67.15-.15.33-.39.5-.58.17-.2.22-.33.33-.55.11-.22.06-.42-.03-.58-.08-.17-.76-1.84-1.05-2.51-.28-.66-.56-.57-.76-.58h-.65c-.22 0-.58.08-.89.42-.3.33-1.16 1.14-1.16 2.77 0 1.63 1.19 3.21 1.36 3.44.17.22 2.34 3.58 5.68 5.02.79.34 1.41.55 1.89.7.79.25 1.51.21 2.08.13.63-.1 1.98-.81 2.26-1.6.28-.78.28-1.46.2-1.6-.08-.14-.3-.22-.63-.39Z"/></svg>"""

def wa_float(context=""):
    msg = "Hola, quiero consultar por Britzen" + (" — " + context if context else "")
    return """  <a class="whatsapp-float" href="{link}" target="_blank" rel="noopener" aria-label="Contactar por WhatsApp">
    {icon}
  </a>""".format(link=wa_link(msg), icon=WHATSAPP_ICON)


SITE_URL = "https://britzen.com.ar"


GA_MEASUREMENT_ID = "G-B3HNSGE9L4"


def head(title, description, depth="", canonical_path="", og_image=""):
    canonical = "{}/{}".format(SITE_URL, canonical_path) if canonical_path else SITE_URL + "/"
    image = og_image or "{}/assets/img/mark-blue.png".format(SITE_URL)
    return """<!DOCTYPE html>
<html lang="es-AR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | BRITZEN</title>
<meta name="description" content="{description}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Britzen">
<meta property="og:title" content="{title} | BRITZEN">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{image}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{depth}assets/img/favicon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{depth}assets/css/styles.css">
<script async src="https://www.googletagmanager.com/gtag/js?id={ga_id}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{ga_id}');
</script>
</head>
<body>""".format(title=title, description=description, depth=depth, canonical=canonical, image=image, ga_id=GA_MEASUREMENT_ID)


def header(active, depth=""):
    def cur(name):
        return ' aria-current="page"' if active == name else ""
    return """<header class="site-header">
  <div class="wrap">
    <a class="brand" href="{d}index.html"><img src="{d}assets/img/logo-black.png" alt="Britzen"></a>
    <nav class="main-nav" id="main-nav">
      <a href="{d}catalogo.html"{cat}>Catálogo</a>
      <a href="{d}quienes-somos.html"{qs}>Quiénes somos</a>
      <a href="{d}contacto.html"{ct}>Contacto</a>
    </nav>
    <div style="display:flex; align-items:center; gap:14px;">
      <button class="search-toggle" aria-label="Buscar productos">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10.5 3a7.5 7.5 0 0 1 5.92 12.12l5.23 5.23-1.06 1.06-5.23-5.23A7.5 7.5 0 1 1 10.5 3Zm0 1.5a6 6 0 1 0 0 12 6 6 0 0 0 0-12Z"/></svg>
      </button>
      <a class="header-cta" href="{wa}" target="_blank" rel="noopener"><span class="long">Escribinos por</span> WhatsApp</a>
      <button class="nav-toggle" aria-label="Abrir menú" aria-expanded="false" aria-controls="main-nav">
        <span></span><span></span><span></span>
      </button>
    </div>
  </div>
</header>
<div class="search-overlay" id="search-overlay">
  <div class="search-box">
    <div class="search-input-row">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10.5 3a7.5 7.5 0 0 1 5.92 12.12l5.23 5.23-1.06 1.06-5.23-5.23A7.5 7.5 0 1 1 10.5 3Zm0 1.5a6 6 0 1 0 0 12 6 6 0 0 0 0-12Z"/></svg>
      <input type="text" id="search-input" placeholder="Buscar por código o nombre… (ej. 2002, torquímetro)" autocomplete="off">
      <button class="search-close" aria-label="Cerrar búsqueda">&times;</button>
    </div>
    <div class="search-results" id="search-results"></div>
  </div>
</div>""".format(d=depth, cat=cur("catalogo"), qs=cur("quienes-somos"), ct=cur("contacto"),
                     wa=wa_link("Hola, quiero consultar por Britzen"))


def footer(depth=""):
    return """<footer class="site-footer">
  <div class="wrap">
    <div class="footer-top">
      <div>
        <img src="{d}assets/img/logo-white.png" alt="Britzen">
        <p>Herramientas para taller mecánico y automotor. Importado y comercializado en Argentina por Accesorios y Herramientas SRL.</p>
      </div>
      <div class="footer-links">
        <div>
          <h4>Sitio</h4>
          <a href="{d}catalogo.html">Catálogo</a>
          <a href="{d}quienes-somos.html">Quiénes somos</a>
          <a href="{d}contacto.html">Contacto</a>
        </div>
        <div>
          <h4>Contacto</h4>
          <a href="{wa}" target="_blank" rel="noopener">WhatsApp</a>
          <a href="mailto:{email}">{email}</a>
        </div>
      </div>
      <div class="footer-qr">
        <h4>ARCA</h4>
        <a href="http://qr.afip.gob.ar/?qr=Akw3B4DxOsSoRx4DcL9-NA,," target="_F960AFIPInfo"><img src="http://www.afip.gob.ar/images/f960/DATAWEB.jpg" border="0" alt="Constatación de datos fiscales AFIP/ARCA" style="width:96px;height:auto;"></a>
      </div>
    </div>
    <div class="footer-bottom">
      <span>© 2026 Britzen Argentina. Importado por Accesorios y Herramientas SRL.</span>
      <span>britzen.com.ar</span>
    </div>
  </div>
</footer>
<script src="{d}assets/js/search-data.js"></script>
<script src="{d}assets/js/main.js"></script>""".format(d=depth, wa=wa_link("Hola, quiero consultar por Britzen"), email=EMAIL)


def page(title, description, active, body, depth="", canonical_path="", og_image=""):
    return head(title, description, depth, canonical_path, og_image) + "\n" + header(active, depth) + "\n" + body + "\n" + wa_float() + "\n" + footer(depth) + "\n</body>\n</html>\n"


def write(path, content):
    full = os.path.join(SITE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    print("✓", path)


# ---------------------------------------------------------------------------
# Card de producto (reutilizada en home, catálogo y relacionados)
# ---------------------------------------------------------------------------

def has_photo(p):
    return bool(p.get("photos"))


def product_media(p, depth="", detail=False):
    css_class = "detail-media" if detail else "product-media"
    photos = p.get("photos") or []
    if not photos:
        return """<div class="{cls}">
          <img src="{d}assets/img/mark-blue.png" alt="">
          <span class="photo-pending">Foto próximamente</span>
        </div>""".format(cls=css_class, d=depth)

    id_attr = ' id="gallery-main"' if detail else ""
    main_img = """<div class="{cls}">
          <img{id_attr} src="{src}" alt="{title}" style="width:100%;height:100%;object-fit:contain;">
        </div>""".format(cls=css_class, id_attr=id_attr, src=photos[0], title=p["title"])

    if detail and len(photos) > 1:
        thumbs = "\n          ".join(
            '<button class="gallery-thumb{active}" data-src="{src}"><img src="{src}" alt=""></button>'.format(
                src=src, active=" is-active" if i == 0 else ""
            )
            for i, src in enumerate(photos)
        )
        gallery = main_img + '\n        <div class="gallery-thumbs">\n          {thumbs}\n        </div>'.format(thumbs=thumbs)
        return '<div class="detail-gallery">\n        {gallery}\n      </div>'.format(gallery=gallery)

    return main_img

def product_card(p, depth=""):
    return """<a class="product-card" href="{d}producto/{slug}.html" data-category="{cat}">
        {media}
        <div class="product-info">
          <div class="product-cat">{cat}</div>
          <div class="product-name">{title}</div>
          <div class="product-sku">Cód. {sku}</div>
        </div>
      </a>""".format(d=depth, slug=p["slug"], cat=p["category"], title=p["title"], sku=p["sku"],
                     media=product_media(p, depth))


# ---------------------------------------------------------------------------
# HOME
# ---------------------------------------------------------------------------

def build_home():
    CATEGORY_HERO = {
        "Bomba Trasvase": "NEVIS-20", "Compresómetro": "1031", "Suspensión": "1233",
        "Frenos": "1037", "Prensa Válvula": "1001", "Extractor": "1147",
        "Torquímetro": "8512", "Juego de Llaves": "1002", "Sondas": "1905",
        "Fresador": "1364", "Refrigeración": "8971", "Vacuómetro": "1173",
        "Morsa": "NEVIS-03",
    }
    cat_tiles = ""
    for c in CATEGORIES:
        n = sum(1 for p in PRODUCTS if p["category"] == c)
        hero_sku = CATEGORY_HERO.get(c)
        hero_product = next((p for p in PRODUCTS if p["sku"] == hero_sku), None) if hero_sku else None
        if hero_product and has_photo(hero_product):
            style = ' style="background-image:url(\'{}\')"'.format(hero_product["photos"][0].lstrip("/"))
            icon = ""
        else:
            style = ""
            icon = '<img class="clip-icon" src="assets/img/mark-blue.png" alt="">'
        cat_tiles += """      <a class="category-tile" href="catalogo.html#{slug}"{style}>
        <div class="scrim"></div>
        <span class="count">{n} {label}</span>
        {icon}
        <span>{cat}</span>
      </a>\n""".format(slug=slugify(c), n=n, label="producto" if n == 1 else "productos", cat=c, style=style, icon=icon)

    featured_skus = ["1233", "8331", "1147", "1702"]
    featured_products = [p for sku in featured_skus for p in PRODUCTS if p["sku"] == sku]
    featured = "\n      ".join(product_card(p) for p in featured_products)

    review_cards = ""
    for r in REVIEWS:
        initial = r["author"][0]
        review_cards += """      <div class="review-card">
        <div class="stars">★★★★★</div>
        <p>"{text}"</p>
        <div class="review-author">
          <span class="review-avatar">{initial}</span>
          {author} · Google
        </div>
      </div>\n""".format(text=r["text"], initial=initial, author=r["author"])

    body = """<section class="hero">
  <div class="wrap">
    <div>
      <div class="hero-eyebrow">Herramientas para taller mecánico y automotor</div>
      <h1>El taller no espera. <br>Las herramientas de Britzen tampoco.</h1>
      <p class="lead">Extractores, prensas y compresores pensados para el uso diario de taller. Catálogo en crecimiento, consulta directa por WhatsApp.</p>
      <div class="hero-actions">
        <a class="btn btn-primary" href="catalogo.html">Ver catálogo</a>
        <a class="btn btn-outline" href="{wa}" target="_blank" rel="noopener">Hablar por WhatsApp</a>
      </div>
    </div>
    <div class="hero-graphic">
      <img class="bolt" src="assets/img/mark-blue.png" alt="">
    </div>
  </div>
</section>
<div class="diagonal-cut"></div>

<section class="section">
  <div class="wrap">
    <div class="section-head">
      <div>
        <h2>Categorías</h2>
        <p class="sub">Del extractor de rulemanes al kit de pestañado — organizado por el tipo de trabajo que resuelve.</p>
      </div>
      <a class="btn btn-dark" href="catalogo.html">Ver todo el catálogo</a>
    </div>
    <div class="category-grid">
{tiles}    </div>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="section-head">
      <div>
        <h2>Recién llegados</h2>
        <p class="sub">Una selección del catálogo. El resto de los productos se suma en las próximas semanas.</p>
      </div>
    </div>
    <div class="product-grid">
      {featured}
    </div>
  </div>
</section>

<section class="section bg-steel">
  <div class="wrap">
    <div class="section-head">
      <div>
        <h2>Lo que dicen de nosotros</h2>
        <p class="sub">Britzen la trae a Argentina Accesorios y Herramientas SRL — esto es lo que sus clientes cuentan en Google.</p>
      </div>
    </div>
    <div class="reviews-summary">
      <div class="reviews-score">{score}</div>
      <div>
        <div class="reviews-stars">★★★★★</div>
        <div class="reviews-meta">{count} opiniones en Google · <a href="{reviews_url}" target="_blank" rel="noopener">ver todas</a></div>
      </div>
    </div>
    <div class="reviews-grid">
{reviews}    </div>
  </div>
</section>""".format(wa=wa_link("Hola, quiero consultar por Britzen"), tiles=cat_tiles, featured=featured,
                     score=REVIEWS_SCORE, count=REVIEWS_COUNT, reviews_url=REVIEWS_URL, reviews=review_cards)

    write("index.html", page("Herramientas para taller mecánico y automotor", "Britzen — extractores, prensas y compresores para taller mecánico y automotor en Argentina. Catálogo y contacto directo por WhatsApp.", "inicio", body, canonical_path=""))


# ---------------------------------------------------------------------------
# CATÁLOGO
# ---------------------------------------------------------------------------

def build_catalogo():
    filter_btns = '<button class="filter-btn is-active" data-filter="todos" data-slug="todos">Todos</button>\n      '
    filter_btns += "\n      ".join(
        '<button class="filter-btn" data-filter="{cat}" data-slug="{slug}">{cat}</button>'.format(cat=c, slug=slugify(c)) for c in CATEGORIES
    )
    cards = "\n      ".join(product_card(p) for p in PRODUCTS)

    body = """<section class="section-tight">
  <div class="wrap">
    <div class="section-head">
      <div>
        <h2>Catálogo</h2>
        <p class="sub">{n} productos disponibles. Cada ficha tiene su botón directo de contacto por WhatsApp.</p>
      </div>
    </div>
    <div class="filters">
      {filters}
    </div>
    <p class="catalog-count">{n} productos</p>
    <div class="product-grid">
      {cards}
    </div>
  </div>
</section>""".format(n=len(PRODUCTS), filters=filter_btns, cards=cards)

    write("catalogo.html", page("Catálogo", "Catálogo completo de herramientas Britzen para taller mecánico y automotor.", "catalogo", body, canonical_path="catalogo"))


# ---------------------------------------------------------------------------
# QUIÉNES SOMOS
# ---------------------------------------------------------------------------

def build_quienes_somos():
    body = """<section class="page-hero">
  <div class="wrap">
    <h1>Quiénes somos</h1>
    <p class="sub">Britzen llega a Argentina para ofrecer herramientas de taller pensadas para el trabajo real: uso diario, resultados consistentes y un catálogo que no deja de crecer.</p>
  </div>
</section>

<section class="section">
  <div class="wrap story-grid">
    <div>
      <h2>Herramientas para el trabajo de taller</h2>
    </div>
    <div>
      <p>Britzen es una marca de herramientas para taller mecánico y automotor. <strong>Accesorios y Herramientas SRL es el importador oficial de Britzen en Argentina</strong>, encargado de traer la marca al país y ponerla a disposición de talleres y particulares. Nuestro catálogo se concentra en extractores, prensas y compresores: la herramienta específica que un taller necesita para resolver un trabajo puntual, sin vueltas.</p>
      <p>Elegimos empezar por un catálogo acotado y bien resuelto antes que uno enorme y disperso. Cada producto que sumamos pasa por una selección pensada para el uso real de taller — no para quedar bien en una foto.</p>
      <p>El contacto es directo: cada producto del catálogo tiene su botón de WhatsApp para consultar disponibilidad, precio o asesoramiento antes de comprar.</p>
    </div>
  </div>
</section>

<section class="section bg-steel">
  <div class="wrap">
    <div class="section-head">
      <div>
        <h2>Lo que nos define</h2>
      </div>
    </div>
    <div class="values-grid">
      <div class="value-card">
        <div class="num">01</div>
        <h3>Herramienta específica</h3>
        <p>Cada producto está pensado para un trabajo puntual de taller, no para ser una herramienta genérica más.</p>
      </div>
      <div class="value-card">
        <div class="num">02</div>
        <h3>Catálogo en crecimiento</h3>
        <p>Sumamos productos de forma constante a medida que identificamos las necesidades más frecuentes del taller argentino.</p>
      </div>
      <div class="value-card">
        <div class="num">03</div>
        <h3>Contacto directo</h3>
        <p>Sin formularios ni intermediarios: WhatsApp directo para consultar cualquier producto del catálogo.</p>
      </div>
    </div>
  </div>
</section>"""

    write("quienes-somos.html", page("Quiénes somos", "Britzen es una marca de herramientas para taller mecánico y automotor que estamos trayendo a Argentina.", "quienes-somos", body, canonical_path="quienes-somos"))


# ---------------------------------------------------------------------------
# CONTACTO
# ---------------------------------------------------------------------------

def build_contacto():
    body = """<section class="section-tight">
  <div class="wrap">
    <div class="contact-grid">
      <div class="contact-panel">
        <h2>Contacto</h2>
        <p>¿Consulta por un producto, precio o disponibilidad? Escribinos directo por WhatsApp — es la vía más rápida para recibir atención.</p>
        <div class="contact-list">
          <div>
            <div class="label">WhatsApp</div>
            <div class="value">+54 9 11 4928-7469</div>
          </div>
          <div>
            <div class="label">Email</div>
            <div class="value">{email}</div>
          </div>
          <div>
            <div class="label">Horario de atención</div>
            <div class="value">{hours}</div>
          </div>
          <div>
            <div class="label">Ubicación</div>
            <div class="value">{address}<br><a href="{maps_link}" target="_blank" rel="noopener" style="color:var(--blue);">Abrir en Google Maps ↗</a></div>
          </div>
        </div>
        <a class="btn btn-primary" href="{wa}" target="_blank" rel="noopener">Escribir por WhatsApp</a>
      </div>
      <div class="map-panel" style="padding:0;">
        <iframe src="{maps_embed}" width="100%" height="100%" style="border:0; min-height:380px;" allowfullscreen="" loading="lazy" referrerpolicy="no-referrer-when-downgrade" title="Ubicación de Britzen / Accesorios y Herramientas SRL"></iframe>
      </div>
    </div>
  </div>
</section>""".format(wa=wa_link("Hola, quiero hacer una consulta"), email=EMAIL, address=ADDRESS,
                     hours=HOURS, maps_embed=MAPS_EMBED_SRC, maps_link=MAPS_LINK)

    write("contacto.html", page("Contacto y ubicación", "Contactá a Britzen por WhatsApp o email para consultas sobre productos, precios y disponibilidad.", "contacto", body, canonical_path="contacto"))


# ---------------------------------------------------------------------------
# FICHAS DE PRODUCTO
# ---------------------------------------------------------------------------

def render_long_description(ld):
    parts = []
    parts.append("\n    ".join(
        '<p style="margin-bottom:16px; color:var(--gray-600);">{}</p>'.format(p) for p in ld["paragraphs"]
    ))

    for block in ld["blocks"]:
        heading = '<h3 class="detail-section-title">{}</h3>'.format(block["heading"]) if block.get("heading") else ""
        if block["type"] == "specs":
            rows = "\n      ".join("<tr><td>{}</td><td>{}</td></tr>".format(k, v) for k, v in block["rows"])
            parts.append('{heading}\n    <table class="spec-table">\n      {rows}\n    </table>'.format(heading=heading, rows=rows))
        elif block["type"] == "numbered":
            items = "\n      ".join(
                '<li><span class="pos-num">{}</span><span>{}</span></li>'.format(i + 1, txt)
                for i, txt in enumerate(block["items"])
            )
            parts.append('{heading}\n    <ul class="positions-list">\n      {items}\n    </ul>'.format(heading=heading, items=items))
        else:  # paragraph
            parts.append('{heading}\n    <p style="margin-bottom:24px; color:var(--gray-600);">{text}</p>'.format(heading=heading, text=block["text"]))

    if ld.get("important"):
        parts.append('<div class="callout-warning"><strong>Importante:</strong> {}</div>'.format(ld["important"]))

    return "\n    ".join(parts)


def build_products():
    for p in PRODUCTS:
        related = [r for r in PRODUCTS if r["category"] == p["category"] and r["sku"] != p["sku"]][:4]
        if len(related) < 4:
            others = [r for r in PRODUCTS if r["sku"] != p["sku"] and r not in related]
            related += others[: 4 - len(related)]

        if p["sku"] in LONG_DESCRIPTIONS:
            ld = LONG_DESCRIPTIONS[p["sku"]]
            short_desc_html = '<p style="margin-bottom:24px; color:var(--gray-600);">{}</p>'.format(ld["short"])
            full_desc_section = """<section class="section">
  <div class="wrap" style="max-width:860px;">
    <h2 style="font-size:24px; margin-bottom:24px;">Descripción completa</h2>
    {content}
  </div>
</section>""".format(content=render_long_description(ld))
        else:
            features_li = "\n            ".join("<li>{}</li>".format(f) for f in p["features"])
            features_block = """<ul style="margin:0 0 28px; padding-left:20px; color:var(--gray-600);">
      {features}
    </ul>""".format(features=features_li) if p["features"] else ""
            short_desc_html = '<p style="margin-bottom:24px; color:var(--gray-600);">{}</p>\n    {}'.format(p["desc"], features_block)
            full_desc_section = ""

        related_cards = "\n      ".join(product_card(r, depth="../") for r in related)

        if p["price"]:
            price_html = '<span class="price-amount">${:,.0f}</span><span class="tag">Mejor precio por WhatsApp</span>'.format(p["price"]).replace(",", ".")
        else:
            price_html = '<span class="price-amount price-soon">Precio próximamente</span><span class="tag">Consultá disponibilidad</span>'

        ml_block = '<a class="ml-secondary" href="{ml}" target="_blank" rel="noopener">Ver publicación en Mercado Libre ↗</a>'.format(ml=p["ml_url"]) if p["ml_url"] else ""

        body = """<div class="wrap breadcrumb">
  <a href="../catalogo.html">Catálogo</a> / <span>{cat}</span> / <span>{title}</span>
</div>

<section class="wrap product-detail">
  {media}
  <div class="detail-info">
    <div class="product-cat">{cat}</div>
    <h1>{title}</h1>

    <div class="detail-meta">
      <div><span>Código</span><strong>{sku}</strong></div>
      <div><span>Categoría</span><strong>{cat}</strong></div>
    </div>

    {short_desc_html}

    <div class="price-line">{price_html}</div>

    <div class="detail-actions">
      <a class="btn btn-primary" href="{wa}" target="_blank" rel="noopener">
        <svg class="wa-icon" viewBox="0 0 32 32">{wa_path}</svg>
        Consultar por WhatsApp
      </a>
      {ml_block}
    </div>
  </div>
</section>

{full_desc_section}

<section class="section bg-steel">
  <div class="wrap">
    <h2 class="related-heading">También te puede interesar</h2>
    <div class="product-grid">
      {related}
    </div>
  </div>
</section>""".format(
            cat=p["category"], title=p["title"], lead=p["lead"], sku=p["sku"], short_desc_html=short_desc_html,
            media=product_media(p, depth="../", detail=True), full_desc_section=full_desc_section,
            wa=wa_link("Hola, quiero consultar por: " + p["title"] + " (Cód. " + p["sku"] + ")"),
            wa_path=WHATSAPP_ICON.split(">", 1)[1].rsplit("</svg", 1)[0],
            ml_block=ml_block, related=related_cards, price_html=price_html,
        )

        product_og_image = "{}{}".format(SITE_URL, p["photos"][0]) if has_photo(p) else ""
        full_page = page(p["title"], p["desc"][:155], "catalogo", body, depth="../", canonical_path="producto/" + p["slug"], og_image=product_og_image)
        write("producto/{}.html".format(p["slug"]), full_page)


def build_search_data():
    import json
    data = [
        {"sku": p["sku"], "title": p["title"], "category": p["category"], "slug": p["slug"]}
        for p in PRODUCTS
    ]
    js = "window.SEARCH_DATA = " + json.dumps(data, ensure_ascii=False) + ";\n"
    write("assets/js/search-data.js", js)


def build_sitemap():
    urls = ["", "catalogo", "quienes-somos", "contacto"] + ["producto/" + p["slug"] for p in PRODUCTS]
    items = "\n".join(
        "  <url><loc>{}/{}</loc></url>".format(SITE_URL, u) if u else "  <url><loc>{}/</loc></url>".format(SITE_URL)
        for u in urls
    )
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{items}
</urlset>
""".format(items=items)
    write("sitemap.xml", xml)

    robots = """User-agent: *
Allow: /

Sitemap: {}/sitemap.xml
""".format(SITE_URL)
    write("robots.txt", robots)


os.makedirs(SITE, exist_ok=True)
if os.path.exists(os.path.join(SITE, "assets")):
    shutil.rmtree(os.path.join(SITE, "assets"))
shutil.copytree(os.path.join(ROOT, "assets"), os.path.join(SITE, "assets"))

admin_src = os.path.join(ROOT, "admin")
if os.path.exists(admin_src):
    admin_dst = os.path.join(SITE, "admin")
    if os.path.exists(admin_dst):
        shutil.rmtree(admin_dst)
    shutil.copytree(admin_src, admin_dst)

build_home()
build_catalogo()
build_quienes_somos()
build_contacto()
build_products()
build_sitemap()
build_search_data()

print("\nListo:", len(PRODUCTS), "fichas de producto +", 4, "páginas principales")
