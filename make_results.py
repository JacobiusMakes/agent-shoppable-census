#!/usr/bin/env python3
"""
Render RESULTS-DRAFT.md from data/probe-summary.csv and data/run-meta.json.

A monthly rerun is two commands:

    python probe.py
    python make_results.py            # writes RESULTS-DRAFT.md (use --stdout to print instead)

Everything in the results file comes from the run outputs plus the fixed
methodology text below. No em dashes are emitted.

License: MIT (see LICENSE-MIT).
"""

from __future__ import annotations

import csv
import io
import json
import os
import sys
from collections import Counter
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
SUMMARY = os.path.join(DATA, "probe-summary.csv")
META = os.path.join(DATA, "run-meta.json")
RESULTS = os.path.join(DATA, "probe-results.jsonl")
OUT = os.path.join(HERE, "RESULTS-DRAFT.md")

INTRO = """# Agent-Shoppable Census: results draft

Can an AI agent buy a ring here?

A census of 100 of the largest US online sellers of engagement rings and diamond
jewelry, probed for agent-readiness and split into two tiers so that Shopify's
default-on features do not inflate the count. Published by Stienhardt
(stienhardt.com), which is one of the 100 rows and is flagged as the publisher
wherever it appears. Tables and text: CC BY 4.0. Script: MIT. See README.md.

Draft status: this is the output of a single run on the date below. Numbers
change as sellers ship things; rerun `python probe.py` and
`python make_results.py` to regenerate every table from scratch.
"""

