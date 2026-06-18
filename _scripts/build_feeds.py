#!/usr/bin/env python3
"""Génère sitemap.xml, carnet/index.xml (RSS 2.0) et feed.json pour harnais.be.

Parse le HTML statique du repo (index.html dans chaque dossier) pour en déduire
URL, titre, description et date de dernière modification. Aucune dépendance
externe — Python stdlib uniquement. À relancer après chaque publication.

Usage:  python3 _scripts/build_feeds.py
"""
import os
import re
import glob
import json
from html import unescape
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime

BASE = "https://harnais.be"
HERE = os.path.dirname(os.path.abspath(__file__))
SITE_ROOT = os.path.dirname(HERE)  # parent du dossier _scripts
TZ = timezone(timedelta(hours=2))  # Bruxelles, heure d'été (CEST)
CHAPEAUX_PATH = os.path.join(SITE_ROOT, "_chapeaux.json")


def load_chapeaux():
    """Read _chapeaux.json {date_iso: chapeau}. Returns {} if absent/invalid.

    The chapeau is a 50-100 words self-contained lead, produced by the
    editor-du-carnet in the post-artifact zone and persisted by the Aegis
    in_review hook. John overrides by editing this file directly.
    """
    if not os.path.isfile(CHAPEAUX_PATH):
        return {}
    try:
        with open(CHAPEAUX_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v).strip() for k, v in data.items() if v}


def truncate_chapeau(chapeau, max_chars):
    """Smart-truncate to max_chars on a word boundary (… ellipsis if cut)."""
    if not chapeau:
        return ""
    chapeau = chapeau.strip()
    if len(chapeau) <= max_chars:
        return chapeau
    cut = chapeau[: max_chars - 1].rstrip()
    sp = cut.rfind(" ")
    if sp > max_chars * 0.6:
        cut = cut[:sp].rstrip(",.;:—–-")
    return cut + "…"


def date_iso_from_url(url_path):
    """Extract YYYY-MM-DD from a carnet URL path. Returns None if not a billet."""
    m = re.match(r"/carnet/(\d{4}-\d{2}-\d{2})/", url_path)
    return m.group(1) if m else None

# Dossiers non déployés / non pertinents pour l'index public.
EXCLUDE_DIRS = {
    ".git", ".wrangler", "render", "toolbars", "templates", "_templates",
    "_drafts", "_fiches", "_scripts", "assets",
}


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def title_of(txt):
    m = re.search(r"<title>(.*?)</title>", txt, re.S | re.I)
    if not m:
        return None
    t = unescape(m.group(1))
    for sep in (" — ", " · ", " | ", " - "):
        if sep in t:
            return t.split(sep)[0].strip()
    return t.strip()


def desc_of(txt):
    m = re.search(r'<meta\s+name="description"\s+content="(.*?)"', txt, re.S | re.I)
    return unescape(m.group(1).strip()) if m else ""


def first_paragraph(txt):
    """Premier paragraphe de contenu substantiel (exclut le 'Bruxelles, DATE')."""
    body = txt.split("</head>", 1)[-1] if "</head>" in txt else txt
    for m in re.finditer(r"<p[^>]*>(.*?)</p>", body, re.S | re.I):
        clean = re.sub(r"<[^>]+>", "", m.group(1))
        clean = unescape(re.sub(r"\s+", " ", clean)).strip()
        if len(clean) > 60 and not clean.lower().startswith("bruxelles,"):
            return clean
    return ""


def iso_lastmod(path):
    t = os.path.getmtime(path)
    dt = datetime.fromtimestamp(t, TZ)
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + dt.strftime("%z")[:3] + ":" + dt.strftime("%z")[3:]


def rfc822(path):
    t = os.path.getmtime(path)
    return format_datetime(datetime.fromtimestamp(t, TZ))


def collect_pages():
    """Retourne la liste des (url_path, full_path) pour tous les index.html publics."""
    pages = []
    for dirpath, dirnames, filenames in os.walk(SITE_ROOT):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        if "index.html" not in filenames:
            continue
        full = os.path.join(dirpath, "index.html")
        rel = os.path.relpath(dirpath, SITE_ROOT)
        url_path = "/" if rel == "." else "/" + rel.replace(os.sep, "/") + "/"
        pages.append((url_path, full))
    pages.sort()
    return pages


