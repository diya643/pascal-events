#!/usr/bin/env python3
"""Build the event recap pages and the updated /events hub.

python3 src/build.py            -> public/ (base/ copy + recap pages + new hub + sitemap, robots, llms.txt)
The nav, footer, site.css and events.css come from base/ (a copy of the
pascal-events build), so recap pages match the live events pages.
"""
import hashlib, html, json, re, shutil, sys
from pathlib import Path
from PIL import Image, ImageOps, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from content import EVENTS, PHOTOS  # noqa: E402

BASE, OUT = ROOT / "base", ROOT / "public"
SITE = "https://pascalailabs.com"
PUBLISHED = "2026-11-19"
PHOTO_DIR = OUT / "assets/photos/recaps"

TPL = (BASE / "events/index.html").read_text()
HEADER = TPL[TPL.index("<body>"):TPL.index('<main id="main">')]
FOOTER = TPL[TPL.index("<footer"):]
HEAD_LINKS = re.search(r'(<link rel="icon".*?</script>\n<script async.*?</script>\n<script>.*?</script>)', TPL, re.S).group(1)


def esc(s):
    return html.escape(s, quote=True)


def md(s):
    """[text](href) -> link; everything else escaped."""
    out, pos = [], 0
    for m in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", s):
        out.append(esc(s[pos:m.start()]))
        out.append(f'<a href="{esc(m.group(2))}">{esc(m.group(1))}</a>')
        pos = m.end()
    out.append(esc(s[pos:]))
    return "".join(out)


def plain(s):
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)


def ver(p):
    return hashlib.md5(p.read_bytes()).hexdigest()[:10]


# ------------------------------------------------------------------ photos
def crop_to(im, ratio, fx, fy):
    w, h = im.size
    if w / h > ratio:
        nw = int(h * ratio); x = int(min(max(fx * w - nw / 2, 0), w - nw))
        return im.crop((x, 0, x + nw, h))
    nh = int(w / ratio); y = int(min(max(fy * h - nh / 2, 0), h - nh))
    return im.crop((0, y, w, y + nh))


SIZES = {"hero": (16 / 9, [2000, 1000]), "card": (3 / 2, [800]), "gal": (3 / 2, [1400, 700]),
         "galp": (4 / 5, [900, 600]), "og": (1200 / 630, [1200])}
_done = {}


def photo(key, kind):
    """Return {w: url} for a processed photo (cropped, resized with light sharpening)."""
    if (key, kind) in _done:
        return _done[(key, kind)]
    src, fx, fy, _ = PHOTOS[key]
    ratio, widths = SIZES[kind]
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    im = crop_to(im, ratio, fx, fy)
    urls = {}
    for w in widths:
        w2 = min(w, im.size[0])
        out = PHOTO_DIR / f"{key}-{kind}-{w}.jpg"
        out.parent.mkdir(parents=True, exist_ok=True)
        r = im.resize((w2, round(w2 / ratio)), Image.LANCZOS)
        if w2 < im.size[0]:  # downscaled: restore edge crispness
            r = r.filter(ImageFilter.UnsharpMask(radius=0.8, percent=60, threshold=2))
        r.save(out, quality=86, optimize=True, progressive=True)
        urls[w] = f"/assets/photos/recaps/{out.name}?v={ver(out)}"
    _done[(key, kind)] = urls
    return urls


def _is_portrait(key):
    im = ImageOps.exif_transpose(Image.open(PHOTOS[key][0]))
    return im.size[1] > im.size[0]


def img(key, kind, alt, sizes, eager=False, cls=""):
    urls = photo(key, kind)
    ws = sorted(urls)
    ratio = SIZES[kind][0]
    srcset = ", ".join(f"{urls[w]} {w}w" for w in ws)
    load = 'fetchpriority="high"' if eager else 'loading="lazy"'
    c = f' class="{cls}"' if cls else ""
    return (f'<img{c} src="{urls[ws[0]]}" srcset="{srcset}" sizes="{sizes}" alt="{esc(alt)}" '
            f'width="{ws[-1]}" height="{round(ws[-1] / ratio)}" {load} decoding="async">')


def credit(key):
    c = PHOTOS[key][3]
    if not c:
        return ""
    author, lic, url = c
    return f' <span class="rc-credit">Photo: <a href="{url}" rel="noopener">{esc(author)}</a>, {esc(lic)}, via Wikimedia Commons.</span>'


