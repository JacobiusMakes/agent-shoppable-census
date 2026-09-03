#!/usr/bin/env python3
"""
Agent-Shoppable Census probe.

For every domain in data/domains.csv this script fetches a fixed set of public
URLs, records the raw evidence, and classifies the seller into one of three
buckets:

  Tier A  (merchant-built)      the seller itself published something for AI
                                agents: an entry in the official MCP Registry,
                                a live custom /mcp endpoint or .well-known/mcp.json,
                                an agents.md or llms.txt with real content that is
                                not a platform template, an ACP checkout endpoint,
                                or a UCP profile that is not the Shopify-hosted
                                default.
  Tier B  (platform-inherited)  only what the platform gives every store by
                                default: a Shopify-hosted /.well-known/ucp, a
                                platform-templated agents.md or llms.txt, or
                                schema.org Product/Offer JSON-LD emitted by the
                                theme.
  Unreachable                   none of the above, or the site refused automated
                                fetches.

Safety rules baked in:
  * GET only, except one JSON-RPC "initialize" and one "tools/list" POST to
    endpoints that advertise MCP (read-only discovery calls).
  * Never creates carts, checkouts, sessions, or accounts.
  * One request per second per host, 15 second timeout, honest User-Agent.

Standard library only, plus `requests` if installed (falls back to urllib).

License: MIT (script). Tables and text in this repository: CC BY 4.0.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html import unescape
from urllib.parse import urljoin, urlparse

try:
    import requests  # type: ignore
    HAVE_REQUESTS = True
except Exception:  # pragma: no cover
    HAVE_REQUESTS = False
    import urllib.request
    import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
DOMAINS_CSV = os.path.join(DATA, "domains.csv")
RESULTS_JSONL = os.path.join(DATA, "probe-results.jsonl")
SUMMARY_CSV = os.path.join(DATA, "probe-summary.csv")
REGISTRY_SNAPSHOT = os.path.join(DATA, "mcp-registry-snapshot.json")
CHATGPT_APPS_README = os.path.join(DATA, "awesome-chatgpt-apps-README.md")
RUN_META = os.path.join(DATA, "run-meta.json")

PROBE_VERSION = "0.2"
USER_AGENT = (
    f"StienhardtAgentCensus/{PROBE_VERSION} (read-only agent-readiness census; "
    "+https://stienhardt.com/agents.md)"
)
TIMEOUT = 15
PER_HOST_INTERVAL = 1.0  # seconds between requests to the same host
MAX_BODY = 1_500_000     # bytes we keep from any single response
SNIPPET = 400

REGISTRY_BASE = "https://registry.modelcontextprotocol.io/v0/servers"
CHATGPT_APPS_URL = (
    "https://raw.githubusercontent.com/rdmgator12/awesome-chatgpt-apps/main/README.md"
)

AI_BOTS = [
    "GPTBot", "ChatGPT-User", "OAI-SearchBot", "ClaudeBot", "Claude-User",
    "Claude-SearchBot", "anthropic-ai", "PerplexityBot", "Perplexity-User",
    "Google-Extended", "CCBot", "Bytespider", "Applebot-Extended", "meta-externalagent",
]

BOT_WALL_MARKERS = [
    "just a moment", "cf-browser-verification", "challenge-platform",
    "attention required", "access denied", "request unsuccessful",
    "incapsula", "_incapsula_resource", "perimeterx", "px-captcha",
    "datadome", "captcha-delivery", "akamai", "reference #18.",
    "are you a human", "verify you are human", "bot detection",
    "enable javascript and cookies to continue", "pardon our interruption",
]

# Hosts that bot-check services redirect a challenged visitor to. A homepage that lands on one
# of these is a blocked fetch, not a site that moved (jamesallen.com sent the 2026-09-02 run to
# validate.perfdrive.com, a PerimeterX challenge host, and the row was mis-read as a redirect).
BOT_WALL_HOSTS = ("perfdrive.com", "captcha-delivery.com", "perimeterx.net", "px-cdn.net",
                  "px-cloud.net", "datadome.co", "hcaptcha.com", "arkoselabs.com")

# ----------------------------------------------------------------------------
# polite HTTP
# ----------------------------------------------------------------------------

_host_lock = threading.Lock()
_host_last: dict[str, float] = {}


def _wait_host(host: str) -> None:
    """Block until at least PER_HOST_INTERVAL has passed since the last request to host."""
    while True:
        with _host_lock:
            last = _host_last.get(host, 0.0)
            now = time.monotonic()
            gap = now - last
            if gap >= PER_HOST_INTERVAL:
                _host_last[host] = now
                return
            sleep_for = PER_HOST_INTERVAL - gap
        time.sleep(sleep_for)


def fetch(url: str, method: str = "GET", headers: dict | None = None,
          body: bytes | None = None, allow_redirects: bool = True, _retry: bool = True) -> dict:
    """Fetch a URL politely. Returns a dict with status, headers, text, final_url, error.
    A connection-level failure (timeout, reset, DNS) is retried once after two seconds; HTTP
    status codes are never retried. One earlier run lost a real llms.txt to a single reset."""
    out = _fetch_once(url, method, headers, body, allow_redirects)
    if out["error"] and _retry and method == "GET":
        time.sleep(2.0)
        again = _fetch_once(url, method, headers, body, allow_redirects)
        again["retried"] = True
        if not again["error"]:
            return again
        out["retried"] = True
    return out


def _fetch_once(url: str, method: str, headers: dict | None, body: bytes | None,
                allow_redirects: bool) -> dict:
    host = urlparse(url).netloc.lower()
    _wait_host(host)
    hdrs = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/json,text/plain,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if headers:
        hdrs.update(headers)
    out = {"url": url, "method": method, "status": None, "final_url": None,
           "headers": {}, "text": "", "bytes": 0, "error": None, "elapsed_ms": None}
    t0 = time.monotonic()
    try:
        if HAVE_REQUESTS:
            r = requests.request(method, url, headers=hdrs, data=body,
                                 timeout=TIMEOUT, allow_redirects=allow_redirects,
                                 stream=True)
            raw = b""
            for chunk in r.iter_content(65536):
                raw += chunk
                if len(raw) >= MAX_BODY:
                    break
            r.close()
            out["status"] = r.status_code
            out["final_url"] = r.url
            out["headers"] = {k.lower(): v for k, v in r.headers.items()}
            # requests labels text/* bodies with no charset as ISO-8859-1, which turned UTF-8
            # llms.txt files into mojibake in the 2026-09-02 run. Try strict UTF-8 first, then
            # the declared encoding, then UTF-8 with replacement.
            declared = r.encoding
            try:
                out["text"] = raw.decode("utf-8", errors="strict")
            except Exception:
                try:
                    out["text"] = raw.decode(declared or "utf-8", errors="replace")
                except Exception:
                    out["text"] = raw.decode("utf-8", errors="replace")
            out["text"] = out["text"].lstrip("\ufeff")
            out["bytes"] = len(raw)
        else:  # pragma: no cover
            req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
            try:
                with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                    raw = resp.read(MAX_BODY)
                    out["status"] = resp.status
                    out["final_url"] = resp.geturl()
                    out["headers"] = {k.lower(): v for k, v in resp.headers.items()}
            except urllib.error.HTTPError as e:
                raw = e.read(MAX_BODY) if hasattr(e, "read") else b""
                out["status"] = e.code
                out["final_url"] = url
                out["headers"] = {k.lower(): v for k, v in e.headers.items()}
            out["text"] = raw.decode("utf-8", errors="replace")
            out["bytes"] = len(raw)
    except Exception as e:  # network errors, timeouts, TLS, DNS
        # Drop object addresses ("... at 0x1b69dcc0590>") so two runs of the same failure diff clean.
        out["error"] = re.sub(r" at 0x[0-9a-fA-F]+", "", f"{type(e).__name__}: {str(e)[:220]}")
    out["elapsed_ms"] = int((time.monotonic() - t0) * 1000)
    return out


def ctype(resp: dict) -> str:
    return (resp.get("headers") or {}).get("content-type", "").lower()


def looks_like_html(text: str) -> bool:
    head = text[:2000].lower()
    return "<html" in head or "<!doctype html" in head or "<head" in head or "<body" in head


def bot_wall(resp: dict) -> bool:
    if resp.get("status") in (403, 429, 503):
        return True
    t = (resp.get("text") or "")[:5000].lower()
    return any(m in t for m in BOT_WALL_MARKERS) and resp.get("status") != 200 or (
        resp.get("status") == 200 and ("just a moment" in t or "px-captcha" in t or "datadome" in t)
    )


def snippet(text: str, n: int = SNIPPET) -> str:
    return re.sub(r"\s+", " ", (text or "")[:n]).strip()


def try_json(text: str):
    t = (text or "").strip()
    if not t:
        return None
    try:
        return json.loads(t)
    except Exception:
        return None


# ----------------------------------------------------------------------------
# JSON-LD
# ----------------------------------------------------------------------------

LDJSON_RE = re.compile(
    r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
    re.IGNORECASE | re.DOTALL,
)


def _walk(node, acc: list):
    if isinstance(node, dict):
        acc.append(node)
        for v in node.values():
            _walk(v, acc)
    elif isinstance(node, list):
        for v in node:
            _walk(v, acc)


def _repair_json(b: str) -> str:
    """Minimal repairs for the two defects seen on real product pages: raw control characters
    inside strings (finks.com) and trailing commas before } or ] (withclarity.com)."""
    b = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", b)
    b = re.sub(r"(?<!\\)\n", " ", b)
    b = re.sub(r",\s*([}\]])", r"\1", b)
    return b


def parse_jsonld(html: str) -> dict:
    """Return a summary of JSON-LD in the page: types, product presence, gtin/mpn/sku.
    A block that fails strict parsing is retried after _repair_json; if it then parses it is
    counted and flagged `repaired`. A block that still fails but mentions "Product" is flagged
    `malformed_product` and NOT counted as present: that is what a strict agent parser sees."""
    blocks = LDJSON_RE.findall(html or "")
    types: list[str] = []
    product_nodes: list[dict] = []
    parsed = 0
    repaired = 0
    malformed_product = 0
    for b in blocks:
        b = unescape(b).strip()
        b = re.sub(r"^\s*<!--|-->\s*$", "", b)
        data = try_json(b)
        if data is None:
            # Some themes emit several JSON objects back to back; try to salvage the leading one.
            m = re.search(r"\{.*\}", b, re.DOTALL)
            data = try_json(m.group(0)) if m else None
        if data is None:
            data = try_json(_repair_json(b))
            if data is not None:
                repaired += 1
        if data is None:
            if re.search(r"[\"']@type[\"']\s*:\s*[\"']Product", b):
                malformed_product += 1
            continue
        parsed += 1
        nodes: list[dict] = []
        _walk(data, nodes)
        for n in nodes:
            t = n.get("@type")
            if isinstance(t, list):
                tl = [str(x) for x in t]
            elif t is None:
                tl = []
            else:
                tl = [str(t)]
            types.extend(tl)
            if any(x in ("Product", "ProductGroup", "ProductModel", "IndividualProduct") for x in tl):
                product_nodes.append(n)
    has_product = bool(product_nodes)
    has_offer = any(x in ("Offer", "AggregateOffer") for x in types)
    gtin = False
    mpn = False
    sku = False
    for p in product_nodes:
        sub: list[dict] = []
        _walk(p, sub)
        for n in sub:
            for k in n.keys():
                kl = str(k).lower()
                if kl.startswith("gtin") or kl == "isbn":
                    if n.get(k) not in (None, "", [], {}):
                        gtin = True
                if kl == "mpn" and n.get(k) not in (None, "", [], {}):
                    mpn = True
                if kl == "sku" and n.get(k) not in (None, "", [], {}):
                    sku = True
    return {
        "blocks": len(blocks),
        "parsed": parsed,
        "repaired": repaired,
        "malformed_product": malformed_product,
        "types": sorted(set(types))[:40],
        "has_product": has_product,
        "has_offer": has_offer,
        "gtin": gtin,
        "mpn": mpn,
        "sku": sku,
    }


# ----------------------------------------------------------------------------
# platform detection
# ----------------------------------------------------------------------------

def detect_platform(home: dict, extra_html: str = "") -> dict:
    h = home.get("headers") or {}
    html = ((home.get("text") or "") + " " + (extra_html or ""))
    hl = html.lower()
    plat = None
    signals = []
    # Strong Shopify signals only. A bare "cdn.shopify.com" reference is NOT enough: Shop Pay
    # buttons and Shop app embeds put that host on non-Shopify sites (an early smoke test hit
    # this on brilliantearth.com).
    if "x-shopid" in h or "x-shopify-stage" in h or "x-sorting-hat-shopid" in h or "x-shardid" in h:
        plat = "shopify"; signals.append("shopify-headers")
    strong_html = [s for s in ("shopify.theme", "shopify-checkout-api-token",
                               "cdn.shopify.com/s/files/", "window.shopify", "shopify.routes",
                               "shopify-digital-wallet", "shopify-section")
                   if s in hl]
    # An actual <shop>.myshopify.com hostname counts; the bare string ".myshopify.com" does
    # not, because generic scripts test for it (the second smoke test hit that on
    # brilliantearth.com).
    myshopify_hosts = sorted(set(re.findall(r"\b([a-z0-9][a-z0-9-]{1,80}\.myshopify\.com)\b", hl)))
    if strong_html:
        plat = plat or "shopify"; signals.append("shopify-html:" + ",".join(strong_html[:3]))
    if myshopify_hosts:
        signals.append("myshopify-host:" + myshopify_hosts[0])
        if plat is None:
            # A Shopify store is referenced by page scripts, but the storefront itself shows no
            # theme or header signals: headless, partial, or a dev store (brilliantearth.com
            # references brilliantearth-dev.myshopify.com in an A/B testing config).
            plat = "shopify-referenced"
    if plat is None and ("cdn.shopify.com" in hl or ".myshopify.com" in hl):
        signals.append("weak:shopify-string-only")
    if plat is None:
        if "demandware" in hl or "dwstatic" in hl or "/on/demandware.store" in hl:
            plat = "salesforce-commerce-cloud"
        elif "bigcommerce" in hl or "cdn11.bigcommerce.com" in hl:
            plat = "bigcommerce"
        elif "/static/frontend/" in hl and "magento" in hl or "mage/" in hl and "requirejs" in hl:
            plat = "magento"
        elif "wp-content/plugins/woocommerce" in hl:
            plat = "woocommerce"
        elif "squarespace" in hl and "static1.squarespace.com" in hl:
            plat = "squarespace"
        elif "wix.com" in hl and "static.wixstatic.com" in hl:
            plat = "wix"
        elif "commercecloud" in hl or "salesforce" in (h.get("x-powered-by", "").lower()):
            plat = "salesforce-commerce-cloud"
        elif "cdn.shoprenter" in hl:
            plat = "shoprenter"
        elif "x-hybris" in h or "hybris" in hl and "/_ui/" in hl:
            plat = "sap-commerce"
        elif "commercetools" in hl:
            plat = "commercetools"
        elif "webflow" in hl and "assets.website-files.com" in hl:
            plat = "webflow"
    checkout_shopify = plat == "shopify" or "checkout.shopify.com" in hl or "/checkouts/" in hl and "shopify" in hl
    return {"platform": plat, "signals": signals, "checkout_shopify": bool(checkout_shopify)}


# ----------------------------------------------------------------------------
# product page discovery
# ----------------------------------------------------------------------------

HREF_RE = re.compile(r"href=[\"']([^\"'#?]+)(?:[?#][^\"']*)?[\"']", re.IGNORECASE)
# Path fragments that identify a single product page on the common platforms
# (Shopify /products/<handle>, WooCommerce and Magento /product/<slug>, SAP and SFCC /p/<id>,
# BigCommerce /item/, misc /pd/ and /dp/). Category words like /rings/ are deliberately
# NOT hints: they select collection pages, which was the failure in an early smoke test.
PRODUCT_PATH_HINTS = ("/products/", "/product/", "/p/", "/pd/", "/prod/", "/item/", "/dp/", "/product-page/")
COLLECTION_HINTS = ("/collections/", "/c/", "/category/", "/shop/", "/engagement-rings", "/engagement", "/rings")
PRODUCT_WORDS = ("ring", "solitaire", "engagement", "diamond", "band")
NON_PAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg", ".css", ".js", ".xml", ".pdf", ".ico")


def _same_site(u: str, base: str) -> bool:
    return urlparse(u).netloc.lower().replace("www.", "") == urlparse(base).netloc.lower().replace("www.", "")


EXCLUDED_SECTIONS = ("blog", "blogs", "guide", "guides", "education", "learn", "news", "press",
                     "article", "articles", "stories", "journal", "magazine", "faq", "faqs",
                     "policy", "policies", "about", "contact", "sitemap", "careers", "help",
                     "support", "stores", "store-locator", "services", "reviews", "events",
                     "discover", "similar", "info", "pages", "account", "cart", "checkout", "search",
                     "journals", "trends", "inspiration", "lookbook", "editorial", "community")


def _excluded_section(path_lower: str) -> bool:
    return any(("/" + x + "/") in path_lower or path_lower.endswith("/" + x) for x in EXCLUDED_SECTIONS)


def _is_product_path(path: str) -> bool:
    p = path.lower()
    if p.endswith(NON_PAGE_EXT) or _excluded_section(p):
        return False
    for h in PRODUCT_PATH_HINTS:
        i = p.find(h)
        if i >= 0:
            rest = p[i + len(h):].strip("/")
            # /products/<handle>, /product/<slug>/, /p/<id>, /product/<id>/<slug>: one or two
            # segments after the hint. Three or more is a utility page (/products/info/id/52007).
            if rest and len(rest) >= 2 and rest.count("/") <= 1:
                return True
    return False


PRODUCT_WORDS_EXT = ("ring", "solitaire", "engagement", "diamond", "band", "earring", "necklace",
                     "pendant", "bracelet", "halo", "pave", "setting")


def _is_product_path_heuristic(path: str) -> bool:
    """Second-pass picker for platforms whose product URLs carry no path hint.
    Shapes seen in the sample: /engagement-rings/<slug>/2810968.html (Salesforce Commerce Cloud),
    /wedding/engagement-rings/<slug>-WR1118RPL.html (SFCC with SKU), <slug>-item-291542 (Blue Nile),
    <slug>-3644.htm (Whiteflash), /fine-jewelry/<slug>/53680 (Rare Carat),
    /0465906-<slug>-2144719724 (Robbins Brothers). Requires a long slug, a product word, and
    either a numeric or SKU-like id or an .html/.htm ending."""
    p = path
    if p.lower().endswith(NON_PAGE_EXT) and not p.lower().endswith((".html", ".htm")):
        return False
    segs = [s for s in p.split("/") if s]
    if not segs:
        return False
    # Editorial and utility sections anywhere in the path disqualify the URL (Blue Nile's
    # /blog/love-brilliant/... post slipped through when only the tail was checked).
    pl = p.lower()
    if _excluded_section(pl) or any(("/" + x + "-") in pl for x in ("shopping-guide", "guide", "how-to", "what-is")):
        return False
    # Price facets (/wedding-bands-500-to-1000, /rings-under-500, /up-to-1000) are category pages.
    if re.search(r"\d+-to-\d+|(?:under|over|up-to|below|above)-\d+|\d+-(?:and|or)-(?:under|over|up|less|more)", pl):
        return False
    tail = "/".join(segs[-2:])
    tail_l = tail.lower()
    core = re.sub(r"\.html?$", "", tail_l)
    words = [w for w in re.split(r"[-_/]", core) if w]
    long_slug = len(words) >= 5
    product_word = any(w in tail_l for w in PRODUCT_WORDS_EXT)
    # A trailing year (…-trends-for-2021) is an article date, not a product id.
    if re.search(r"-(?:19|20)\d\d(?:\.html?)?/?$", tail_l) and re.search(r"-(?:for|in|of|the)-(?:19|20)\d\d", tail_l):
        return False
    has_num_id = bool(re.search(r"(?:^|[-/_])(?:item-)?\d{4,}(?:$|[-/_.])", tail_l))
    has_sku = bool(re.search(r"[-/][A-Za-z]{1,4}\d{3,}[A-Za-z0-9]*(?:\.html?)?$", tail))
    # A trailing short numeric id (adadiamonds.com /lab-diamond-engagement-rings/bezel-solitaire-148)
    # or a long alphanumeric record id (/diamond/<slug>-01t4m000004npejqam) also marks a product.
    # A three-digit suffix only counts when the path has two or more segments, so a price
    # facet like /wedding-bands-up-to-500 does not qualify.
    trailing_id = (bool(re.search(r"-\d{4,}(?:\.html?)?/?$", tail_l))
                   or (len(segs) >= 2 and bool(re.search(r"-\d{3}(?:\.html?)?/?$", tail_l)))
                   or bool(re.search(r"-[a-z0-9]{15,}/?$", tail_l)))
    # An .html ending alone is not enough: Salesforce Commerce Cloud category pages end in .html
    # too. Product pages on those platforms carry a SKU or numeric id (…/MTR1160.html,
    # …-CRB4232900.html, …-WR1118RPL.html), which has_sku and has_num_id cover.
    return long_slug and product_word and (has_num_id or has_sku or trailing_id)


def jsonld_item_urls(html: str, base: str) -> list[str]:
    """Product URLs from Product nodes or ItemList JSON-LD on a collection page.
    BreadcrumbList is skipped on purpose: its ListItems are category pages, and reading them
    made a dozen rows sample a category or an article instead of a product in an earlier run.
    A URL from a plain ItemList is kept only if the item is typed Product or the path looks
    like a product page."""
    urls = []
    for b in LDJSON_RE.findall(html or ""):
        data = try_json(unescape(b).strip())
        if data is None:
            continue
        nodes: list[dict] = []
        _walk(data, nodes)
        for n in nodes:
            t = n.get("@type")
            tl = [str(x) for x in (t if isinstance(t, list) else [t]) if x]
            if "Product" in tl or "ProductGroup" in tl:
                u = n.get("url") or n.get("@id")
                if isinstance(u, str) and u.startswith("http"):
                    urls.append((u, True))
            elif "ItemList" in tl and "BreadcrumbList" not in tl:
                for el in n.get("itemListElement") or []:
                    if not isinstance(el, dict):
                        continue
                    item = el.get("item")
                    typed_product = False
                    if isinstance(item, dict):
                        it = item.get("@type")
                        itl = [str(x) for x in (it if isinstance(it, list) else [it]) if x]
                        typed_product = "Product" in itl or "ProductGroup" in itl
                        u = item.get("url") or item.get("@id")
                    elif isinstance(item, str):
                        u = item
                    else:
                        u = el.get("url")
                    if isinstance(u, str) and u.startswith("http"):
                        urls.append((u, typed_product))
    out = []
    seen = set()
    for u, typed in urls:
        u = u.split("?")[0]
        path = urlparse(u).path
        if not _same_site(u, base) or u in seen or path.rstrip("/") == "":
            continue
        if typed or _is_product_path(path) or _is_product_path_heuristic(path):
            seen.add(u); out.append(u)
    return out


def find_product_links(html: str, base: str, heuristic: bool = False) -> list[str]:
    links = []
    for href in HREF_RE.findall(html or ""):
        href = unescape(href)
        if href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        u = urljoin(base, href)
        if not _same_site(u, base):
            continue
        path = urlparse(u).path
        if _is_product_path(path) or (heuristic and _is_product_path_heuristic(path)):
            links.append(u)
    # Prefer ring-ish product URLs, then Shopify-style /products/ URLs.
    def score(u: str) -> tuple:
        p = urlparse(u).path.lower()
        return (0 if any(w in p for w in PRODUCT_WORDS) else 1,
                0 if "/products/" in p else 1,
                len(p))
    seen = set()
    out = []
    for u in sorted(links, key=score):
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def find_collection_links(html: str, base: str) -> list[str]:
    """Collection or category pages on the same site, ring-ish ones sorted to the front."""
    links = []
    for href in HREF_RE.findall(html or ""):
        href = unescape(href)
        if href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        u = urljoin(base, href)
        if not _same_site(u, base):
            continue
        path = urlparse(u).path.lower()
        if path.endswith(NON_PAGE_EXT) or _is_product_path(path):
            continue
        if any(h in path for h in COLLECTION_HINTS) and path.strip("/"):
            links.append(u)
    def score(u: str) -> tuple:
        p = urlparse(u).path.lower()
        return (0 if "engagement" in p else 1, 0 if "ring" in p else 1, len(p))
    seen = set(); out = []
    for u in sorted(links, key=score):
        if u not in seen:
            seen.add(u); out.append(u)
    return out


SITEMAP_LOC_RE = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.IGNORECASE)


def product_from_sitemap(base: str, evidence: dict, heuristic: bool = False) -> str | None:
    """Strict pass (path hints or a sitemap the site itself named 'product'); the heuristic pass
    is only used as a late fallback because it is the noisiest picker."""
    if heuristic:
        cands = evidence.get("_sitemap_candidates") or []
        prods = [u for u in cands if _same_site(u, base) and _is_product_path_heuristic(urlparse(u).path)]
        if prods:
            evidence.setdefault("sitemap", {})["heuristic"] = True
            ringy = [u for u in prods if any(w in urlparse(u).path.lower() for w in PRODUCT_WORDS)]
            return (ringy or prods)[0]
        return None
    sm = fetch(urljoin(base, "/sitemap.xml"))
    evidence["sitemap"] = {"status": sm["status"], "bytes": sm["bytes"], "error": sm["error"]}
    if sm["status"] != 200 or not sm["text"]:
        return None
    locs = SITEMAP_LOC_RE.findall(sm["text"])
    if not locs:
        return None
    is_index = "<sitemapindex" in sm["text"].lower()
    candidates = []
    if is_index:
        child = None
        for loc in locs:
            if "product" in loc.lower():
                child = loc; break
        if child is None:
            child = locs[0]
        evidence["sitemap"]["child"] = child
        sm2 = fetch(child)
        evidence["sitemap"]["child_status"] = sm2["status"]
        if sm2["status"] == 200 and sm2["text"]:
            candidates = SITEMAP_LOC_RE.findall(sm2["text"])
    else:
        candidates = locs
    # Keep same-host URLs that look like product pages. If the sitemap the site itself named
    # "product" has no path hints (brilliantearth.com lists root-level slugs), trust the sitemap.
    evidence["_sitemap_candidates"] = candidates[:5000]
    prods = [u for u in candidates if _same_site(u, base) and _is_product_path(urlparse(u).path)]
    if not prods and is_index and "product" in (evidence["sitemap"].get("child") or "").lower():
        prods = [u for u in candidates if _same_site(u, base)
                 and not u.lower().endswith(NON_PAGE_EXT) and len(urlparse(u).path.strip("/")) > 12]
        if prods:
            evidence["sitemap"]["trusted_product_sitemap"] = True
    if not prods:
        return None
    ringy = [u for u in prods if any(w in urlparse(u).path.lower() for w in PRODUCT_WORDS)]
    return (ringy or prods)[0]


# ----------------------------------------------------------------------------
# MCP discovery (read-only)
# ----------------------------------------------------------------------------

def parse_sse_json(text: str):
    """Extract the last JSON payload from an SSE body."""
    last = None
    for line in (text or "").splitlines():
        if line.startswith("data:"):
            d = try_json(line[5:].strip())
            if d is not None:
                last = d
    return last


def mcp_handshake(url: str) -> dict:
    """POST initialize then tools/list. Read-only discovery. Returns tool names."""
    res = {"endpoint": url, "initialize_status": None, "initialize_ok": False,
           "server_info": None, "protocol_version": None, "tools_status": None,
           "tools": [], "error": None}
    hdrs = {"Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"}
    init = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18",
                       "capabilities": {},
                       "clientInfo": {"name": "stienhardt-agent-census", "version": "0.1"}}}
    r = fetch(url, method="POST", headers=hdrs, body=json.dumps(init).encode())
    res["initialize_status"] = r["status"]
    if r["error"]:
        res["error"] = r["error"]
        return res
    payload = try_json(r["text"]) if "json" in ctype(r) else parse_sse_json(r["text"])
    if payload is None:
        payload = try_json(r["text"]) or parse_sse_json(r["text"])
    sid = (r.get("headers") or {}).get("mcp-session-id")
    if isinstance(payload, dict) and isinstance(payload.get("result"), dict):
        res["initialize_ok"] = True
        res["server_info"] = payload["result"].get("serverInfo")
        res["protocol_version"] = payload["result"].get("protocolVersion")
    elif isinstance(payload, dict) and payload.get("error"):
        res["error"] = f"jsonrpc error: {str(payload.get('error'))[:200]}"
    if not res["initialize_ok"]:
        return res
    h2 = dict(hdrs)
    if sid:
        h2["Mcp-Session-Id"] = sid
    # notifications/initialized is optional for discovery; most servers accept tools/list directly.
    tl = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    r2 = fetch(url, method="POST", headers=h2, body=json.dumps(tl).encode())
    res["tools_status"] = r2["status"]
    p2 = try_json(r2["text"]) if "json" in ctype(r2) else parse_sse_json(r2["text"])
    if p2 is None:
        p2 = try_json(r2["text"]) or parse_sse_json(r2["text"])
    if isinstance(p2, dict) and isinstance(p2.get("result"), dict):
        tools = p2["result"].get("tools") or []
        res["tools"] = [t.get("name") for t in tools if isinstance(t, dict)][:50]
    return res


def mcp_like_get(resp: dict) -> bool:
    """Does a GET to /mcp look like an MCP endpoint rather than a web page?"""
    st = resp.get("status")
    ct = ctype(resp)
    txt = (resp.get("text") or "")
    if st in (405, 406, 415) and not looks_like_html(txt):
        return True
    if "text/event-stream" in ct:
        return True
    if "json" in ct and st in (200, 400, 401, 403, 404, 405, 406):
        j = try_json(txt)
        if isinstance(j, dict) and ("jsonrpc" in j or "error" in j or "tools" in j):
            return True
    if st in (400, 401) and "json" in ct:
        return True
    return False


# ----------------------------------------------------------------------------
# registry + chatgpt apps index
# ----------------------------------------------------------------------------

def slim_registry_entry(entry: dict) -> dict:
    """Keep only the fields the matcher reads, so the cached snapshot stays a few MB."""
    s = entry.get("server") or entry
    meta = ((entry.get("_meta") or {}).get("io.modelcontextprotocol.registry/official") or {})
    return {
        "server": {
            "name": s.get("name"),
            "title": s.get("title"),
            "description": s.get("description"),
            "version": s.get("version"),
            "websiteUrl": s.get("websiteUrl"),
            "repository": {"url": (s.get("repository") or {}).get("url")} if s.get("repository") else None,
            "remotes": [{"type": r.get("type"), "url": r.get("url")} for r in (s.get("remotes") or []) if isinstance(r, dict)],
        },
        "_meta": {"io.modelcontextprotocol.registry/official": {
            "status": meta.get("status"), "isLatest": meta.get("isLatest"),
            "publishedAt": meta.get("publishedAt"), "updatedAt": meta.get("updatedAt")}},
    }


def crawl_registry(force: bool = False) -> list[dict]:
    if os.path.exists(REGISTRY_SNAPSHOT) and not force:
        with open(REGISTRY_SNAPSHOT, encoding="utf-8") as f:
            snap = json.load(f)
        if isinstance(snap, dict) and "servers" in snap:
            return snap["servers"]
    servers: list[dict] = []
    cursor = None
    pages = 0
    while True:
        url = REGISTRY_BASE + "?limit=100" + (f"&cursor={cursor}" if cursor else "")
        r = fetch(url)
        if r["status"] != 200:
            print(f"[registry] page {pages} status {r['status']} error {r['error']}", file=sys.stderr)
            break
        j = try_json(r["text"]) or {}
        servers.extend(slim_registry_entry(e) for e in (j.get("servers") or []))
        pages += 1
        cursor = (j.get("metadata") or {}).get("nextCursor")
        if not cursor:
            break
        if pages > 400:  # hard stop
            break
    with open(REGISTRY_SNAPSHOT, "w", encoding="utf-8") as f:
        json.dump({"fetched_at": datetime.now(timezone.utc).isoformat(),
                   "pages": pages, "count": len(servers), "servers": servers}, f)
    return servers


def _label(domain: str) -> str:
    parts = domain.lower().split(".")
    return parts[-2] if len(parts) >= 2 else parts[0]


def registry_matches(domain: str, seller: str, servers: list[dict]) -> list[dict]:
    """Match a seller against the registry by domain in URLs, then by label in name/host."""
    d = domain.lower().replace("www.", "")
    label = _label(d)
    hits = []
    for entry in servers:
        s = entry.get("server") or entry
        name = str(s.get("name") or "")
        desc = str(s.get("description") or "")
        site = str(s.get("websiteUrl") or "")
        repo = str(((s.get("repository") or {}).get("url")) or "")
        remotes = " ".join(str(r.get("url") or "") for r in (s.get("remotes") or []))
        blob_urls = " ".join([site, repo, remotes]).lower()
        reason = None
        if d in blob_urls:
            reason = "domain-in-url"
        elif d in desc.lower():
            reason = "domain-in-description"
        else:
            # label match only in server name segments or URL hosts, whole token
            name_tokens = re.split(r"[./_\-\s]+", name.lower())
            hosts = [urlparse(u).netloc.lower() for u in re.findall(r"https?://[^\s\"']+", blob_urls)]
            host_tokens = []
            for h in hosts:
                host_tokens.extend(h.split("."))
            if len(label) >= 5 and (label in name_tokens or label in host_tokens):
                reason = "label-in-name-or-host"
        if reason:
            hits.append({"name": name, "reason": reason, "websiteUrl": site,
                         "remotes": [r.get("url") for r in (s.get("remotes") or [])],
                         "repository": repo,
                         "status": ((entry.get("_meta") or {}).get("io.modelcontextprotocol.registry/official") or {}).get("status"),
                         "isLatest": ((entry.get("_meta") or {}).get("io.modelcontextprotocol.registry/official") or {}).get("isLatest")})
    return hits


def registry_search(seller: str, domain: str = "") -> dict:
    """The registry's own ?search= endpoint, as a cross-check on the full-crawl match.
    Raw hits are name substring matches and include unrelated servers (a search for
    "Zales" returns "com.zaleso/tools"), so the domain-confirmed subset is reported too."""
    q = re.sub(r"\s*\(.*?\)\s*", " ", seller).strip()
    q = re.sub(r"[^A-Za-z0-9 &'.-]", "", q).strip()
    r = fetch(REGISTRY_BASE + "?search=" + (requests.utils.quote(q) if HAVE_REQUESTS else q.replace(" ", "%20")))
    j = try_json(r["text"]) or {}
    entries = j.get("servers") or []
    names = [((e.get("server") or {}).get("name")) for e in entries]
    d = domain.lower().replace("www.", "")
    confirmed = sorted({(e.get("server") or {}).get("name") for e in entries
                        if d and d in json.dumps(e.get("server") or {}).lower()})
    return {"query": q, "status": r["status"], "count": len(names), "names": names[:20],
            "domain_confirmed": confirmed}


def load_chatgpt_apps(force: bool = False) -> str | None:
    if os.path.exists(CHATGPT_APPS_README) and not force:
        with open(CHATGPT_APPS_README, encoding="utf-8") as f:
            return f.read()
    r = fetch(CHATGPT_APPS_URL)
    if r["status"] == 200 and r["text"]:
        with open(CHATGPT_APPS_README, "w", encoding="utf-8") as f:
            f.write(r["text"])
        return r["text"]
    print(f"[chatgpt-apps] unreachable: status {r['status']} error {r['error']}", file=sys.stderr)
    return None


def chatgpt_apps_match(domain: str, seller: str, readme: str | None) -> dict:
    if readme is None:
        return {"checked": False, "match": False, "lines": []}
    d = domain.lower().replace("www.", "")
    base_seller = re.sub(r"\s*\(.*?\)\s*", "", seller).strip()
    lines = []
    for line in readme.splitlines():
        if not line.startswith("- ["):
            continue
        ll = line.lower()
        m = re.match(r"- \[([^\]]+)\]\(([^)]+)\)", line)
        if not m:
            continue
        app_name, app_url = m.group(1), m.group(2)
        if d in app_url.lower():
            lines.append(line.strip()[:200]); continue
        if re.fullmatch(re.escape(base_seller.lower()), app_name.lower().strip()):
            lines.append(line.strip()[:200]); continue
    return {"checked": True, "match": bool(lines), "lines": lines[:5]}


# ----------------------------------------------------------------------------
# text-file classification (agents.md / llms.txt)
# ----------------------------------------------------------------------------

# Generator signatures. A file carrying one of these was produced by the platform or by an
# installed plugin from the catalog, not written by the merchant for agents. Such files are
# platform-inherited (Tier B) even when only one store in the sample has them.
GENERATOR_SIGNATURES = [
    # Shopify's auto-generated llms.txt ("# Store URL: ... Last Modified Time: ... Store Description: ...")
    ("shopify-llms", lambda t: t.lstrip("﻿").lower().startswith("# store url:") or
                               ("last modified time:" in t.lower()[:400] and "store description:" in t.lower()[:800])),
    # Shopify's auto-generated agents.md ("# Agent Instructions ... This document describes how AI agents can interact with")
    ("shopify-agents", lambda t: t.lstrip("﻿").lower().startswith("# agent instructions") and
                                 "this document describes how ai agents can interact with" in t.lower()[:600]),
    # Yoast SEO (WordPress) auto-generated llms.txt
    ("yoast-seo", lambda t: "generated by yoast seo" in t.lower()[:600]),
    # Other common generators that stamp themselves
    ("generic-generated", lambda t: bool(re.search(r"(?i)\bgenerated (?:by|with) [a-z0-9 .\-]{2,40}(?:plugin|app|seo|generator)", t[:800]))),
]


def detect_generator(text: str) -> str | None:
    for name, test in GENERATOR_SIGNATURES:
        try:
            if test(text or ""):
                return name
        except Exception:
            continue
    return None


def classify_textfile(resp: dict) -> dict:
    """Return kind in {absent, html_soft404, blocked, error, empty, real} plus fingerprint and generator."""
    out = {"status": resp.get("status"), "content_type": ctype(resp), "bytes": resp.get("bytes"),
           "kind": "absent", "snippet": "", "fingerprint": None, "generator": None, "error": resp.get("error")}
    if resp.get("error"):
        out["kind"] = "error"; return out
    st = resp.get("status")
    txt = resp.get("text") or ""
    if st in (401, 403, 429, 503):
        out["kind"] = "blocked"; out["snippet"] = snippet(txt, 160); return out
    if st != 200:
        return out
    if looks_like_html(txt):
        out["kind"] = "html_soft404"; out["snippet"] = snippet(re.sub(r"<[^>]+>", " ", txt), 160); return out
    if len(txt.strip()) < 80:
        out["kind"] = "empty"; out["snippet"] = snippet(txt, 160); return out
    out["kind"] = "real"
    out["snippet"] = snippet(txt, SNIPPET)
    out["fingerprint"] = structural_fingerprint(txt)
    out["generator"] = detect_generator(txt)
    out["line_count"] = txt.count("\n") + 1
    return out


def structural_fingerprint(txt: str) -> str:
    """Hash the structure of the leading 30 lines with URLs, digits and brand tokens removed.
    Identical fingerprints across unrelated stores indicate a platform or app template."""
    lines = []
    for line in txt.splitlines():
        s = line.strip()
        if not s:
            continue
        s = re.sub(r"https?://\S+", "<url>", s)
        s = re.sub(r"[A-Za-z0-9.-]+\.(com|co|net|org|shop|store)\b", "<host>", s)
        s = re.sub(r"\d+", "#", s)
        # keep only the leading structural token (heading marker, bullet, key:)
        m = re.match(r"^(#+\s*[A-Za-z ]{0,24}|[-*]\s*\[?|[A-Za-z _-]{1,24}:)", s)
        lines.append(m.group(1).strip().lower() if m else s[:12].lower())
        if len(lines) >= 30:
            break
    return hashlib.sha1("\n".join(lines).encode()).hexdigest()[:12]


# ----------------------------------------------------------------------------
# per-domain probe
# ----------------------------------------------------------------------------

def probe_domain(row: dict, servers: list[dict], readme: str | None) -> dict:
    domain = row["domain"].strip().lower()
    seller = row["seller"].strip()
    ev: dict = {"domain": domain, "seller": seller, "rank_source": row.get("rank_source", ""),
                "probed_at": datetime.now(timezone.utc).isoformat(), "fetches": {}}

    # 1. homepage (establish canonical base after redirects)
    home = fetch(f"https://{domain}/")
    if home["error"] and "SSL" in (home["error"] or ""):
        home = fetch(f"http://{domain}/")
    if home["error"] or home["status"] is None:
        # try www.
        alt = fetch(f"https://www.{domain}/")
        if not alt["error"]:
            home = alt
    base = home["final_url"] or f"https://{domain}/"
    pb = urlparse(base)
    netloc = pb.netloc
    if (pb.scheme == "https" and netloc.endswith(":443")) or (pb.scheme == "http" and netloc.endswith(":80")):
        netloc = netloc.rsplit(":", 1)[0]
    final_host = netloc.lower().replace("www.", "")
    # A homepage that lands on a bot-check host is a blocked fetch. Keep the seller's own domain
    # as the base for the remaining fetches so the evidence stays attached to the seller.
    wall_host = None
    if any(final_host == h or final_host.endswith("." + h) for h in BOT_WALL_HOSTS):
        wall_host = final_host
        base = f"https://{domain}/"
        netloc = domain
        final_host = domain.replace("www.", "")
    else:
        base = f"{pb.scheme}://{netloc}/"
    ev["base"] = base
    ev["final_host"] = final_host
    ev["bot_wall_host"] = wall_host
    # A redirect to a different registrable domain means the evidence below belongs to that
    # other site (jamesallen.com forwarded to bluenile.com with ?jaRedirect=true on 2026-09-02).
    ev["redirected_offsite"] = final_host != domain.replace("www.", "") and not final_host.endswith("." + domain.replace("www.", ""))
    ev["fetches"]["home"] = {"status": home["status"], "final_url": home["final_url"],
                             "content_type": ctype(home), "bytes": home["bytes"],
                             "error": home["error"], "elapsed_ms": home["elapsed_ms"],
                             "server": (home.get("headers") or {}).get("server"),
                             "bot_wall": (bot_wall(home) if home["status"] else False) or bool(wall_host),
                             "bot_wall_host": wall_host,
                             "snippet": snippet(re.sub(r"<[^>]+>", " ", home["text"] or ""), 200)}
    home_html = home["text"] or ""
    ev["home_jsonld"] = parse_jsonld(home_html)
    plat = detect_platform(home)
    ev["platform"] = plat

    # 2. robots.txt
    rb = fetch(urljoin(base, "/robots.txt"))
    robots_txt = rb["text"] if rb["status"] == 200 and not looks_like_html(rb["text"] or "") else ""
    blocked_bots = []
    if robots_txt:
        cur_agents: list[str] = []
        rules: dict[str, list[str]] = {}
        for line in robots_txt.splitlines():
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            k, _, v = line.partition(":")
            k = k.strip().lower(); v = v.strip()
            if k == "user-agent":
                cur_agents.append(v.lower()); rules.setdefault(v.lower(), [])
            elif k == "disallow" and cur_agents:
                for a in cur_agents:
                    rules[a].append(v)
            elif k in ("allow", "sitemap", "crawl-delay"):
                pass
            if k not in ("user-agent",) and k != "disallow" and k != "allow":
                cur_agents = cur_agents  # keep group
            if k == "" :
                cur_agents = []
        for bot in AI_BOTS:
            dis = rules.get(bot.lower())
            if dis and any(d.strip() == "/" for d in dis):
                blocked_bots.append(bot)
        star = rules.get("*") or []
        star_all = any(d.strip() == "/" for d in star)
    else:
        star_all = False
    ev["fetches"]["robots"] = {"status": rb["status"], "bytes": rb["bytes"], "error": rb["error"],
                               "ai_bots_fully_disallowed": blocked_bots, "wildcard_disallow_all": star_all,
                               "mentions_ai_bot": [b for b in AI_BOTS if b.lower() in robots_txt.lower()]}

    # 3. well-known and agent files
    ucp = fetch(urljoin(base, "/.well-known/ucp"))
    ucp_json = try_json(ucp["text"]) if ucp["status"] == 200 else None
    ucp_kind = "none"
    ucp_mcp = None
    ucp_summary = None
    if isinstance(ucp_json, dict):
        blob = json.dumps(ucp_json).lower()
        urls = re.findall(r"https?://[^\s\"']+", json.dumps(ucp_json))
        mcp_urls = [u for u in urls if "/mcp" in u.lower()]
        ucp_mcp = mcp_urls[0] if mcp_urls else None
        if "myshopify.com" in blob or "shopify" in blob:
            ucp_kind = "shopify_hosted"
        else:
            ucp_kind = "custom"
        ucp_summary = {"top_keys": list(ucp_json.keys())[:12], "urls": urls[:8],
                       "version": (ucp_json.get("ucp") or {}).get("version") if isinstance(ucp_json.get("ucp"), dict) else ucp_json.get("version")}
    elif ucp["status"] == 200 and not looks_like_html(ucp["text"] or ""):
        ucp_kind = "non_json_200"
    ev["fetches"]["ucp"] = {"status": ucp["status"], "content_type": ctype(ucp), "bytes": ucp["bytes"],
                            "error": ucp["error"], "kind": ucp_kind, "mcp_endpoint": ucp_mcp,
                            "summary": ucp_summary, "snippet": snippet(ucp["text"], 300) if ucp["status"] == 200 else ""}

    agents = classify_textfile(fetch(urljoin(base, "/agents.md")))
    llms = classify_textfile(fetch(urljoin(base, "/llms.txt")))
    ev["fetches"]["agents_md"] = agents
    ev["fetches"]["llms_txt"] = llms

    mcpwk = fetch(urljoin(base, "/.well-known/mcp.json"))
    mcpwk_json = try_json(mcpwk["text"]) if mcpwk["status"] == 200 else None
    mcpwk_endpoint = None
    if isinstance(mcpwk_json, (dict, list)):
        cands = [u for u in re.findall(r"https?://[^\s\"']+", json.dumps(mcpwk_json)) if "mcp" in u.lower()]
        # Prefer a URL that ends in /mcp (the transport) over documentation links that merely mention it.
        cands.sort(key=lambda u: (not u.rstrip("/").lower().endswith("/mcp"), "developers" in u.lower() or "docs" in u.lower()))
        mcpwk_endpoint = cands[0] if cands else None
    ev["fetches"]["mcp_wellknown"] = {"status": mcpwk["status"], "content_type": ctype(mcpwk),
                                      "is_json": mcpwk_json is not None, "endpoint": mcpwk_endpoint,
                                      "snippet": snippet(mcpwk["text"], 300) if mcpwk_json is not None else ""}

    mcpget = fetch(urljoin(base, "/mcp"), headers={"Accept": "application/json, text/event-stream"})
    mcp_like = mcp_like_get(mcpget) if not mcpget["error"] else False
    ev["fetches"]["mcp_get"] = {"status": mcpget["status"], "content_type": ctype(mcpget), "bytes": mcpget["bytes"],
                                "error": mcpget["error"], "mcp_like": mcp_like,
                                "snippet": snippet(mcpget["text"], 200) if not looks_like_html(mcpget["text"] or "") else "(html page)"}

    # ACP (OpenAI Agentic Commerce Protocol) checkout endpoint: GET only, strict evidence rule.
    acp = fetch(urljoin(base, "/checkout_sessions"))
    acp_like = False
    if not acp["error"] and acp["status"] in (400, 401, 403, 405, 415) and not looks_like_html(acp["text"] or "") and ("json" in ctype(acp) or acp["status"] == 405):
        acp_like = True
    ev["fetches"]["acp_checkout_sessions"] = {"status": acp["status"], "content_type": ctype(acp),
                                              "error": acp["error"], "acp_like": acp_like,
                                              "snippet": snippet(acp["text"], 160) if not looks_like_html(acp["text"] or "") else "(html page)"}

    # 4. read-only MCP handshakes on endpoints that advertise MCP: the site's own /mcp,
    #    a /.well-known/mcp.json declaration, the UCP profile's endpoint, and the remote URL of
    #    every latest active MCP Registry entry matched to this seller.
    ev["registry_matches"] = registry_matches(domain, seller, servers)
    handshakes = []
    targets = []
    if mcp_like:
        targets.append(("site_/mcp", urljoin(base, "/mcp")))
    if mcpwk_endpoint:
        targets.append(("well-known_mcp.json", mcpwk_endpoint))
    if ucp_mcp:
        targets.append(("ucp_profile", ucp_mcp))
    for m in ev["registry_matches"]:
        if m.get("isLatest") and m.get("status") == "active":
            for ru in m.get("remotes") or []:
                if isinstance(ru, str) and ru.startswith("http"):
                    targets.append((f"registry_remote:{m['name']}", ru))
    done_by_url: dict[str, dict] = {}
    for label, url in targets:
        if url in done_by_url:
            # Same endpoint reached by two routes: record it under both labels, handshake once.
            dup = dict(done_by_url[url])
            dup["source"] = label
            dup["duplicate_of"] = done_by_url[url]["source"]
            handshakes.append(dup)
            continue
        hs = mcp_handshake(url)
        hs["source"] = label
        done_by_url[url] = hs
        handshakes.append(hs)
    ev["mcp_handshakes"] = handshakes

    # 5. one product page: homepage links, then one collection page, then the sitemap, then guesses
    product_url = None
    disc = ev.setdefault("discovery", {})
    links = find_product_links(home_html, base)
    if links:
        product_url = links[0]; disc["method"] = "homepage_link"
    collection_pages: list[str] = []
    if not product_url:
        for coll in find_collection_links(home_html, base)[:2]:
            g = fetch(coll)
            disc.setdefault("collections_tried", []).append({"url": coll, "status": g["status"]})
            if g["status"] == 200 and g["text"]:
                collection_pages.append(g["text"])
                l2 = find_product_links(g["text"], base)
                if l2:
                    product_url = l2[0]; disc["method"] = "collection_link"; break
                l3 = jsonld_item_urls(g["text"], base)
                if l3:
                    product_url = l3[0]; disc["method"] = "collection_jsonld_itemlist"; break
    if not product_url:
        product_url = product_from_sitemap(base, disc)
        if product_url:
            disc["method"] = "sitemap"
    if not product_url:
        # Second pass over the collection pages already fetched, with the heuristic picker.
        for page in collection_pages:
            l4 = find_product_links(page, base, heuristic=True)
            if l4:
                product_url = l4[0]; disc["method"] = "collection_link_heuristic"; break
    if not product_url:
        l5 = find_product_links(home_html, base, heuristic=True)
        if l5:
            product_url = l5[0]; disc["method"] = "homepage_link_heuristic"
    if not product_url:
        product_url = product_from_sitemap(base, disc, heuristic=True)
        if product_url:
            disc["method"] = "sitemap_heuristic"
    disc.pop("_sitemap_candidates", None)
    if not product_url:
        for guess in ("/collections/engagement-rings", "/engagement-rings", "/collections/all"):
            g = fetch(urljoin(base, guess))
            if g["status"] == 200 and g["text"]:
                l2 = find_product_links(g["text"], base) or find_product_links(g["text"], base, heuristic=True)
                if l2:
                    product_url = l2[0]; disc["method"] = "guessed_collection"; break
    prod = None
    if product_url:
        prod = fetch(product_url)
        ev["fetches"]["product"] = {"url": product_url, "status": prod["status"], "final_url": prod["final_url"],
                                    "content_type": ctype(prod), "bytes": prod["bytes"], "error": prod["error"],
                                    "bot_wall": bot_wall(prod) if prod["status"] else False}
        ev["product_jsonld"] = parse_jsonld(prod["text"] or "")
        if plat["platform"] is None:
            plat2 = detect_platform(home, prod["text"] or "")
            if plat2["platform"]:
                ev["platform"] = plat2
    else:
        ev["fetches"]["product"] = {"url": None, "status": None, "error": "no product url discovered"}
        ev["product_jsonld"] = {"blocks": 0, "parsed": 0, "types": [], "has_product": False,
                                "has_offer": False, "gtin": False, "mpn": False, "sku": False}

    # 6. registry ?search= cross-check (matches were computed in step 4) and chatgpt apps index
    ev["registry_search"] = registry_search(seller, domain)
    ev["chatgpt_apps"] = chatgpt_apps_match(domain, seller, readme)
    return ev


# ----------------------------------------------------------------------------
# classification (second pass, needs the whole population for template detection)
# ----------------------------------------------------------------------------

def classify_all(results: list[dict]) -> None:
    # Template detection: any structural fingerprint shared by 3+ distinct domains is a template.
    fp_count: dict[str, set] = {}
    for ev in results:
        for key in ("agents_md", "llms_txt"):
            f = ev["fetches"].get(key) or {}
            if f.get("kind") == "real" and f.get("fingerprint"):
                fp_count.setdefault((key, f["fingerprint"]), set()).add(ev["domain"])
    templates = {k for k, v in fp_count.items() if len(v) >= 3}

    for ev in results:
        F = ev["fetches"]
        a_reasons: list[str] = []
        b_reasons: list[str] = []
        home = F.get("home") or {}
        home_ok = home.get("status") == 200 and not home.get("bot_wall")
        blocked = bool(home.get("bot_wall")) or home.get("status") in (403, 429, 503)
        prod = F.get("product") or {}
        if prod.get("bot_wall"):
            blocked = True

        # Tier A evidence
        if ev.get("registry_matches"):
            a_reasons.append("mcp_registry:" + ",".join(sorted({m["name"] for m in ev["registry_matches"]})[:3]))
        for hs in ev.get("mcp_handshakes") or []:
            if hs.get("initialize_ok") and hs.get("source") in ("site_/mcp", "well-known_mcp.json"):
                a_reasons.append(f"custom_mcp:{hs['source']}:{len(hs.get('tools') or [])}tools")
        if (F.get("mcp_wellknown") or {}).get("is_json"):
            a_reasons.append("well-known_mcp.json")
        for key in ("agents_md", "llms_txt"):
            f = F.get(key) or {}
            if f.get("kind") == "real":
                if f.get("generator"):
                    f["template"] = True
                    b_reasons.append(f"{key}:generated:{f['generator']}")
                elif (key, f.get("fingerprint")) in templates:
                    f["template"] = True
                    b_reasons.append(f"{key}:platform_template")
                else:
                    f["template"] = False
                    a_reasons.append(f"{key}:real")
        if (F.get("acp_checkout_sessions") or {}).get("acp_like"):
            a_reasons.append("acp_checkout_sessions")
        ucp = F.get("ucp") or {}
        if ucp.get("kind") == "custom":
            a_reasons.append("ucp:custom")

        # Tier B evidence
        if ucp.get("kind") == "shopify_hosted":
            b_reasons.append("ucp:shopify_hosted")
            live = any(h.get("initialize_ok") for h in (ev.get("mcp_handshakes") or []) if h.get("source") == "ucp_profile")
            if live:
                b_reasons.append("ucp_mcp_live")
        pj = ev.get("product_jsonld") or {}
        hj = ev.get("home_jsonld") or {}
        if pj.get("has_product") or hj.get("has_product"):
            b_reasons.append("schema_product_jsonld")
        elif pj.get("has_offer") or hj.get("has_offer"):
            b_reasons.append("schema_offer_jsonld")

        # Third bucket follows the brief's label: "unreachable" means unreachable FOR AN AGENT
        # (none of the Tier A or Tier B evidence), not that the website is down. The separate
        # blocked_automated_fetch and site_loaded flags say which kind it is.
        if a_reasons:
            tier = "A"
        elif b_reasons:
            tier = "B"
        else:
            tier = "unreachable"
        ev["tier"] = tier
        ev["tier_a_reasons"] = a_reasons
        ev["tier_b_reasons"] = b_reasons
        ev["blocked_automated_fetch"] = blocked
        ev["home_ok"] = home_ok


def summary_row(ev: dict) -> dict:
    F = ev["fetches"]
    pj = ev.get("product_jsonld") or {}
    hs = ev.get("mcp_handshakes") or []
    ucp_live = next((h for h in hs if h.get("source") == "ucp_profile"), None)
    custom_hs = [h for h in hs if h.get("source") in ("site_/mcp", "well-known_mcp.json")]
    reg_hs = [h for h in hs if str(h.get("source") or "").startswith("registry_remote:")]
    return {
        "domain": ev["domain"],
        "seller": ev["seller"],
        "rank_source": ev.get("rank_source", ""),
        "tier": ev["tier"],
        "home_status": F["home"].get("status"),
        "final_host": ev.get("final_host") or "",
        "redirected_offsite": bool(ev.get("redirected_offsite")),
        "site_loaded": ev["home_ok"],
        "blocked_automated_fetch": ev["blocked_automated_fetch"],
        "bot_wall_host": ev.get("bot_wall_host") or "",
        "home_error": F["home"].get("error") or "",
        "platform": (ev.get("platform") or {}).get("platform"),
        "platform_signals": ";".join((ev.get("platform") or {}).get("signals") or []),
        "checkout_shopify": (ev.get("platform") or {}).get("checkout_shopify"),
        "ucp_status": F["ucp"].get("status"),
        "ucp_kind": F["ucp"].get("kind"),
        "ucp_mcp_live": bool(ucp_live and ucp_live.get("initialize_ok")),
        "ucp_mcp_tools": ";".join(ucp_live.get("tools") or []) if ucp_live else "",
        "agents_md": F["agents_md"].get("kind") + (":template" if F["agents_md"].get("template") else ""),
        "llms_txt": F["llms_txt"].get("kind") + (":template" if F["llms_txt"].get("template") else ""),
        "mcp_get_status": F["mcp_get"].get("status"),
        "mcp_get_like": F["mcp_get"].get("mcp_like"),
        "mcp_wellknown_json": F["mcp_wellknown"].get("is_json"),
        "custom_mcp_initialized": any(h.get("initialize_ok") for h in custom_hs),
        "custom_mcp_tools": ";".join(t for h in custom_hs for t in (h.get("tools") or [])),
        "registry_remote_live": any(h.get("initialize_ok") for h in reg_hs),
        "registry_remote_endpoints": ";".join(sorted({h.get("endpoint") or "" for h in reg_hs if h.get("initialize_ok")})),
        "registry_remote_tools": ";".join(t for h in reg_hs if h.get("initialize_ok") and not h.get("duplicate_of") for t in (h.get("tools") or [])),
        "acp_checkout_endpoint": F["acp_checkout_sessions"].get("acp_like"),
        "registry_match": bool(ev.get("registry_matches")),
        "registry_server_names": ";".join(sorted({m["name"] for m in ev.get("registry_matches") or []})),
        "registry_search_hits": (ev.get("registry_search") or {}).get("count"),
        "registry_search_domain_confirmed": ";".join((ev.get("registry_search") or {}).get("domain_confirmed") or []),
        "agents_md_generator": F["agents_md"].get("generator") or "",
        "llms_txt_generator": F["llms_txt"].get("generator") or "",
        "chatgpt_apps_checked": (ev.get("chatgpt_apps") or {}).get("checked"),
        "chatgpt_apps_match": (ev.get("chatgpt_apps") or {}).get("match"),
        "product_url": (F.get("product") or {}).get("url"),
        "product_status": (F.get("product") or {}).get("status"),
        "product_discovery": (ev.get("discovery") or {}).get("method"),
        "product_jsonld": pj.get("has_product"),
        "product_jsonld_offer": pj.get("has_offer"),
        "product_jsonld_gtin": pj.get("gtin"),
        "product_jsonld_mpn": pj.get("mpn"),
        "product_jsonld_gtin_or_mpn": bool(pj.get("gtin") or pj.get("mpn")),
        "product_jsonld_repaired": bool(pj.get("repaired")),
        "product_jsonld_malformed": bool(pj.get("malformed_product")),
        "robots_ai_bots_disallowed": ";".join(F["robots"].get("ai_bots_fully_disallowed") or []),
        "tier_a_reasons": ";".join(ev["tier_a_reasons"]),
        "tier_b_reasons": ";".join(ev["tier_b_reasons"]),
    }


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Agent-Shoppable Census probe")
    ap.add_argument("--domains", default=DOMAINS_CSV)
    ap.add_argument("--only", help="comma separated domains to probe; results are merged into the "
                                   "existing probe-results.jsonl unless --no-merge is given")
    ap.add_argument("--no-merge", action="store_true", help="with --only, write only the probed rows")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--refresh-registry", action="store_true", help="re-crawl the MCP registry")
    ap.add_argument("--refresh-chatgpt-apps", action="store_true")
    args = ap.parse_args()

    started = datetime.now(timezone.utc)
    os.makedirs(DATA, exist_ok=True)
    with open(args.domains, encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))
    rows = all_rows
    previous: dict[str, dict] = {}
    if args.only:
        keep = {d.strip().lower() for d in args.only.split(",")}
        rows = [r for r in all_rows if r["domain"].strip().lower() in keep]
        if not args.no_merge and os.path.exists(RESULTS_JSONL):
            with open(RESULTS_JSONL, encoding="utf-8") as f:
                for line in f:
                    try:
                        ev = json.loads(line)
                        previous[ev["domain"]] = ev
                    except Exception:
                        continue
    print(f"[census] {len(rows)} domains; requests lib: {HAVE_REQUESTS}; started {started.isoformat()}")

    print("[census] crawling MCP registry ...")
    servers = crawl_registry(force=args.refresh_registry)
    print(f"[census] registry servers: {len(servers)}")
    readme = load_chatgpt_apps(force=args.refresh_chatgpt_apps)
    print(f"[census] chatgpt apps index: {'loaded' if readme else 'UNREACHABLE (skipped)'}")

    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(probe_domain, r, servers, readme): r for r in rows}
        done = 0
        for fut in as_completed(futs):
            r = futs[fut]
            done += 1
            try:
                ev = fut.result()
            except Exception as e:  # keep going, record the crash
                ev = {"domain": r["domain"], "seller": r["seller"], "rank_source": r.get("rank_source", ""),
                      "probed_at": datetime.now(timezone.utc).isoformat(), "crash": f"{type(e).__name__}: {e}",
                      "fetches": {"home": {"status": None, "error": str(e)}, "robots": {}, "ucp": {}, "agents_md": {"kind": "error"},
                                  "llms_txt": {"kind": "error"}, "mcp_wellknown": {}, "mcp_get": {}, "acp_checkout_sessions": {}},
                      "product_jsonld": {}, "home_jsonld": {}, "mcp_handshakes": [], "registry_matches": [], "platform": {}}
            results.append(ev)
            print(f"[{done:3d}/{len(rows)}] {ev['domain']:28s} home={ (ev['fetches'].get('home') or {}).get('status')} "
                  f"ucp={(ev['fetches'].get('ucp') or {}).get('kind')} agents={(ev['fetches'].get('agents_md') or {}).get('kind')} "
                  f"llms={(ev['fetches'].get('llms_txt') or {}).get('kind')} reg={len(ev.get('registry_matches') or [])}")

    # Merge re-probed rows into the previous full run (each row keeps its own probed_at).
    if previous:
        fresh = {e["domain"]: e for e in results}
        merged = []
        for r in all_rows:
            d = r["domain"].strip().lower()
            if d in fresh:
                merged.append(fresh[d])
            elif d in previous:
                merged.append(previous[d])
        results = merged
        rows = all_rows
    # keep the CSV order
    order = {r["domain"].strip().lower(): i for i, r in enumerate(rows)}
    results.sort(key=lambda e: order.get(e["domain"], 999))
    classify_all(results)

    with open(RESULTS_JSONL, "w", encoding="utf-8") as f:
        for ev in results:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    srows = [summary_row(ev) for ev in results]
    with open(SUMMARY_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(srows[0].keys()))
        w.writeheader()
        w.writerows(srows)

    finished = datetime.now(timezone.utc)
    counts = {}
    for ev in results:
        counts[ev["tier"]] = counts.get(ev["tier"], 0) + 1
    prev_meta = {}
    if previous and os.path.exists(RUN_META):
        try:
            prev_meta = json.load(open(RUN_META, encoding="utf-8"))
        except Exception:
            prev_meta = {}
    meta = {"started_utc": prev_meta.get("started_utc", started.isoformat()),
            "finished_utc": prev_meta.get("finished_utc", finished.isoformat()),
            "reprobes": (prev_meta.get("reprobes") or []) + ([{"domains": sorted(fresh.keys()), "at_utc": finished.isoformat()}] if previous else []),
            "domains": len(results), "counts": counts, "registry_servers": len(servers),
            "chatgpt_apps_index_loaded": readme is not None,
            "probe_version": PROBE_VERSION,
            "user_agent": USER_AGENT, "per_host_interval_s": PER_HOST_INTERVAL, "timeout_s": TIMEOUT}
    with open(RUN_META, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print("[census] done", json.dumps(meta))
    return 0


if __name__ == "__main__":
    sys.exit(main())