def build_sitemap(pages):
    urls = []
    for url_path, full in pages:
        loc = BASE + url_path
        lastmod = iso_lastmod(full)
        # priorité : index > sections > billets
        if url_path == "/":
            prio = "1.0"
        elif url_path in ("/carnet/", "/essais/"):
            prio = "0.9"
        elif url_path.startswith("/carnet/2026"):
            prio = "0.7"
        else:
            prio = "0.6"
        urls.append(
            f"  <url>\n"
            f"    <loc>{loc}</loc>\n"
            f"    <lastmod>{lastmod}</lastmod>\n"
            f"    <changefreq>{"daily" if url_path == "/carnet/" or url_path.startswith("/carnet/2026") else "monthly"}</changefreq>\n"
            f"    <priority>{prio}</priority>\n"
            f"  </url>"
        )
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += "\n".join(urls) + "\n"
    xml += "</urlset>\n"
    return xml


def build_rss(pages):
    carnet = [(u, f) for (u, f) in pages if re.match(r"/carnet/2026-\d{2}-\d{2}/", u)]
    carnet.sort(key=lambda x: x[0], reverse=True)  # plus récent d'abord

    chapeaux = load_chapeaux()
    items = []
    for url_path, full in carnet:
        txt = read(full)
        title = title_of(txt) or url_path.strip("/").split("/")[-1]
        date_iso = date_iso_from_url(url_path)
        # Chapeau-first (2026-06-18): self-contained lead for LLM/snippet
        # extraction. Falls back to first_paragraph for old billets.
        chapeau = chapeaux.get(date_iso) if date_iso else None
        if chapeau:
            desc = truncate_chapeau(chapeau, 280)
        else:
            desc = first_paragraph(txt) or desc_of(txt) or "Chronique de veille IA sourcée."
            if len(desc) > 280:
                desc = desc[:277].rstrip() + "…"
        link = BASE + url_path
        items.append(
            f"    <item>\n"
            f"      <title>{escape_xml(title)}</title>\n"
            f"      <link>{link}</link>\n"
            f"      <guid isPermaLink=\"true\">{link}</guid>\n"
            f"      <description>{escape_xml(desc)}</description>\n"
            f"      <pubDate>{rfc822(full)}</pubDate>\n"
            f"    </item>"
        )
    now = format_datetime(datetime.now(TZ))
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
    xml += '  <channel>\n'
    xml += f"    <title>Le Carnet — Département des Harnais</title>\n"
    xml += f"    <link>{BASE}/carnet/</link>\n"
    xml += f"    <description>Chronique de veille IA quotidienne sourcée — Bruxelles.</description>\n"
    xml += f"    <language>fr-be</language>\n"
    xml += f"    <copyright>© John Linotte — traces CC-BY 4.0</copyright>\n"
    xml += f"    <lastBuildDate>{now}</lastBuildDate>\n"
    xml += f'    <atom:link href="{BASE}/carnet/index.xml" rel="self" type="application/rss+xml" />\n'
    xml += "\n".join(items) + "\n"
    xml += "  </channel>\n"
    xml += "</rss>\n"
    return xml


def build_json_feed(pages):
    carnet = [(u, f) for (u, f) in pages if re.match(r"/carnet/2026-\d{2}-\d{2}/", u)]
    carnet.sort(key=lambda x: x[0], reverse=True)
    import json
    chapeaux = load_chapeaux()
    items = []
    for url_path, full in carnet:
        txt = read(full)
        title = title_of(txt) or url_path.strip("/").split("/")[-1]
        billet_date = date_iso_from_url(url_path)
        # Chapeau-first: JSON Feed carries the FULL chapeau (no truncation —
        # 50-100 words is well within JSON Feed's loose summary convention).
        chapeau = chapeaux.get(billet_date) if billet_date else None
        if chapeau:
            desc = chapeau
        else:
            desc = first_paragraph(txt) or desc_of(txt) or ""
            if len(desc) > 280:
                desc = desc[:277].rstrip() + "…"
        date_iso = datetime.fromtimestamp(os.path.getmtime(full), TZ).strftime("%Y-%m-%dT%H:%M:%S%z")
        date_iso = date_iso[:-2] + ":" + date_iso[-2:]
        items.append({
            "id": BASE + url_path,
            "url": BASE + url_path,
            "title": title,
            "content_text": desc,
            "summary": desc,
            "date_published": date_iso,
        })
    feed = {
        "version": "https://jsonfeed.org/version/1.1",
        "title": "Le Carnet — Département des Harnais",
        "home_page_url": BASE + "/carnet/",
        "feed_url": BASE + "/carnet/feed.json",
        "description": "Chronique de veille IA quotidienne sourcée — Bruxelles.",
        "language": "fr-BE",
        "authors": [{"name": "John Linotte", "url": BASE + "/a-propos/"}],
        "items": items,
    }
    return json.dumps(feed, ensure_ascii=False, indent=2)