# ------------------------------------------------------------------ head
def head(title, desc, path, og, og_alt, schema, kind="article", keywords=(), published=None):
    url = SITE + path
    og_url = SITE + og.split("?")[0]
    art = ""
    if kind == "article":
        art = (f'<meta property="article:published_time" content="{published or PUBLISHED}">\n'
               f'<meta property="article:modified_time" content="{PUBLISHED}">\n'
               f'<meta property="article:section" content="Events">\n'
               f'<meta property="article:author" content="Pascal AI Labs">\n')
        art += "".join(f'<meta property="article:tag" content="{esc(k)}">\n' for k in keywords)
    kw = f'<meta name="keywords" content="{esc(", ".join(keywords))}">\n' if keywords else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script>document.documentElement.classList.add("js")</script>
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
{kw}<meta name="author" content="Pascal AI Labs">
<link rel="canonical" href="{url}">
<link rel="alternate" hreflang="en" href="{url}">
<link rel="alternate" hreflang="x-default" href="{url}">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">
<meta name="theme-color" content="#052A2E">
<meta property="og:type" content="{kind}">
<meta property="og:site_name" content="Pascal AI">
<meta property="og:locale" content="en_US">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{og_url}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{esc(og_alt)}">
{art}<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@pascalailabs">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{og_url}">
<meta name="twitter:image:alt" content="{esc(og_alt)}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Funnel+Display:wght@400;500;600&amp;family=Funnel+Sans:wght@400;500;600&amp;family=Geist+Mono:wght@400;500&amp;display=swap">
<link rel="stylesheet" href="/assets/site.css?v={ver(BASE / 'assets/site.css')}">
<link rel="stylesheet" href="/assets/pages/events.css?v={ver(BASE / 'assets/pages/events.css')}">
<link rel="stylesheet" href="/assets/pages/recaps.css?v={ver(ROOT / 'src/recaps.css')}">
{HEAD_LINKS}
<script type="application/ld+json">
{json.dumps(schema, indent=1, ensure_ascii=False)}
</script>
</head>
"""


def crumbs_schema(path, items):
    return {"@type": "BreadcrumbList", "@id": f"{SITE}{path}#breadcrumb", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + p} for i, (n, p) in enumerate(items)]}


ORG = {"@type": "Organization", "@id": f"{SITE}/#org", "name": "Pascal AI Labs", "alternateName": "Pascal AI",
       "url": f"{SITE}/", "logo": {"@type": "ImageObject", "url": f"{SITE}/assets/pascal-logo.png"},
       "sameAs": ["https://www.linkedin.com/company/pascal-ai-labs/", "https://twitter.com/pascalailabs"]}
WEBSITE = {"@type": "WebSite", "@id": f"{SITE}/#website", "url": f"{SITE}/", "name": "Pascal AI",
           "publisher": {"@id": f"{SITE}/#org"}}

CTA = """<section class="rc-cta dark" aria-labelledby="cta-title">
  <div class="rc-cta-in">
    <h2 class="h2" id="cta-title">See Pascal on Your Firm's Own Data</h2>
    <p>We run a working session on your documents, models and workflows, inside your environment.</p>
    <a class="btn btn-white" href="https://pascalailabs.com/demo">Book a demo</a>
  </div>