METHOD = """## Methodology, in plain language

**Who is in the list.** 100 domains in `data/domains.csv`. They come from
National Jeweler's 2026 "State of the Majors" rankings (the $100 Million
Supersellers and the Top 50 Specialty Jewelers by store count), the Semrush and
Similarweb public category pages for US jewelry and luxury websites (July 2026),
the aggregate jewelry pages of Digital Commerce 360's Top 1000 (the ranked list
itself is paywalled), three editorial round-ups of places to buy engagement
rings online, the sellers named in the census brief, and well-known US online
engagement ring sellers added to reach 100. Marketplaces, general merchandisers,
watch-only and fashion-only sellers, insurers, and sellers with no US operation
are excluded; JTV, a jewelry-only television and online retailer that sells
diamond and engagement rings online, is included. Every source URL and its
access date is listed in README.md and below. No public page ranks online engagement ring sellers by web sales, so
"largest" is a best public-source approximation and the file order is by source
tier, not a precise size order.

**What the probe fetches.** For each domain, with an honest User-Agent, a 15
second timeout, and at most one request per second per host: the homepage,
`/robots.txt`, `/.well-known/ucp`, `/agents.md`, `/llms.txt`,
`/.well-known/mcp.json`, `/mcp` (GET), `/checkout_sessions` (GET), and one
product page found from homepage links, then one collection page, then the
sitemap. Nothing is POSTed except a JSON-RPC `initialize` and `tools/list` to
endpoints that advertise MCP; both are read-only discovery calls. The probe never
creates a cart, a checkout, a session, or an account.

**How a row is classified.** Tier A (merchant-built) needs at least one thing the
seller itself published for agents: an entry in the official MCP Registry
(matched by the seller's domain in the server's website, remote, or repository
URL, or by the domain label in the server name), a live custom MCP endpoint, an
`agents.md` or `llms.txt` with real content that is not a shared template, an
ACP checkout endpoint, or a UCP profile the merchant hosts itself. Tier B
(platform-inherited) means the only signals are ones the platform gives every
store: a Shopify-hosted UCP profile (the JSON points at `myshopify.com`), an
`agents.md` or `llms.txt` whose structure is shared by three or more unrelated
stores in the sample, or schema.org Product or Offer JSON-LD emitted by the
theme. "Unreachable" follows the brief's label and means unreachable for an
agent: none of the above. Two flags say why: `site_loaded` and
`blocked_automated_fetch`. A row with any Tier A evidence is Tier A even when
it also has Tier B evidence; both reason lists are printed.

**What "real content" means for agents.md and llms.txt.** HTTP 200, not an HTML
page (many sites serve their 404 page with a 200 status), at least 80
characters, and a structural fingerprint (headings, bullets, keys, with URLs,
numbers, and brand names removed) that is not shared by three or more other
domains in the run. Files that share a fingerprint are counted as a platform or
app template and land in Tier B.

**The MCP Registry check.** The full registry (`/v0/servers`, cursor-paged, 100
per page) is crawled once per run and cached. Each seller is matched against
every entry, and the registry's own `?search=<seller name>` endpoint is queried
as a second check; both results are in the evidence file. For every latest,
active registry entry matched to a seller that declares a remote URL, the probe
also sends the same read-only `initialize` and `tools/list` to that remote and
records whether it answered and which tools it listed.

**The ChatGPT Apps check.** The community-maintained index at
github.com/rdmgator12/awesome-chatgpt-apps (a mirror of OpenAI's directory
listings) is downloaded and matched by seller name or domain. It is not OpenAI's
directory itself. If the index cannot be downloaded the column is marked
unchecked and the run continues.

## Caveats, every one we know of

* **Default-on Shopify features inflate naive counts.** Every Shopify store in
  the sample can expose a hosted UCP profile with a working MCP endpoint that
  answers `search_catalog` and `create_checkout` without the merchant lifting a
  finger. Counting those as "agent-ready merchants" would be misleading. They
  are Tier B here, reported separately, and the live MCP handshake result is
  recorded so nobody has to take our word for it.
* **One product page per site.** Found automatically, from the homepage, a
  collection page, or the sitemap. "No GTIN or MPN" means none on that page.
  The sampled product is sometimes earrings or a band rather than an engagement
  ring; the JSON-LD test does not care, but a reader might. The sampled URL is
  in `data/probe-summary.csv` for every row.
* **Some sites block fetchers.** A 403, 429, or 503, or a bot-wall page, to our
  User-Agent is recorded as `blocked_automated_fetch`. Those rows are
  Unreachable. That is what a plain-HTTP agent would see; it does not prove the
  seller has nothing behind the wall.
* **Client-side rendering.** Several large storefronts deliver product data by
  JavaScript. Server-delivered HTML without Product JSON-LD is recorded as no
  JSON-LD, because that is what a non-browser agent receives.
* **Malformed JSON-LD.** Some themes emit Product JSON-LD that a strict parser
  rejects (a trailing comma, a raw control character in a description). The
  probe retries such blocks after repairing those two defects and flags the row
  `product_jsonld_repaired`; a block that still fails is flagged
  `product_jsonld_malformed` and is not counted as present. Both counts are in
  the signal table so nobody has to guess which rows they are.
* **ACP feeds are private.** OpenAI's Agentic Commerce Protocol product feeds are
  submitted to OpenAI, not published. Only a public `/checkout_sessions`
  endpoint is probed, with a strict rule (a JSON or 405 answer, not a web page).
* **Registry matching is by domain.** A seller whose MCP server is registered
  under a name and URLs that never mention its domain would be missed by the
  automatic match. The `?search=` count is printed alongside as a cross-check.
* **Template detection needs company.** A platform template used by only one or
  two stores in the sample would not be recognized as a template and would be
  counted as real content. The fingerprint is stored per row so this can be
  audited.
* **Shopify detection.** "shopify" means theme or header signals on the
  storefront; "shopify-referenced" means a `<shop>.myshopify.com` hostname
  appears in the page scripts but the storefront itself shows no Shopify theme
  or headers (headless, partial, or a dev store). Only the former is treated as
  a Shopify checkout.
* **Silent connection drops.** Some hosts never complete a connection to our
  fetcher: the TCP or TLS handshake times out with no HTTP status at all. That is
  recorded in `home_error`, the row is Unreachable with `site_loaded` false, and
  `blocked_automated_fetch` stays false because a timeout is consistent with
  edge-level bot filtering but is not proof of it.
* **Bot-check redirects.** A homepage that redirects to a known bot-check host
  (for example `validate.perfdrive.com`) is recorded as `blocked_automated_fetch`
  with the host in `bot_wall_host`; the seller's own domain is kept as the base
  for the remaining fetches so the evidence stays attached to the seller.
* **Point in time.** The run timestamps are printed above. Anything a seller
  shipped after that is not in this table.

## Sources for the domain list (accessed 2026-09-02, re-checked 2026-09-03)

* National Jeweler, "$100 Million Supersellers", State of the Majors 2026 edition (fiscal 2025 sales; 37 companies):
  https://nationaljeweler.com/ranks/sotm_100_mill
* National Jeweler, "Top 50 Specialty Jewelers", State of the Majors 2026 edition (store counts as of 2025-12-31; 51 companies):
  https://nationaljeweler.com/ranks/sotm_top_50
* Semrush, Top websites, US, Jewelry and Luxury Products, July 2026 (top 20 visible):
  https://www.semrush.com/trending-websites/us/jewelry-and-luxury-products
* Similarweb, Top websites, US, Lifestyle, Jewelry and Luxury Products, July 2026 (top 5 visible):
  https://www.similarweb.com/top-websites/united-states/lifestyle/jewelry-and-luxury-products/
* Digital Commerce 360, jewelry category pages (aggregate figures only; ranked list paywalled):
  https://www.digitalcommerce360.com/jewelry-ecommerce-statistics/ and
  https://www.digitalcommerce360.com/article/jewelry-top-5-online-merchants/
* Diamonds.pro, "Best Places To Buy Diamond Engagement Ring", updated 2026-06-12:
  https://www.diamonds.pro/education/best-place-buy-engagement-ring/
* Reviewed.com, "15 best places to buy engagement rings online", updated 2025-01-30:
  https://www.reviewed.com/style/features/best-places-to-buy-engagement-rings-online
* Pompeii3, "12 Best Places to Buy Engagement Rings Online in 2026", 2026-05-06 (a seller's own list, corroboration only):
  https://www.pompeii3.com/blog/12-best-places-to-buy-engagement-rings-online-in-2026/
* Could not be read by our tooling on 2026-09-02 (HTTP 403 or paywall): Forbes Vetted's engagement ring and diamond buying guides, Brillianteers' lab-grown buying guide, Digital Commerce 360's ranked jewelry list.
* JCK (jckonline.com), searched 2026-09-02 and 2026-09-03: JCK reports on other bodies' rankings (for example Signet's placement on the NRF Top 100) but publishes no ranked list of online jewelers that we could find, so no domain carries a JCK source code.

Other public endpoints used by the probe: the official MCP Registry
(https://registry.modelcontextprotocol.io/v0/servers) and the community ChatGPT
Apps index (https://github.com/rdmgator12/awesome-chatgpt-apps).
"""