def escape_xml(s):
    return (s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


CARNET_RSS = '<link rel="alternate" type="application/rss+xml" title="Le Carnet — Département des Harnais" href="/carnet/index.xml">'
CARNET_JSON = '<link rel="alternate" type="application/json" title="Le Carnet — JSON Feed" href="/carnet/feed.json">'
ESSAIS_RSS = '<link rel="alternate" type="application/rss+xml" title="Les Essais — Département des Harnais" href="/essais/index.xml">'
ESSAIS_JSON = '<link rel="alternate" type="application/json" title="Les Essais — JSON Feed" href="/essais/feed.json">'


def inject_feed_links(pages):
    """Insère les balises de découverte RSS + JSON Feed avant </head> (idempotent).

    Quatre balises au total : flux Carnet + flux Essais (RSS et JSON chacun).
    S'applique à tous les index.html publics + 404.html. N'écrit le fichier que
    si une modification est réellement nécessaire.
    """
    targets = [full for (_, full) in pages]
    err404 = os.path.join(SITE_ROOT, "404.html")
    if os.path.exists(err404):
        targets.append(err404)

    touched = 0
    for full in targets:
        txt = read(full)
        if not txt or "</head>" not in txt:
            continue
        to_add = []
        if "/carnet/index.xml" not in txt:
            to_add.append("  " + CARNET_RSS + "\n  " + CARNET_JSON + "\n")
        if "/essais/index.xml" not in txt:
            to_add.append("  " + ESSAIS_RSS + "\n  " + ESSAIS_JSON + "\n")
        if not to_add:
            continue
        block = "".join(to_add)
        new_txt = txt.replace("</head>", block + "</head>", 1)
        try:
            with open(full, "w", encoding="utf-8") as f:
                f.write(new_txt)
            touched += 1
        except OSError as e:
            print(f"  ! écriture impossible {full}: {e}")
    return touched


def build_essais_rss(pages):
    """RSS 2.0 pour les essais publiés (essais/tN/). Description = meta description."""
    essais = [(u, f) for (u, f) in pages if re.match(r"/essais/t\d+/", u)]
    essais.sort(key=lambda x: x[0])  # t0, t1, ... (ordre croissant = essai le + récent en bas par convention ; RSS veut récent d'abord → on inverse)
    essais.reverse()

    items = []
    for url_path, full in essais:
        txt = read(full)
        title = title_of(txt) or url_path.strip("/").split("/")[-1]
        desc = desc_of(txt) or first_paragraph(txt) or "Essai du Département des Harnais."
        if len(desc) > 300:
            desc = desc[:297].rstrip() + "…"
        link = BASE + url_path
        items.append(
            f"    <item>\n"
            f"      <title>{escape_xml(title)}</title>\n"
            f"      <link>{link}</link>\n"
            f"      <guid isPermaLink=\"true\">{link}</guid>\n"
            f"      <description>{escape_xml(desc)}</description>\n"
            f"      <pubDate>{rfc822(full)}</pubDate>\n"
            f"    </item>"
        )
    now = format_datetime(datetime.now(TZ))
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
    xml += '  <channel>\n'
    xml += "    <title>Les Essais — Département des Harnais</title>\n"
    xml += f"    <link>{BASE}/essais/</link>\n"
    xml += "    <description>Essais long-form numérotés (T0…Tn) — une position défendue sur ce qu'un harness doit faire.</description>\n"
    xml += "    <language>fr-be</language>\n"
    xml += "    <copyright>© John Linotte — traces CC-BY 4.0</copyright>\n"
    xml += f"    <lastBuildDate>{now}</lastBuildDate>\n"
    xml += f'    <atom:link href="{BASE}/essais/index.xml" rel="self" type="application/rss+xml" />\n'
    xml += "\n".join(items) + "\n"
    xml += "  </channel>\n"
    xml += "</rss>\n"
    return xml


def build_essais_json(pages):
    import json
    essais = [(u, f) for (u, f) in pages if re.match(r"/essais/t\d+/", u)]
    essais.sort(key=lambda x: x[0])
    essais.reverse()
    items = []
    for url_path, full in essais:
        txt = read(full)
        title = title_of(txt) or url_path.strip("/").split("/")[-1]
        desc = desc_of(txt) or first_paragraph(txt) or ""
        if len(desc) > 300:
            desc = desc[:297].rstrip() + "…"
        date_iso = datetime.fromtimestamp(os.path.getmtime(full), TZ).strftime("%Y-%m-%dT%H:%M:%S%z")
        date_iso = date_iso[:-2] + ":" + date_iso[-2:]
        items.append({
            "id": BASE + url_path,
            "url": BASE + url_path,
            "title": title,
            "content_text": desc,
            "summary": desc,
            "date_published": date_iso,
        })
    feed = {
        "version": "https://jsonfeed.org/version/1.1",
        "title": "Les Essais — Département des Harnais",
        "home_page_url": BASE + "/essais/",
        "feed_url": BASE + "/essais/feed.json",
        "description": "Essais long-form numérotés (T0…Tn) — une position défendue sur ce qu'un harness doit faire.",
        "language": "fr-BE",
        "authors": [{"name": "John Linotte", "url": BASE + "/a-propos/"}],
        "items": items,
    }
    return json.dumps(feed, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Canonical + JSON-LD (schema.org)
# ---------------------------------------------------------------------------

LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"

ORG = {
    "@type": "Organization",
    "name": "Département des Harnais",
    "alternateName": "DDH",
    "url": BASE + "/",
    "description": "Atelier d'auteur sur l'IA : harness d'agents et agentivité, deterministic-first. Bruxelles, mmxxvi.",
    "foundingDate": "2026",
    "founder": {"@type": "Person", "name": "John Linotte", "url": BASE + "/a-propos/"},
    "email": "mailto:contact@harnais.be",
    "logo": BASE + "/assets/forum.jpg",
}

PERSON = {
    "@type": "Person",
    "name": "John Linotte",
    "url": BASE + "/a-propos/",
    "jobTitle": "Opérateur — atelier d'auteur",
    "address": {"@type": "PostalAddress", "addressLocality": "Bruxelles", "addressCountry": "BE"},
    "knowsAbout": [
        "harness d'agents IA", "agentivité", "orchestration déterministe",
        "deterministic-first", "trace certifiée",
    ],
    "worksFor": {"@type": "Organization", "name": "Département des Harnais", "url": BASE + "/"},
}


def canonical_url(url_path):
    return BASE + url_path


def breadcrumb(url_path, full):
    """BreadcrumbList déduit du chemin. None sur la home."""
    if url_path == "/":
        return None
    title = title_of(read(full))
    items = [{"@type": "ListItem", "position": 1, "name": "Index", "item": BASE + "/"}]
    if url_path.startswith("/carnet/"):
        items.append({"@type": "ListItem", "position": 2, "name": "Le Carnet", "item": BASE + "/carnet/"})
        if url_path != "/carnet/":
            items.append({"@type": "ListItem", "position": 3, "name": title or "Billet", "item": BASE + url_path})
    elif url_path.startswith("/essais/"):
        items.append({"@type": "ListItem", "position": 2, "name": "Les Essais", "item": BASE + "/essais/"})
        if url_path != "/essais/":
            items.append({"@type": "ListItem", "position": 3, "name": title or "Essai", "item": BASE + url_path})
    else:
        items.append({"@type": "ListItem", "position": 2, "name": title or url_path.strip("/"), "item": BASE + url_path})
    return {"@type": "BreadcrumbList", "itemListElement": items}


def build_jsonld_blocks(url_path, full):
    """Liste des dicts JSON-LD à injecter sur la page."""
    txt = read(full)
    title = title_of(txt) or "Département des Harnais"
    desc = desc_of(txt)
    # Pour les contenus (billet carnet, essai), on préfère le 1er paragraphe
    # substantiel à la meta description (souvent pauvre sur le carnet).
    if re.match(r"/carnet/2026-\d{2}-\d{2}/", url_path) or re.match(r"/essais/t\d+/", url_path):
        para = first_paragraph(txt)
        if para:
            desc = para
    # Chapeau-first (2026-06-18): override with the self-contained lead when
    # available for this date. JSON-LD description ~250 chars target.
    billet_date = date_iso_from_url(url_path)
    if billet_date:
        chapeau = load_chapeaux().get(billet_date)
        if chapeau:
            desc = truncate_chapeau(chapeau, 250)
    blocks = []

    # 1. Organization sur toutes les pages (identité globale)
    blocks.append({"@context": "https://schema.org", **ORG})

    # 2. Breadcrumb (sauf home)
    bc = breadcrumb(url_path, full)
    if bc:
        blocks.append({"@context": "https://schema.org", **bc})

    # 3. Type-spécifique
    if url_path == "/":
        blocks.append({
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": "Département des Harnais",
            "url": BASE + "/",
            "inLanguage": "fr-BE",
            "publisher": {"@type": "Organization", "name": "Département des Harnais", "url": BASE + "/"},
        })
    elif url_path == "/a-propos/":
        blocks.append({"@context": "https://schema.org", **PERSON})
    elif re.match(r"/carnet/2026-\d{2}-\d{2}/", url_path):
        date_pub = url_path.strip("/").split("/")[-1]  # 2026-06-18
        date_mod = datetime.fromtimestamp(os.path.getmtime(full), TZ).strftime("%Y-%m-%d")
        blocks.append({
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": title,
            "description": desc or "Chronique de veille IA sourcée.",
            "datePublished": date_pub,
            "dateModified": date_mod,
            "inLanguage": "fr-BE",
            "author": {"@type": "Person", "name": "John Linotte", "url": BASE + "/a-propos/"},
            "publisher": {"@type": "Organization", "name": "Département des Harnais", "url": BASE + "/"},
            "mainEntityOfPage": {"@type": "WebPage", "@id": BASE + url_path},
            "license": LICENSE_URL,
        })
    elif re.match(r"/essais/t\d+/", url_path):
        date_mod = datetime.fromtimestamp(os.path.getmtime(full), TZ).strftime("%Y-%m-%d")
        blocks.append({
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": title,
            "description": desc or "Essai du Département des Harnais.",
            "datePublished": date_mod,
            "dateModified": date_mod,
            "inLanguage": "fr-BE",
            "author": {"@type": "Person", "name": "John Linotte", "url": BASE + "/a-propos/"},
            "publisher": {"@type": "Organization", "name": "Département des Harnais", "url": BASE + "/"},
            "mainEntityOfPage": {"@type": "WebPage", "@id": BASE + url_path},
            "license": LICENSE_URL,
        })
    return blocks


def inject_canonical(pages):
    """Ajoute <link rel=canonical> manquant (déduit du chemin). Idempotent."""
    touched = 0
    for url_path, full in pages:
        txt = read(full)
        if not txt or "</head>" not in txt:
            continue
        if 'rel="canonical"' in txt or "rel='canonical'" in txt:
            continue
        link = f'  <link rel="canonical" href="{canonical_url(url_path)}">\n'
        new_txt = txt.replace("</head>", link + "</head>", 1)
        try:
            with open(full, "w", encoding="utf-8") as f:
                f.write(new_txt)
            touched += 1
        except OSError as e:
            print(f"  ! canonical écriture impossible {full}: {e}")
    return touched


JSONLD_START = "<!-- ddh:jsonld-start -->"
JSONLD_END = "<!-- ddh:jsonld-end -->"


def inject_jsonld(pages):
    """Insère/régénère les blocs JSON-LD avant </head>.

    Utilise des marqueurs commentaires pour pouvoir mettre à jour le JSON-LD à
    chaque exécution (utile quand on affine les données). La 1re fois, retire
    aussi d'éventuels blocs ld+json non marqués injectés par une version
    précédente du script.
    """
    touched = 0
    marked_re = re.compile(re.escape(JSONLD_START) + r".*?" + re.escape(JSONLD_END) + r"\n?", re.S)
    for url_path, full in pages:
        txt = read(full)
        if not txt or "</head>" not in txt:
            continue
        blocks = build_jsonld_blocks(url_path, full)
        if not blocks:
            continue
        scripts = []
        for b in blocks:
            s = json.dumps(b, ensure_ascii=False, indent=2)
            s = s.replace("</", "<\\/")  # empêche la fermeture prématurée du <script>
            scripts.append(f'  <script type="application/ld+json">\n{s}\n  </script>')
        new_block = JSONLD_START + "\n" + "\n".join(scripts) + "\n" + JSONLD_END + "\n"

        if JSONLD_START in txt and JSONLD_END in txt:
            new_txt = marked_re.sub(new_block, txt, count=1)
        elif "application/ld+json" in txt:
            # migration : retire les anciens blocs non marqués, puis insère le bloc marqué
            stripped = re.sub(r'\s*<script type="application/ld\+json">.*?</script>', "", txt, flags=re.S)
            new_txt = stripped.replace("</head>", new_block + "</head>", 1)
        else:
            new_txt = txt.replace("</head>", new_block + "</head>", 1)

        if new_txt == txt:
            continue
        try:
            with open(full, "w", encoding="utf-8") as f:
                f.write(new_txt)
            touched += 1
        except OSError as e:
            print(f"  ! json-ld écriture impossible {full}: {e}")
    return touched


# ---------------------------------------------------------------------------
# llms.txt + llms-full.txt (https://llmstxt.org)
# ---------------------------------------------------------------------------

def _strip_tags(s):
    return unescape(re.sub(r"<[^>]+>", "", s))


def extract_article(txt):
    """Retourne le HTML du contenu principal : <article> sinon <main> sinon body
    nettoyé des balises structurelles (nav/header/footer/aside/script/style)."""
    m = re.search(r"<article[^>]*>(.*?)</article>", txt, re.S | re.I)
    if m:
        return m.group(1)
    m = re.search(r"<main[^>]*>(.*?)</main>", txt, re.S | re.I)
    if m:
        return m.group(1)
    body = txt.split("</head>", 1)[-1] if "</head>" in txt else txt
    body = re.sub(r"<script.*?</script>", "", body, flags=re.S | re.I)
    body = re.sub(r"<style.*?</style>", "", body, flags=re.S | re.I)
    body = re.sub(r"<nav[^>]*>.*?</nav>", "", body, flags=re.S | re.I)
    body = re.sub(r"<footer[^>]*>.*?</footer>", "", body, flags=re.S | re.I)
    body = re.sub(r"<aside[^>]*>.*?</aside>", "", body, flags=re.S | re.I)
    return body


def html_to_markdown(html):
    """Conversion HTML -> Markdown volontairement simple et robuste.

    Préserve la prose (paragraphes, titres, listes, citations, emphases,
    liens, blocs de code). Suffisant pour que les LLM reçoivent un texte lisible.
    """
    # Retirer les éléments non textuels
    h = re.sub(r"<script.*?</script>", "", html, flags=re.S | re.I)
    h = re.sub(r"<style.*?</style>", "", h, flags=re.S | re.I)
    h = re.sub(r"<!--.*?-->", "", h, flags=re.S)

    # Liens : <a href="X">T</a> -> [T](X)
    h = re.sub(r'<a\s+[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r"[\2](\1)", h, flags=re.S | re.I)
    # Emphases
    h = re.sub(r"<(strong|b)>(.*?)</\1>", r"**\2**", h, flags=re.S | re.I)
    h = re.sub(r"<(em|i)>(.*?)</\1>", r"*\2*", h, flags=re.S | re.I)
    # Code inline
    h = re.sub(r"<code>(.*?)</code>", r"`\1`", h, flags=re.S | re.I)
    # Blocs de code <pre>
    h = re.sub(r"<pre[^>]*>(.*?)</pre>", lambda m: "\n```\n" + _strip_tags(m.group(1)) + "\n```\n", h, flags=re.S | re.I)
    # Citations
    h = re.sub(r"<blockquote[^>]*>(.*?)</blockquote>", lambda m: "\n" + "\n".join("> " + ln for ln in _strip_tags(m.group(1)).split("\n")) + "\n", h, flags=re.S | re.I)

    # Listes
    def list_repl(m):
        items = re.findall(r"<li[^>]*>(.*?)</li>", m.group(2), re.S | re.I)
        out = []
        for it in items:
            out.append("- " + _strip_tags(it).strip())
        return "\n" + "\n".join(out) + "\n"
    h = re.sub(r"(<ul[^>]*>)(.*?)</ul>", list_repl, h, flags=re.S | re.I)
    h = re.sub(r"(<ol[^>]*>)(.*?)</ol>", list_repl, h, flags=re.S | re.I)

    # Titres
    for i in range(6, 0, -1):
        h = re.sub(rf"<h{i}[^>]*>(.*?)</h{i}>", lambda m: "\n" + "#" * i + " " + _strip_tags(m.group(1)).strip() + "\n", h, flags=re.S | re.I)

    # Paragraphes et retours à la ligne
    h = re.sub(r"<p[^>]*>(.*?)</p>", lambda m: "\n" + _strip_tags(m.group(1)).strip() + "\n", h, flags=re.S | re.I)
    h = re.sub(r"<br\s*/?>", "\n", h, flags=re.S | re.I)

    # Retirer tout ce qui reste de balises
    h = re.sub(r"<[^>]+>", "", h)
    h = unescape(h)
    # Normaliser les espaces et lignes vides
    h = re.sub(r"[ \t]+", " ", h)
    h = re.sub(r"\n[ \t]+", "\n", h)
    h = re.sub(r"\n{3,}", "\n\n", h)
    return h.strip()


def build_llms_txt(pages):
    """Index au format llms.txt : titre, description, sections, liste des pages."""
    lines = []
    lines.append("# Département des Harnais")
    lines.append("")
    lines.append("> Atelier d'auteur sur l'IA : harness d'agents et agentivité, deterministic-first. Bruxelles, mmxxvi. Traces sous CC-BY 4.0.")
    lines.append("")
    lines.append("## À propos")
    lines.append("Le Département des Harnais (DDH) est l'atelier de John Linotte. Il défend une approche deterministic-first de l'orchestration d'agents IA : Python déterministe d'abord, LLM uniquement pour la compréhension du texte. Le site publie deux fils : Le Carnet (veille IA quotidienne sourcée) et Les Essais (positions longues numérotées T0…Tn).")
    lines.append("")
    lines.append("## Conditions d'usage")
    lines.append("- Citation/RAG (ai-input) autorisée — c'est l'objet de ce site.")
    lines.append("- Entraînement (ai-train) refusé (robots.txt Content-Signal, art. 4 directive EU 2019/790).")
    lines.append("- Traces sous licence Creative Commons BY 4.0 ; mentionner l'auteur John Linotte + l'URL source.")
    lines.append("- Contact : contact@harnais.be")
    lines.append("")
    lines.append("## Pages")

    # Tri logique : home, a-propos, sections, puis billets (récents d'abord) et essais (croissant)
    def sort_key(p):
        u = p[0]
        if u == "/":
            return (0, u)
        if u == "/a-propos/":
            return (1, u)
        if u == "/carnet/":
            return (2, u)
        if u == "/essais/":
            return (3, u)
        if u.startswith("/carnet/2026"):
            return (5, u)  # tri lexicographique inverse des dates ISO = récent d'abord
        if re.match(r"/essais/t\d+/", u):
            return (4, u)
        return (6, u)

    ordered = sorted(pages, key=sort_key, reverse=False)
    # Inverser les billets carnet pour récent d'abord (tri lexicographique inverse sur le groupe 5)
    carnet_group = [p for p in ordered if p[0].startswith("/carnet/2026")]
    carnet_group.sort(key=lambda x: x[0], reverse=True)
    rest = [p for p in ordered if not p[0].startswith("/carnet/2026")]
    ordered = rest + carnet_group

    chapeaux = load_chapeaux()
    for url_path, full in ordered:
        txt = read(full)
        title = title_of(txt) or url_path.strip("/") or "Index"
        if url_path == "/":
            summary = "Page d'accueil — présentation de l'atelier et des deux fils (Carnet, Essais)."
        elif url_path == "/a-propos/":
            summary = desc_of(txt) or "L'opérateur, la méthode deterministic-first, le manifeste de l'atelier."
        elif url_path == "/carnet/":
            summary = "Index du Carnet — chronique de veille IA quotidienne sourcée."
        elif url_path == "/essais/":
            summary = "Index des Essais — positions longues numérotées T0…Tn."
        elif url_path.startswith("/carnet/2026"):
            # Chapeau-first for billets
            billet_date = date_iso_from_url(url_path)
            chapeau = chapeaux.get(billet_date) if billet_date else None
            summary = chapeau or first_paragraph(txt) or desc_of(txt) or "Billet de veille IA."
        elif re.match(r"/essais/t\d+/", url_path):
            summary = first_paragraph(txt) or desc_of(txt) or "Essai du Département des Harnais."
        else:
            summary = desc_of(txt) or "Page du Département des Harnais."
        summary = re.sub(r"\s+", " ", summary).strip()
        if len(summary) > 180:
            summary = truncate_chapeau(summary, 180)
        lines.append(f"- [{title}]({BASE + url_path}): {summary}")

    lines.append("")
    return "\n".join(lines) + "\n"


def build_llms_full(pages):
    """Concaténation Markdown de tout le contenu publié, avec en-tête source."""
    parts = ["# Département des Harnais — texte intégral\n"]
    parts.append("> Compilation automatique de l'ensemble des pages publiées sur https://harnais.be, "
                 "destinée aux agents et moteurs de réponse. Traces CC-BY 4.0 — auteur : John Linotte.\n")

    def sort_key(p):
        u = p[0]
        if u == "/":
            return (0, u)
        if u == "/a-propos/":
            return (1, u)
        if u == "/carnet/":
            return (2, u)
        if u == "/essais/":
            return (3, u)
        if u.startswith("/carnet/2026"):
            return (5, u)
        if re.match(r"/essais/t\d+/", u):
            return (4, u)
        return (6, u)

    carnet_group = [p for p in pages if p[0].startswith("/carnet/2026")]
    carnet_group.sort(key=lambda x: x[0], reverse=True)
    rest = [p for p in pages if not p[0].startswith("/carnet/2026")]
    rest.sort(key=sort_key)
    ordered = rest + carnet_group

    chapeaux = load_chapeaux()
    for url_path, full in ordered:
        txt = read(full)
        title = title_of(txt) or url_path.strip("/") or "Index"
        article = extract_article(txt)
        # La home est un cartel décoratif sans <article> : son texte utile est déjà
        # repris dans /a-propos/. On saute pour éviter le bruit dans le full.
        if url_path == "/":
            continue
        md = html_to_markdown(article)
        if not md:
            continue
        # Chapeau-first (2026-06-18): for billets carnet, prepend the self-
        # contained lead as a markdown blockquote. LLMs parse this as the
        # canonical extract for the section — exactly what we want for RAG.
        chapeau_block = ""
        billet_date = date_iso_from_url(url_path)
        chapeau = chapeaux.get(billet_date) if billet_date else None
        if chapeau:
            chapeau_block = f"\n> {chapeau}\n"
        parts.append(f"\n\n---\n\n## {title}\n\nSource : {BASE + url_path}\n{chapeau_block}")
        parts.append(md)

    return "\n".join(parts).strip() + "\n"


def main():
    pages = collect_pages()
    sitemap = build_sitemap(pages)
    rss = build_rss(pages)
    jsonfeed = build_json_feed(pages)
    essais_rss = build_essais_rss(pages)
    essais_json = build_essais_json(pages)
    llms = build_llms_txt(pages)
    llms_full = build_llms_full(pages)

    sitemap_path = os.path.join(SITE_ROOT, "sitemap.xml")
    rss_path = os.path.join(SITE_ROOT, "carnet", "index.xml")
    json_path = os.path.join(SITE_ROOT, "carnet", "feed.json")
    essais_rss_path = os.path.join(SITE_ROOT, "essais", "index.xml")
    essais_json_path = os.path.join(SITE_ROOT, "essais", "feed.json")
    llms_path = os.path.join(SITE_ROOT, "llms.txt")
    llms_full_path = os.path.join(SITE_ROOT, "llms-full.txt")

    with open(sitemap_path, "w", encoding="utf-8") as f:
        f.write(sitemap)
    with open(rss_path, "w", encoding="utf-8") as f:
        f.write(rss)
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(jsonfeed)
    with open(essais_rss_path, "w", encoding="utf-8") as f:
        f.write(essais_rss)
    with open(essais_json_path, "w", encoding="utf-8") as f:
        f.write(essais_json)
    with open(llms_path, "w", encoding="utf-8") as f:
        f.write(llms)
    with open(llms_full_path, "w", encoding="utf-8") as f:
        f.write(llms_full)

    injected = inject_feed_links(pages)
    injected_canon = inject_canonical(pages)
    injected_jsonld = inject_jsonld(pages)

    n_billets = sum(1 for (u, _) in pages if u.startswith("/carnet/2026"))
    n_essais = sum(1 for (u, _) in pages if re.match(r"/essais/t\d+/", u))
    n_pages = len(pages)
    print(f"OK — sitemap.xml ({n_pages} URLs), carnet/index.xml ({n_billets} billets), essais/index.xml ({n_essais} essai(s))")
    print(f"  sitemap      : {sitemap_path}")
    print(f"  rss carnet   : {rss_path}")
    print(f"  json carnet  : {json_path}")
    print(f"  rss essais   : {essais_rss_path}")
    print(f"  json essais  : {essais_json_path}")
    print(f"  llms.txt     : {llms_path}")
    print(f"  llms-full    : {llms_full_path}")
    print(f"  balises découverte RSS/JSON injectées dans {injected} page(s)")
    print(f"  canonical ajoutés : {injected_canon} page(s)")
    print(f"  JSON-LD injectés  : {injected_jsonld} page(s)")


if __name__ == "__main__":
    main()