</section>"""

COUNTRY = {"HK": "Hong Kong", "SG": "Singapore", "US": "United States", "GB": "United Kingdom", "IN": "India"}


def faq_html(faq):
    items = "".join(f'<details class="faq-item"><summary>{esc(q)}<span class="pm" aria-hidden="true"></span></summary>'
                    f'<div class="ans">{esc(a)}</div></details>' for q, a in faq)
    return f"""<section class="row row-pad bg-cream" id="faq" aria-labelledby="faq-title">
    <div class="faq-wrap">
      <div><h2 class="h2" id="faq-title">Frequently Asked Questions</h2></div>
      <div class="faq">{items}</div>
    </div>
  </section>"""


# ------------------------------------------------------------------ recap page
def recap(ev, others):
    path = f"/events/{ev['slug']}"
    url = SITE + path
    hk, halt, hcap = ev["hero"]
    hero_urls = photo(hk, "hero")
    og = photo(hk, "og")[1200]
    has_own = PHOTOS[hk][3] is None
    facts = "".join(f"<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>" for k, v in ev["facts"])
    intro = "".join(f"<p>{md(p)}</p>" for p in ev["intro"])
    finds = "".join(f'<li><h3 class="rc-fh">{esc(h)}</h3><p>{md(p)}</p></li>' for h, p in ev["findings"])
    take = "".join(f"<p>{md(p)}</p>" for p in ev["take"])
    gal = ""
    if ev["gallery"]:
        n = len(ev["gallery"])
        portrait = all(_is_portrait(k) for k, _, _ in ev["gallery"])
        kind = "galp" if portrait else "gal"
        figs = "".join(
            f'<figure>{img(k, kind, a, "(max-width: 900px) 100vw, 600px")}<figcaption>{esc(c)}{credit(k)}</figcaption></figure>'
            for k, a, c in ev["gallery"])
        gal = f'<section class="rc-gal rc-gal-{n}{" rc-gal-p" if portrait else ""}" aria-label="Photos">{figs}</section>'
    more = "".join(
        f'<li class="ev-row rc-more-row"><span class="ev-row-city">{esc(o["city"])}</span>'
        f'<span class="ev-row-t">{esc(o["card"])}</span><span class="ev-row-d">{esc(o["date"])}</span>'
        f'<a href="/events/{o["slug"]}">Read the recap</a></li>' for o in others)
    label = "Invite-Only Event" if ev["kind"] == "invite" else "Conference"
    hosts = [v for k, v in ev["facts"] if k in ("Host", "Hosts", "Organizer", "Organizers")]
    event = {"@type": "Event", "@id": f"{url}#event", "name": ev["card"], "description": plain(ev["lead"]),
             "startDate": ev["iso"], "endDate": ev.get("iso_end", ev["iso"]),
             "eventStatus": "https://schema.org/EventScheduled",
             "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
             "image": [SITE + hero_urls[2000].split("?")[0]],
             "location": {"@type": "Place", "name": ev["venue"],
                          "address": {"@type": "PostalAddress", "addressLocality": ev["city"],
                                      "addressCountry": ev["country"]}}}
    if hosts:
        event["organizer"] = {"@type": "Organization", "name": hosts[0]}
    if ev["speakers"]:
        event["performer"] = [{"@type": "Person", "name": n, "jobTitle": t} for n, t in ev["speakers"]]
    article = {"@type": "BlogPosting", "@id": f"{url}#article", "headline": ev["title"][:110],
               "description": ev["description"], "url": url, "mainEntityOfPage": {"@id": f"{url}#webpage"},
               "image": {"@type": "ImageObject", "url": SITE + og.split("?")[0], "width": 1200, "height": 630},
               "inLanguage": "en", "datePublished": PUBLISHED, "dateModified": PUBLISHED,
               "articleSection": "Events", "keywords": ev["keywords"],
               "wordCount": len(" ".join([ev["lead"], *ev["intro"], *[h + " " + p for h, p in ev["findings"]], *ev["take"]]).split()),
               "author": {"@id": f"{SITE}/#org"}, "publisher": {"@id": f"{SITE}/#org"},
               "about": {"@id": f"{url}#event"}}
    if ev["speakers"]:
        article["mentions"] = [{"@type": "Person", "name": n, "jobTitle": t} for n, t in ev["speakers"]]
    schema = {"@context": "https://schema.org", "@graph": [
        ORG, WEBSITE,
        {"@type": "WebPage", "@id": f"{url}#webpage", "url": url, "name": ev["seo_title"], "description": ev["description"],
         "inLanguage": "en", "isPartOf": {"@id": f"{SITE}/#website"}, "breadcrumb": {"@id": f"{url}#breadcrumb"},
         "primaryImageOfPage": SITE + og.split("?")[0], "datePublished": PUBLISHED, "dateModified": PUBLISHED},
        article, event,
        {"@type": "FAQPage", "@id": f"{url}#faq", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in ev["faq"]]},
        crumbs_schema(path, [("Home", "/"), ("Events", "/events"), (ev["card"], path)]),
    ]}
    body = f"""<main id="main">