def yn(v: str) -> str:
    return "yes" if str(v) == "True" else ""


def short_reason(reason: str) -> str:
    """Turn a machine reason into a short human label."""
    if reason.startswith("mcp_registry:"):
        return "MCP Registry entry (" + reason.split(":", 1)[1] + ")"
    if reason.startswith("custom_mcp:"):
        return "live custom MCP endpoint"
    if reason == "well-known_mcp.json":
        return "/.well-known/mcp.json"
    if reason == "agents_md:real":
        return "agents.md"
    if reason == "llms_txt:real":
        return "llms.txt"
    if reason == "acp_checkout_sessions":
        return "ACP /checkout_sessions endpoint"
    if reason == "ucp:custom":
        return "merchant-hosted UCP profile"
    if reason == "ucp:shopify_hosted":
        return "Shopify-hosted UCP profile"
    if reason == "ucp_mcp_live":
        return "Shopify UCP MCP endpoint answers tools/list"
    if reason.endswith(":platform_template"):
        return reason.split(":")[0].replace("_", ".") + " (platform template)"
    if reason == "schema_product_jsonld":
        return "Product JSON-LD"
    if reason == "schema_offer_jsonld":
        return "Offer JSON-LD"
    if ":generated:" in reason:
        key, gen = reason.split(":generated:")
        label = {"shopify-llms": "Shopify auto-generated", "shopify-agents": "Shopify auto-generated",
                 "yoast-seo": "Yoast SEO plugin generated"}.get(gen, gen + " generated")
        return key.replace("_", ".") + " (" + label + ")"
    return reason


def redirect_note(r: dict) -> str:
    if r.get("redirected_offsite") == "True" and r.get("final_host"):
        return f" (domain forwards to {r['final_host']})"
    return ""


def main() -> None:
    to_stdout = "--stdout" in sys.argv
    buf = io.StringIO()
    with redirect_stdout(buf):
        render()
    text = buf.getvalue()
    assert "\u2014" not in text, "em dash in output"
    if to_stdout:
        sys.stdout.write(text)
    else:
        with open(OUT, "w", encoding="utf-8") as f:
            f.write(text)
        sys.stderr.write(f"wrote {OUT} ({len(text)} chars)\n")