<article>
<section class="hero-teal hero-ent rc-hero" aria-labelledby="page-title">
  <div class="hero-teal-in">
    <nav class="crumbs" aria-label="Breadcrumb"><a href="/">Home</a><span aria-hidden="true">/</span><a href="/events">Events</a><span aria-hidden="true">/</span><span aria-current="page">{esc(ev['card'])}</span></nav>
    <p class="rc-kind">{label} · {esc(ev['city'])} · <time datetime="{ev['iso']}">{esc(ev['date'])}</time></p>
    <h1 class="rc-h1" id="page-title">{esc(ev['title'])}</h1>
    <p class="lead rc-lead">{md(ev['lead'])}</p>
    <dl class="rc-facts">{facts}</dl>
  </div>
</section>
<div class="frame">
  <figure class="rc-heroimg{'' if has_own else ' rc-heroimg-stock'}">{img(hk, "hero", halt, "(max-width: 1280px) 100vw, 1280px", eager=True)}<figcaption>{esc(hcap)}{credit(hk)}</figcaption></figure>
  <section class="row rc-row" aria-labelledby="about-title">
    <h2 class="rc-h2" id="about-title">{esc(ev['intro_h'])}</h2>
    <div class="rc-body">{intro}</div>
  </section>
  <section class="row rc-row bg-cream" aria-labelledby="find-title">
    <h2 class="rc-h2" id="find-title">{esc(ev['findings_h'])}</h2>
    <ol class="rc-finds">{finds}</ol>
  </section>
  {gal}
  <section class="row rc-row" aria-labelledby="take-title">
    <h2 class="rc-h2" id="take-title">{esc(ev['take_h'])}</h2>
    <div class="rc-body">{take}</div>
  </section>
  {faq_html(ev['faq'])}
  <section class="row rc-row bg-mint" aria-labelledby="more-title">
    <h2 class="rc-h2" id="more-title">More Event Recaps</h2>
    <div class="rc-body rc-more"><ul class="ev-rows">{more}</ul><p class="rc-all"><a href="/events">See all events</a></p></div>
  </section>
  {CTA}
</div>
</article>
</main>
"""
    return head(ev["seo_title"], ev["description"], path, og, halt, schema, "article", ev["keywords"]) + HEADER + body + FOOTER


# ------------------------------------------------------------------ hub
def card(ev):
    k = ev["hero"][0]
    return (f'<li class="rc-card"><a href="/events/{ev["slug"]}">'
            f'{img(k, "card", ev["hero"][1], "(max-width: 700px) 100vw, (max-width: 1100px) 50vw, 400px")}'
            f'<p class="rc-card-meta"><time datetime="{ev["iso"]}">{esc(ev["date"])}</time> · {esc(ev["city"])}</p>'
            f'<h3 class="rc-card-t">{esc(ev["card"])}</h3>'
            f'<span class="rc-card-link">Read the recap</span></a></li>')


HUB_FAQ = [
    ("What events does Pascal AI Labs host?", "Invite-only roundtables, dinners and breakfasts for leaders at hedge funds, asset managers and the firms that serve them, often co-hosted with partners."),
    ("Which conferences does Pascal attend?", "Industry forums including Global Fintech Fest, Global Alts Miami, InvestOps Asia, the AIMA APAC Annual Forum and MFA Ops."),
    ("How can I attend a Pascal roundtable?", "Our roundtables are invite-only. Book a demo or contact the Pascal team to be considered for upcoming events."),
    ("Are the roundtable discussions attributed?", "No. Our roundtables run under the Chatham House Rule, so recaps share themes without naming who said what."),
]


def hub():
    inv = [e for e in EVENTS if e["kind"] == "invite"]
    conf = [e for e in EVENTS if e["kind"] == "conf"]
    title = "Events and Roundtables | Pascal AI"
    desc = ("Recaps of Pascal AI Labs events: invite-only roundtables for hedge fund and asset manager leaders, "
            "and the industry conferences where we exhibit and speak.")
    og = photo(inv[1]["hero"][0], "og")[1200]
    url = f"{SITE}/events"
    schema = {"@context": "https://schema.org", "@graph": [
        ORG, WEBSITE,
        {"@type": "CollectionPage", "@id": f"{url}#webpage", "url": url, "name": title, "description": desc,
         "inLanguage": "en", "isPartOf": {"@id": f"{SITE}/#website"}, "breadcrumb": {"@id": f"{url}#breadcrumb"},
         "dateModified": PUBLISHED, "mainEntity": {"@id": f"{url}#list"}},
        {"@type": "ItemList", "@id": f"{url}#list", "name": "Pascal AI Labs event recaps", "numberOfItems": len(EVENTS),
         "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f"{SITE}/events/{e['slug']}", "name": e["card"]}
                             for i, e in enumerate(inv + conf)]},
        {"@type": "FAQPage", "@id": f"{url}#faq", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in HUB_FAQ]},
        crumbs_schema("/events", [("Home", "/"), ("Events", "/events")]),
    ]}
    body = f"""<main id="main">
<section class="hero-teal hero-ent" aria-labelledby="page-title">
  <div class="hero-teal-in">
    <nav class="crumbs" aria-label="Breadcrumb"><a href="/">Home</a><span aria-hidden="true">/</span><span aria-current="page">Events</span></nav>
    <div class="ht-grid">
      <div><h1 class="h1" id="page-title">Events</h1></div>
      <div class="ht-side">
        <p class="lead">Private roundtables we host with partners, the industry conferences where we exhibit and speak, and what we learned at each one.</p>
      </div>
    </div>
  </div>
</section>
<div class="frame">
  <section class="row rc-hubsec" aria-labelledby="inv-title">
    <div class="rc-hubhead">
      <h2 class="h2" id="inv-title">Invite-Only Roundtables</h2>
      <p>Closed-door sessions for leaders at hedge funds, asset managers and the firms that serve them, hosted by Pascal or by our partners.</p>
    </div>
    <ul class="rc-cards">{''.join(card(e) for e in inv)}</ul>
  </section>
  <section class="row rc-hubsec bg-cream" aria-labelledby="conf-title">
    <div class="rc-hubhead">
      <h2 class="h2" id="conf-title">Conferences</h2>
      <p>Industry forums where our team exhibits, speaks and meets clients.</p>
    </div>
    <ul class="rc-cards">{''.join(card(e) for e in conf)}</ul>
  </section>
  <section class="row row-pad" aria-labelledby="host-title">
    <h2 class="h2" id="host-title" style="margin-bottom:40px">About Pascal AI Labs</h2>
    <div class="ev-host">
      <div class="ev-host-logo"><img src="/assets/pascal-logo.png" alt="Pascal AI Labs" width="360" height="106" loading="lazy"></div>
      <div class="ev-host-copy">
        <h3>Pascal AI Labs</h3>
        <p>Pascal builds context-driven AI agents for institutional finance, working across the front, middle and back office for <a href="{SITE}/solutions/hedge-funds">hedge funds</a>, <a href="{SITE}/solutions/asset-wealth-management">asset managers</a> and <a href="{SITE}/solutions/asset-servicing">asset servicers</a>.</p>
      </div>
    </div>
  </section>
  {faq_html(HUB_FAQ)}
  {CTA}