def render() -> None:
    with open(SUMMARY, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    meta = json.load(open(META, encoding="utf-8")) if os.path.exists(META) else {}
    print(INTRO)

    counts = Counter(r["tier"] for r in rows)
    blocked = [r for r in rows if r["blocked_automated_fetch"] == "True"]
    unreach = [r for r in rows if r["tier"] == "unreachable"]
    unreach_blocked = [r for r in unreach if r["blocked_automated_fetch"] == "True"]
    unreach_not_loaded = [r for r in unreach if r["blocked_automated_fetch"] != "True" and r["site_loaded"] != "True"]
    unreach_nothing = [r for r in unreach if r["blocked_automated_fetch"] != "True" and r["site_loaded"] == "True"]
    shopify = [r for r in rows if r["platform"] == "shopify"]
    shopify_ref = [r for r in rows if r["platform"] == "shopify-referenced"]
    ucp_shop = [r for r in rows if r["ucp_kind"] == "shopify_hosted"]
    ucp_live = [r for r in rows if r["ucp_mcp_live"] == "True"]
    ucp_custom = [r for r in rows if r["ucp_kind"] == "custom"]
    llms_real = [r for r in rows if r["llms_txt"] == "real"]
    agents_real = [r for r in rows if r["agents_md"] == "real"]
    llms_tpl = [r for r in rows if r["llms_txt"].endswith(":template")]
    agents_tpl = [r for r in rows if r["agents_md"].endswith(":template")]
    registry = [r for r in rows if r["registry_match"] == "True"]
    custom_mcp = [r for r in rows if r["custom_mcp_initialized"] == "True"]
    reg_live = [r for r in rows if r.get("registry_remote_live") == "True"]
    acp = [r for r in rows if r["acp_checkout_endpoint"] == "True"]
    chatgpt = [r for r in rows if r["chatgpt_apps_match"] == "True"]
    chatgpt_checked = [r for r in rows if r["chatgpt_apps_checked"] == "True"]
    prod_sampled = [r for r in rows if r["product_status"] == "200"]
    prod_jsonld = [r for r in rows if r["product_jsonld"] == "True"]
    prod_ids = [r for r in rows if r["product_jsonld_gtin_or_mpn"] == "True"]
    prod_repaired = [r for r in rows if r.get("product_jsonld_repaired") == "True"]
    prod_malformed = [r for r in rows if r.get("product_jsonld_malformed") == "True"]
    robots_block = [r for r in rows if r["robots_ai_bots_disallowed"]]

    print("## Run")
    print()
    print(f"* Started (UTC): {meta.get('started_utc', 'n/a')}")
    print(f"* Finished (UTC): {meta.get('finished_utc', 'n/a')}")
    print(f"* Domains probed: {len(rows)}")
    for rp in meta.get("reprobes") or []:
        print(f"* Re-probed after the run, at {rp.get('at_utc')} (UTC): {', '.join(rp.get('domains') or [])} (each row's own `probed_at` is in the evidence file)")
    print(f"* MCP Registry servers scanned: {meta.get('registry_servers', 'n/a')}")
    print(f"* Probe version: {meta.get('probe_version', 'n/a')}")
    print(f"* ChatGPT Apps index loaded: {'yes' if meta.get('chatgpt_apps_index_loaded') else 'no, column skipped'}")
    print(f"* User-Agent: `{meta.get('user_agent', '')}`")
    print()
    print("## Counts")
    print()
    print("| Bucket | Domains |")
    print("|---|---:|")
    print(f"| Tier A (merchant-built) | {counts.get('A', 0)} |")
    print(f"| Tier B (platform-inherited only) | {counts.get('B', 0)} |")
    print(f"| Unreachable for an agent | {len(unreach)} |")
    print(f"| of which blocked automated fetch (403/429/503 or bot wall) | {len(unreach_blocked)} |")
    print(f"| of which loaded fine but exposed nothing agent-facing | {len(unreach_nothing)} |")
    print(f"| of which did not load at all (DNS, TLS, timeout) | {len(unreach_not_loaded)} |")
    print()
    print(f"Sites that refused the fetcher in any bucket (including Tier A or B rows reached via other signals): {len(blocked)}.")
    print()
    print(f"## Signal counts across all {len(rows)}")
    print()
    print("| Signal | Domains |")
    print("|---|---:|")
    print(f"| Storefront served by Shopify (theme or header signals) | {len(shopify)} |")
    print(f"| Shopify store referenced by page scripts only (headless, partial, or dev store) | {len(shopify_ref)} |")
    print(f"| Shopify-hosted /.well-known/ucp present | {len(ucp_shop)} |")
    print(f"| Shopify UCP MCP endpoint answered initialize + tools/list | {len(ucp_live)} |")
    print(f"| Merchant-hosted (non-Shopify) UCP profile | {len(ucp_custom)} |")
    print(f"| llms.txt with real, non-template content | {len(llms_real)} |")
    print(f"| agents.md with real, non-template content | {len(agents_real)} |")
    print(f"| llms.txt matching a shared template | {len(llms_tpl)} |")
    print(f"| agents.md matching a shared template | {len(agents_tpl)} |")
    print(f"| Entry in the official MCP Registry | {len(registry)} |")
    print(f"| Live custom MCP endpoint (/mcp or .well-known/mcp.json) | {len(custom_mcp)} |")
    print(f"| Registry-listed remote endpoint answered initialize + tools/list | {len(reg_live)} |")
    print(f"| ACP /checkout_sessions endpoint | {len(acp)} |")
    print(f"| Listed in the community ChatGPT Apps index (of {len(chatgpt_checked)} checked) | {len(chatgpt)} |")
    print(f"| Product page sampled successfully (HTTP 200) | {len(prod_sampled)} |")
    print(f"| Sampled product page has Product JSON-LD | {len(prod_jsonld)} |")
    print(f"| Sampled product page has Product JSON-LD with GTIN or MPN | {len(prod_ids)} |")
    print(f"| of the pages with JSON-LD, blocks that parsed only after repairing a trailing comma or control character | {len(prod_repaired)} |")
    print(f"| Sampled product page has a Product JSON-LD block that does not parse even after repair (not counted as present) | {len(prod_malformed)} |")
    print(f"| robots.txt fully disallows at least one named AI crawler | {len(robots_block)} |")
    print()

    print("## Tier A: merchant-built")
    print()
    print("| Seller | Domain | What the seller built | Also inherits |")
    print("|---|---|---|---|")
    for r in rows:
        if r["tier"] != "A":
            continue
        built = "; ".join(short_reason(x) for x in r["tier_a_reasons"].split(";") if x)
        if r.get("registry_remote_live") == "True":
            built += "; registered remote endpoint answered tools/list"
        inh = "; ".join(short_reason(x) for x in r["tier_b_reasons"].split(";") if x)
        name = r["seller"] + (" (publisher of this census)" if r["rank_source"] == "PUBLISHER" else "")
        print(f"| {name} | {r['domain']}{redirect_note(r)} | {built} | {inh} |")
    print()
    print("### Tier A, one line each")
    print()
    for r in rows:
        if r["tier"] != "A":
            continue
        parts = []
        for x in r["tier_a_reasons"].split(";"):
            if not x:
                continue
            if x.startswith("mcp_registry:"):
                s = "an entry in the official MCP Registry (" + x.split(":", 1)[1] + ")"
                if r.get("registry_remote_live") == "True":
                    eps = [e for e in (r.get("registry_remote_endpoints") or "").split(";") if e]
                    s += " whose registered remote endpoint answered our initialize and tools/list (" + ", ".join(eps) + ")"
                parts.append(s)
            elif x.startswith("custom_mcp:"):
                n = r["custom_mcp_tools"].count(";") + (1 if r["custom_mcp_tools"] else 0)
                parts.append(f"a live custom MCP endpoint exposing {n} tools" + (f" ({r['custom_mcp_tools'].replace(';', ', ')})" if r["custom_mcp_tools"] else ""))
            elif x == "well-known_mcp.json":
                parts.append("a /.well-known/mcp.json file")
            elif x == "agents_md:real":
                parts.append("an agents.md")
            elif x == "llms_txt:real":
                parts.append("an llms.txt")
            elif x == "acp_checkout_sessions":
                parts.append("an ACP /checkout_sessions endpoint")
            elif x == "ucp:custom":
                parts.append("a merchant-hosted UCP profile")
        extra = ""
        if r["ucp_kind"] == "shopify_hosted":
            extra = " It also carries the Shopify-hosted UCP profile" + (" whose MCP endpoint answered our tools/list." if r["ucp_mcp_live"] == "True" else ".")
        pub = " (publisher of this census)" if r["rank_source"] == "PUBLISHER" else ""
        print(f"* **{r['seller']}{pub}** ({r['domain']}) published " + ", ".join(parts) + "." + extra)
    print()

    print("## Tier B: platform-inherited only")
    print()
    print("| Seller | Domain | Platform | Inherited signals |")
    print("|---|---|---|---|")
    for r in rows:
        if r["tier"] != "B":
            continue
        inh = "; ".join(short_reason(x) for x in r["tier_b_reasons"].split(";") if x)
        print(f"| {r['seller']} | {r['domain']}{redirect_note(r)} | {r['platform'] or 'not identified'} | {inh} |")
    print()

    print("## Unreachable for an agent")
    print()
    print("| Seller | Domain | Homepage status | Blocked automated fetch | Note |")
    print("|---|---|---|---|---|")
    for r in rows:
        if r["tier"] != "unreachable":
            continue
        if r["blocked_automated_fetch"] == "True":
            note = "site refused the fetcher" + (f" (redirected to bot-check host {r['bot_wall_host']})" if r.get("bot_wall_host") else "")
        elif r["site_loaded"] == "True":
            note = "site loaded; no agent-facing files, no UCP, no Product JSON-LD on the sampled page"
        else:
            err = (r.get("home_error") or "").split(":", 1)[0]
            why = {"ConnectTimeout": "connection timed out", "ReadTimeout": "read timed out",
                   "ConnectionError": "connection failed or was reset", "SSLError": "TLS failure",
                   "ConnectTimeoutError": "connection timed out"}.get(err, err or "no response")
            note = f"site did not load ({why})"
        print(f"| {r['seller']} | {r['domain']}{redirect_note(r)} | {r['home_status'] or 'none'} | {yn(r['blocked_automated_fetch'])} | {note} |")
    print()

    print("## Full table")
    print()
    print("| # | Seller | Domain | Tier | Platform | Shopify checkout | UCP | agents.md | llms.txt | MCP Registry | Custom MCP | ACP | ChatGPT Apps | Product JSON-LD | GTIN/MPN | AI crawlers disallowed |")
    print("|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(rows, 1):
        ucp = {"shopify_hosted": "Shopify-hosted", "custom": "merchant", "none": "", "non_json_200": "non-JSON 200"}.get(r["ucp_kind"], r["ucp_kind"])
        if r["ucp_kind"] == "shopify_hosted" and r["ucp_mcp_live"] == "True":
            ucp += " (MCP live)"
        a = r["agents_md"].replace("html_soft404", "").replace("absent", "").replace("blocked", "blocked").replace("error", "").replace("empty", "")
        l = r["llms_txt"].replace("html_soft404", "").replace("absent", "").replace("blocked", "blocked").replace("error", "").replace("empty", "")
        print(f"| {i} | {r['seller']} | {r['domain']}{redirect_note(r)} | {r['tier']} | {r['platform'] or ''} | {yn(r['checkout_shopify'])} | {ucp} | {a} | {l} | {yn(r['registry_match'])} | {yn(r['custom_mcp_initialized'])} | {yn(r['acp_checkout_endpoint'])} | {yn(r['chatgpt_apps_match'])} | {yn(r['product_jsonld'])} | {yn(r['product_jsonld_gtin_or_mpn'])} | {r['robots_ai_bots_disallowed'].replace(';', ', ')} |")
    print()
    print("Column notes: \"Shopify checkout\" is set only when the storefront shows Shopify theme or header signals. "
          "\"UCP\" says who hosts the /.well-known/ucp profile. agents.md and llms.txt show \"real\" for merchant content, "
          "\"real:template\" for a shared template, \"blocked\" when the site refused the fetch, and blank when absent or a soft 404. "
          "\"Product JSON-LD\" and \"GTIN/MPN\" refer to the one sampled product page (URL in data/probe-summary.csv). "
          "\"MCP Registry\" is a match in the official registry; whether the matched entry's remote endpoint answered a read-only tools/list is in the Tier A table and in the registry_remote_live column of the CSV.")
    print()
    print(METHOD)


if __name__ == "__main__":
    main()