</div>
</main>
"""
    return head(title, desc, "/events", og, "Pascal AI Labs events and roundtables", schema, "website") + HEADER + body + FOOTER


# ------------------------------------------------------------------ sitemap, robots, llms
def extras():
    urls = [("/events", PUBLISHED)] + [(f"/events/{e['slug']}", PUBLISHED) for e in EVENTS]
    sm = "".join(f"  <url><loc>{SITE}{p}</loc><lastmod>{d}</lastmod></url>\n" for p, d in urls)
    (OUT / "sitemap-events.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{sm}</urlset>\n')
    lines = ["# Pascal AI Labs: Events", "",
             "> Recaps of the invite-only roundtables Pascal AI Labs hosts with partners and the industry conferences it attends, written from Pascal's point of view.", "",
             "## Invite-only roundtables"]
    lines += [f"- [{e['card']}]({SITE}/events/{e['slug']}): {e['description']}" for e in EVENTS if e["kind"] == "invite"]
    lines += ["", "## Conferences"]
    lines += [f"- [{e['card']}]({SITE}/events/{e['slug']}): {e['description']}" for e in EVENTS if e["kind"] == "conf"]
    (OUT / "llms-events.txt").write_text("\n".join(lines) + "\n")


# ------------------------------------------------------------------ audit
BANNED = ["delve", "underscore", "landscape", "robust", "game-changer", "game changer", "seamless", "unlock",
          "transformative", "groundbreaking", "cutting-edge", "cutting edge", "revolutionize", "revolutionise", "empower",
          "embark", "synergy", "holistic", "streamline", "unpack", "deep dive", "it's important to note",
          "it's worth mentioning", "it's worth noting", "in today's world", "in the age of ai", "rapidly evolving",
          "moreover", "furthermore", "leverage", "leverages", "leveraging", "leveraged", "navigate", "navigating",
          "harness", "supercharge", "effortless"]
CONTRAST = re.compile(r"(\.\s+not\b|,\s+not\b|\bnot just\b|\binstead of\b|\brather than\b|\bisn't about\b)", re.I)
UK = re.compile(r"(\w+isation|organis\w*|summaris\w*|recognis\w*|prioritis\w*|analys(e|ed|es|ing)|labelled|programme|centre)\b", re.I)
MINOR = {"a", "an", "the", "and", "but", "or", "nor", "for", "so", "yet", "as", "at", "by", "in", "of", "on", "to", "up", "vs", "via", "per"}
EXTERNAL_NAMES = ["AlphaSense", "Albourne", "Ackerson", "Schmidt", "Malhotra", "Pandey", "NPCI", "iConnections", "Refresh Miami",
                  "Viking", "Coatue", "Millennium", "Bridgewater", "Citadel", "Apollo", "Linklaters", "LinqAlpha"]


def title_case_issues(t):
    bad = []
    words = re.findall(r"[A-Za-z][\w'’&-]*", t)
    for i, w in enumerate(words):
        if w.lower() in MINOR and i > 0:
            continue
        if w[0].islower() and not w.startswith(("iConnections",)):
            bad.append(w)
    return bad


def audit(ev):
    text = " ".join([ev["title"], ev["lead"], *ev["intro"], *[h + " " + p for h, p in ev["findings"]], *ev["take"],
                     *[c for _, _, c in ev["gallery"]], ev["hero"][2], *[q + " " + a for q, a in ev["faq"]]])
    p = plain(text)
    issues = []
    low = p.lower().replace("’", "'")
    for w in BANNED:
        if re.search(r"\b" + re.escape(w) + r"\b", low):
            issues.append(f"banned word '{w}'")
    for m in CONTRAST.finditer(p):
        issues.append(f"contrast: ...{p[max(0, m.start() - 40):m.end() + 20]}...")
    if "—" in p or " – " in p:
        issues.append("em/en dash in copy")
    for m in UK.finditer(p):
        if m.group(0).lower() not in ("centre",) or "Centre" not in m.group(0):
            issues.append(f"UK spelling '{m.group(0)}'")
    findings = " ".join(f for _, f in ev["findings"])
    for n in EXTERNAL_NAMES:
        if n.lower() in findings.lower():
            issues.append(f"name-drop in findings: {n}")
    for h in [ev["title"], ev["card"], ev["intro_h"], ev["findings_h"], ev["take_h"], *[h for h, _ in ev["findings"]]]:
        b = title_case_issues(h)
        if b:
            issues.append(f"title case '{h}': {b}")
    if len(ev["seo_title"]) > 65:
        issues.append(f"seo title {len(ev['seo_title'])} chars")
    if not 110 <= len(ev["description"]) <= 165:
        issues.append(f"description {len(ev['description'])} chars")
    if not 12 <= len(ev["lead"].split()) <= 45:
        issues.append(f"lead is {len(ev['lead'].split())} words")
    if len(re.findall(r"\]\(https://pascalailabs\.com/", text)) < 2:
        issues.append("fewer than 2 links to pascalailabs.com")
    words = len(plain(" ".join([ev["lead"], *ev["intro"], *[h + " " + f for h, f in ev["findings"]], *ev["take"]])).split())
    return words, issues


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(BASE, OUT)
    (OUT / "assets/pages").mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "src/recaps.css", OUT / "assets/pages/recaps.css")
    bad = 0
    for i, ev in enumerate(EVENTS):
        same = [e for e in EVENTS if e is not ev]
        others = (same[i:] + same[:i])[:3]
        d = OUT / "events" / ev["slug"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(recap(ev, others))
        words, issues = audit(ev)
        bad += bool(issues)
        print(f"{'FIX' if issues else 'OK '} {ev['slug']:<55} {words:>4} words")
        for x in issues:
            print("     -", x)
    (OUT / "events/index.html").write_text(hub())
    extras()
    print("wrote", len(EVENTS), "recaps + events/index.html + sitemap-events.xml, llms-events.txt")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
