# Agent-Shoppable Census: results draft

Can an AI agent buy a ring here?

A census of 100 of the largest US online sellers of engagement rings and diamond
jewelry, probed for agent-readiness and split into two tiers so that Shopify's
default-on features do not inflate the count. Published by Stienhardt
(stienhardt.com), which is one of the 100 rows and is flagged as the publisher
wherever it appears. Tables and text: CC BY 4.0. Script: MIT. See README.md.

Draft status: this is the output of a single run on the date below. Numbers
change as sellers ship things; rerun `python probe.py` and
`python make_results.py` to regenerate every table from scratch.

## Run

* Started (UTC): 2026-09-03T14:53:06.509914+00:00
* Finished (UTC): 2026-09-03T15:13:20.996712+00:00
* Domains probed: 100
* Re-probed after the run, at 2026-09-04T17:35:26.070508+00:00 (UTC): stienhardt.com (each row's own `probed_at` is in the evidence file)
* MCP Registry servers scanned: 40100
* Probe version: 0.2
* ChatGPT Apps index loaded: yes
* User-Agent: `StienhardtAgentCensus/0.2 (read-only agent-readiness census; +https://stienhardt.com/agents.md)`

## Counts

| Bucket | Domains |
|---|---:|
| Tier A (merchant-built) | 18 |
| Tier B (platform-inherited only) | 52 |
| Unreachable for an agent | 30 |
| of which blocked automated fetch (403/429/503 or bot wall) | 11 |
| of which loaded fine but exposed nothing agent-facing | 17 |
| of which did not load at all (DNS, TLS, timeout) | 2 |

Sites that refused the fetcher in any bucket (including Tier A or B rows reached via other signals): 12.

## Signal counts across all 100

| Signal | Domains |
|---|---:|
| Storefront served by Shopify (theme or header signals) | 38 |
| Shopify store referenced by page scripts only (headless, partial, or dev store) | 2 |
| Shopify-hosted /.well-known/ucp present | 34 |
| Shopify UCP MCP endpoint answered initialize + tools/list | 34 |
| Merchant-hosted (non-Shopify) UCP profile | 2 |
| llms.txt with real, non-template content | 18 |
| agents.md with real, non-template content | 2 |
| llms.txt matching a shared template | 33 |
| agents.md matching a shared template | 31 |
| Entry in the official MCP Registry | 2 |
| Live custom MCP endpoint (/mcp or .well-known/mcp.json) | 1 |
| Registry-listed remote endpoint answered initialize + tools/list | 2 |
| ACP /checkout_sessions endpoint | 0 |
| Listed in the community ChatGPT Apps index (of 100 checked) | 0 |
| Product page sampled successfully (HTTP 200) | 71 |
| Sampled product page has Product JSON-LD | 56 |
| Sampled product page has Product JSON-LD with GTIN or MPN | 23 |
| of the pages with JSON-LD, blocks that parsed only after repairing a trailing comma or control character | 3 |
| Sampled product page has a Product JSON-LD block that does not parse even after repair (not counted as present) | 1 |
| robots.txt fully disallows at least one named AI crawler | 8 |

## Tier A: merchant-built

| Seller | Domain | What the seller built | Also inherits |
|---|---|---|---|
| Kay Jewelers (Signet) | kay.com | llms.txt |  |
| Zales (Signet) | zales.com | llms.txt |  |
| Jared (Signet) | jared.com | llms.txt |  |
| Brilliant Earth | brilliantearth.com | llms.txt | Product JSON-LD |
| Ross-Simons (Nonantum Capital Partners) | ross-simons.com | llms.txt | agents.md (Shopify auto-generated); Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list; Product JSON-LD |
| VRAI (Diamond Foundry) | vrai.com | llms.txt | Product JSON-LD |
| Grown Brilliance | grownbrilliance.com | llms.txt |  |
| Ada Diamonds | adadiamonds.com | MCP Registry entry (com.adadiamonds/ada-diamonds); live custom MCP endpoint; /.well-known/mcp.json; agents.md; llms.txt; merchant-hosted UCP profile; registered remote endpoint answered tools/list | Offer JSON-LD |
| Rare Carat | rarecarat.com | llms.txt | Product JSON-LD |
| Whiteflash | whiteflash.com | llms.txt | Product JSON-LD |
| Angara | angara.com | llms.txt | Product JSON-LD |
| Pompeii3 | pompeii3.com | llms.txt; merchant-hosted UCP profile |  |
| Gabriel & Co. | gabrielny.com | llms.txt | Product JSON-LD |
| SuperJeweler | superjeweler.com | llms.txt |  |
| Lang Antique & Estate Jewelry | langantiques.com | llms.txt | Product JSON-LD |
| Borsheims | borsheims.com | llms.txt | Product JSON-LD |
| London Jewelers | londonjewelers.com | llms.txt |  |
| Stienhardt (publisher of this census) | stienhardt.com | MCP Registry entry (io.github.JacobiusMakes/diamond-mcp,io.github.JacobiusMakes/stienhardt-store); agents.md; llms.txt; registered remote endpoint answered tools/list | Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list; Product JSON-LD |

### Tier A, one line each

* **Kay Jewelers (Signet)** (kay.com) published an llms.txt.
* **Zales (Signet)** (zales.com) published an llms.txt.
* **Jared (Signet)** (jared.com) published an llms.txt.
* **Brilliant Earth** (brilliantearth.com) published an llms.txt.
* **Ross-Simons (Nonantum Capital Partners)** (ross-simons.com) published an llms.txt. It also carries the Shopify-hosted UCP profile whose MCP endpoint answered our tools/list.
* **VRAI (Diamond Foundry)** (vrai.com) published an llms.txt.
* **Grown Brilliance** (grownbrilliance.com) published an llms.txt.
* **Ada Diamonds** (adadiamonds.com) published an entry in the official MCP Registry (com.adadiamonds/ada-diamonds) whose registered remote endpoint answered our initialize and tools/list (https://www.adadiamonds.com/mcp), a live custom MCP endpoint exposing 8 tools (search_diamonds, search_engagement_rings, search_jewelry, search_knowledge_base, read_article, get_company_info, create_checkout_link, request_consultation), a /.well-known/mcp.json file, an agents.md, an llms.txt, a merchant-hosted UCP profile.
* **Rare Carat** (rarecarat.com) published an llms.txt.
* **Whiteflash** (whiteflash.com) published an llms.txt.
* **Angara** (angara.com) published an llms.txt.
* **Pompeii3** (pompeii3.com) published an llms.txt, a merchant-hosted UCP profile.
* **Gabriel & Co.** (gabrielny.com) published an llms.txt.
* **SuperJeweler** (superjeweler.com) published an llms.txt.
* **Lang Antique & Estate Jewelry** (langantiques.com) published an llms.txt.
* **Borsheims** (borsheims.com) published an llms.txt.
* **London Jewelers** (londonjewelers.com) published an llms.txt.
* **Stienhardt (publisher of this census)** (stienhardt.com) published an entry in the official MCP Registry (io.github.JacobiusMakes/diamond-mcp,io.github.JacobiusMakes/stienhardt-store) whose registered remote endpoint answered our initialize and tools/list (https://diamond-mcp.stienhardt.workers.dev/mcp, https://stienhard-stones.myshopify.com/api/ucp/mcp), an agents.md, an llms.txt. It also carries the Shopify-hosted UCP profile whose MCP endpoint answered our tools/list.

## Tier B: platform-inherited only

| Seller | Domain | Platform | Inherited signals |
|---|---|---|---|
| Blue Nile (Signet) | bluenile.com | not identified | Product JSON-LD |
| James Allen (Signet) | jamesallen.com (domain forwards to bluenile.com) | not identified | Product JSON-LD |
| Helzberg Diamonds | helzberg.com | salesforce-commerce-cloud | Product JSON-LD |
| Ben Bridge Jeweler | benbridge.com | salesforce-commerce-cloud | Product JSON-LD |
| Mejuri | mejuri.com | shopify | Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list; Product JSON-LD |
| Diamonds International (Almod Diamonds) | diamondsinternational.com | shopify | agents.md (Shopify auto-generated); llms.txt (Shopify auto-generated); Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list; Product JSON-LD |
| Daniel's Jewelers (Sherwood Management) | danielsjewelers.com | shopify | agents.md (Shopify auto-generated); llms.txt (Shopify auto-generated); Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list; Product JSON-LD |
| Rogers & Hollands (Rogers Enterprises) | rogersandhollands.com | salesforce-commerce-cloud | Product JSON-LD |
| Cartier (Richemont) | cartier.com | salesforce-commerce-cloud | Product JSON-LD |
| David Yurman | davidyurman.com | salesforce-commerce-cloud | Product JSON-LD |
| Mayors (Watches of Switzerland Group) | mayors.com | sap-commerce | Product JSON-LD |
| Shane Co. | shaneco.com | not identified | Product JSON-LD |
| Robbins Brothers | robbinsbrothers.com | magento | Product JSON-LD |
| Riddle's Jewelry | riddlesjewelry.com | shopify | agents.md (Shopify auto-generated); llms.txt (Shopify auto-generated); Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list; Product JSON-LD |
| Hannoush Jewelers | hannoush.com | shopify | agents.md (Shopify auto-generated); llms.txt (Shopify auto-generated); Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list; Product JSON-LD |
| Jensen Jewelers | jensenjewelers.com | woocommerce | llms.txt (Yoast SEO plugin generated) |
| Harry Ritchie's Jewelers | harryritchies.com | shopify | agents.md (Shopify auto-generated); llms.txt (Shopify auto-generated); Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list; Product JSON-LD |
| Fink's Jewelers | finks.com | shopify | agents.md (Shopify auto-generated); llms.txt (Shopify auto-generated); Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list; Product JSON-LD |
| The Jewelry Exchange (Goldenwest Diamond Corp.) | jewelryexchange.com | woocommerce | llms.txt (Yoast SEO plugin generated); Product JSON-LD |
| International Diamond Center | shopidc.com | shopify | agents.md (Shopify auto-generated); llms.txt (Shopify auto-generated); Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list; Product JSON-LD |
| Michaels Jewelers (The Michaels Group) | michaelsjewelers.com | shopify | agents.md (Shopify auto-generated); llms.txt (Shopify auto-generated); Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list |
| Schiffman's Jewelers (The Schiffman Group) | schiffmans.com | shopify | agents.md (Shopify auto-generated); llms.txt (Shopify auto-generated); Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list; Product JSON-LD |
| With Clarity | withclarity.com | shopify | agents.md (Shopify auto-generated); llms.txt (Shopify auto-generated); Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list; Product JSON-LD |
| Adiamor | adiamor.com | not identified | Product JSON-LD |
| Allurez | allurez.com | shopify | agents.md (Shopify auto-generated); llms.txt (Shopify auto-generated); Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list; Product JSON-LD |
| Catbird | catbirdnyc.com | not identified | Product JSON-LD |
| Brian Gavin Diamonds | briangavindiamonds.com | shopify | agents.md (Shopify auto-generated); llms.txt (Shopify auto-generated); Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list; Product JSON-LD |
| Leibish & Co. | leibish.com | shopify | agents.md (Shopify auto-generated); llms.txt (Shopify auto-generated); Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list; Product JSON-LD |
| The Clear Cut | theclearcut.co | shopify | agents.md (Shopify auto-generated); llms.txt (Shopify auto-generated); Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list; Product JSON-LD |
| Melanie Casey | melaniecasey.com | shopify | agents.md (Shopify auto-generated); llms.txt (Shopify auto-generated); Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list; Product JSON-LD |
| Stag & Finch | stagandfinch.com | shopify | agents.md (Shopify auto-generated); llms.txt (Shopify auto-generated); Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list; Product JSON-LD |
| Keyzar Jewelry | keyzarjewelry.com | shopify | Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list |
| Jean Dousset | jeandousset.com | shopify | agents.md (Shopify auto-generated); llms.txt (Shopify auto-generated); Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list; Product JSON-LD |
| Tacori | tacori.com | shopify | Product JSON-LD |
| Hearts On Fire | heartsonfire.com | salesforce-commerce-cloud | Product JSON-LD |
| Ring Concierge | ringconcierge.com | shopify | agents.md (Shopify auto-generated); llms.txt (Shopify auto-generated); Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list |
| Anna Sheffield | annasheffield.com | shopify | agents.md (Shopify auto-generated); llms.txt (Shopify auto-generated); Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list; Product JSON-LD |
| AUrate New York | auratenewyork.com | shopify | agents.md (Shopify auto-generated); llms.txt (Shopify auto-generated); Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list; Product JSON-LD |
| Kobelli | kobelli.com | shopify | agents.md (Shopify auto-generated); llms.txt (Shopify auto-generated); Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list; Product JSON-LD |
| MiaDonna | miadonna.com | shopify | agents.md (Shopify auto-generated); llms.txt (Shopify auto-generated); Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list; Product JSON-LD |
| Do Amore | doamore.com | shopify-referenced | Product JSON-LD |
| Bario Neal | barioneal.com (domain forwards to bario-neal.com) | woocommerce | llms.txt (Yoast SEO plugin generated); Product JSON-LD |
| Marrow Fine | marrowfine.com | shopify | agents.md (Shopify auto-generated); llms.txt (Shopify auto-generated); Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list; Product JSON-LD |
| Ken & Dana Design | kenanddanadesign.com | shopify | agents.md (Shopify auto-generated); llms.txt (Shopify auto-generated); Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list; Product JSON-LD |
| EraGem | eragem.com | magento | Product JSON-LD |
| Tapper's | tappers.com | shopify | agents.md (Shopify auto-generated); llms.txt (Shopify auto-generated); Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list; Product JSON-LD |
| Day's Jewelers | daysjewelers.com | shopify | agents.md (Shopify auto-generated); llms.txt (Shopify auto-generated); Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list; Product JSON-LD |
| Long's Jewelers | longsjewelers.com | shopify | agents.md (Shopify auto-generated); llms.txt (Shopify auto-generated); Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list; Product JSON-LD |
| Mervis Diamond Importers | mervisdiamond.com | shopify | agents.md (Shopify auto-generated); llms.txt (Shopify auto-generated); Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list |
| Steven Singer Jewelers | stevensingerjewelers.com (domain forwards to ihatestevensinger.com) | shopify | agents.md (Shopify auto-generated); llms.txt (Shopify auto-generated); Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list; Product JSON-LD |
| Greenwich St. Jewelers | greenwichjewelers.com | shopify | agents.md (Shopify auto-generated); llms.txt (Shopify auto-generated); Shopify-hosted UCP profile; Shopify UCP MCP endpoint answers tools/list |
| De Beers Jewellers | debeers.com | salesforce-commerce-cloud | Product JSON-LD |

## Unreachable for an agent

| Seller | Domain | Homepage status | Blocked automated fetch | Note |
|---|---|---|---|---|
| Diamonds Direct (Signet) | diamondsdirect.com | 200 |  | site loaded; no agent-facing files, no UCP, no Product JSON-LD on the sampled page |
| Reeds Jewelers | reeds.com | 200 |  | site loaded; no agent-facing files, no UCP, no Product JSON-LD on the sampled page |
| Fred Meyer Jewelers | fredmeyerjewelers.com | none |  | site did not load (connection timed out) |
| Don Roberto Jewelers | donrobertojewelers.com | 403 | yes | site refused the fetcher |
| Tiffany & Co. (LVMH) | tiffany.com | 403 | yes | site refused the fetcher |
| Van Cleef & Arpels (Richemont) | vancleefarpels.com | none |  | site did not load (read timed out) |
| Bulgari (LVMH) | bulgari.com | 403 | yes | site refused the fetcher |
| Harry Winston (Swatch Group) | harrywinston.com | 200 |  | site loaded; no agent-facing files, no UCP, no Product JSON-LD on the sampled page |
| Boucheron (Kering) | boucheron.com | 200 |  | site loaded; no agent-facing files, no UCP, no Product JSON-LD on the sampled page |
| JTV (Multimedia Commerce Group) | jtv.com | 200 |  | site loaded; no agent-facing files, no UCP, no Product JSON-LD on the sampled page |
| Morgan Jewelers (Morgan Management) | morganjewelers.com | 200 |  | site loaded; no agent-facing files, no UCP, no Product JSON-LD on the sampled page |
| Saslow's Jewelers (S. Saslow Inc.) | saslows.com | 200 |  | site loaded; no agent-facing files, no UCP, no Product JSON-LD on the sampled page |
| DeVons Jewelers | devonsjewelers.com | 200 |  | site loaded; no agent-facing files, no UCP, no Product JSON-LD on the sampled page |
| Lee Michaels Fine Jewelry | lmfj.com | 403 | yes | site refused the fetcher |
| Ritani | ritani.com | 403 | yes | site refused the fetcher |
| Clean Origin | cleanorigin.com | 403 | yes | site refused the fetcher |
| Abe Mor | abemor.com | 200 |  | site loaded; no agent-facing files, no UCP, no Product JSON-LD on the sampled page |
| Olive Ave Jewelry | oliveavejewelry.com | 200 |  | site loaded; no agent-facing files, no UCP, no Product JSON-LD on the sampled page |
| Jewelry by Johan | jewelrybyjohan.com | 403 | yes | site refused the fetcher |
| Frank Darling | frankdarling.com | 200 |  | site loaded; no agent-facing files, no UCP, no Product JSON-LD on the sampled page |
| Verragio | verragio.com | 429 | yes | site refused the fetcher |
| Kwiat | kwiat.com | 403 | yes | site refused the fetcher |
| Noemie | noemie.com | 200 |  | site loaded; no agent-facing files, no UCP, no Product JSON-LD on the sampled page |
| Brilliance | brilliance.com | 403 | yes | site refused the fetcher |
| Szul | szul.com | 200 |  | site loaded; no agent-facing files, no UCP, no Product JSON-LD on the sampled page |
| Lumera Diamonds | lumeradiamonds.com | 200 |  | site loaded; no agent-facing files, no UCP, no Product JSON-LD on the sampled page |
| Graff | graff.com | 200 |  | site loaded; no agent-facing files, no UCP, no Product JSON-LD on the sampled page |
| Chopard | chopard.com | 200 |  | site loaded; no agent-facing files, no UCP, no Product JSON-LD on the sampled page |
| Lauren B | laurenb.com (domain forwards to laurenbjewelry.com) | 403 | yes | site refused the fetcher |
| Bernie Robbins Jewelers | bernierobbins.com | 200 |  | site loaded; no agent-facing files, no UCP, no Product JSON-LD on the sampled page |

## Full table

| # | Seller | Domain | Tier | Platform | Shopify checkout | UCP | agents.md | llms.txt | MCP Registry | Custom MCP | ACP | ChatGPT Apps | Product JSON-LD | GTIN/MPN | AI crawlers disallowed |
|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Kay Jewelers (Signet) | kay.com | A |  |  |  |  | real |  |  |  |  |  |  |  |
| 2 | Zales (Signet) | zales.com | A |  |  |  |  | real |  |  |  |  |  |  |  |
| 3 | Jared (Signet) | jared.com | A |  |  |  |  | real |  |  |  |  |  |  |  |
| 4 | Blue Nile (Signet) | bluenile.com | B |  |  |  |  |  |  |  |  |  | yes | yes |  |
| 5 | James Allen (Signet) | jamesallen.com (domain forwards to bluenile.com) | B |  |  |  |  |  |  |  |  |  | yes | yes |  |
| 6 | Diamonds Direct (Signet) | diamondsdirect.com | unreachable | bigcommerce |  |  |  |  |  |  |  |  |  |  |  |
| 7 | Brilliant Earth | brilliantearth.com | A | shopify-referenced |  |  |  | real |  |  |  |  | yes | yes |  |
| 8 | Helzberg Diamonds | helzberg.com | B | salesforce-commerce-cloud |  |  |  |  |  |  |  |  | yes | yes |  |
| 9 | Ben Bridge Jeweler | benbridge.com | B | salesforce-commerce-cloud |  |  |  |  |  |  |  |  | yes | yes |  |
| 10 | Reeds Jewelers | reeds.com | unreachable | magento |  |  |  | blocked |  |  |  |  |  |  |  |
| 11 | Mejuri | mejuri.com | B | shopify | yes | Shopify-hosted (MCP live) |  |  |  |  |  |  | yes |  | GPTBot |
| 12 | Diamonds International (Almod Diamonds) | diamondsinternational.com | B | shopify | yes | Shopify-hosted (MCP live) | real:template | real:template |  |  |  |  | yes |  |  |
| 13 | Fred Meyer Jewelers | fredmeyerjewelers.com | unreachable |  |  |  |  |  |  |  |  |  |  |  |  |
| 14 | Daniel's Jewelers (Sherwood Management) | danielsjewelers.com | B | shopify | yes | Shopify-hosted (MCP live) | real:template | real:template |  |  |  |  | yes |  |  |
| 15 | Don Roberto Jewelers | donrobertojewelers.com | unreachable |  |  |  | blocked | blocked |  |  |  |  |  |  | GPTBot, ChatGPT-User, OAI-SearchBot, ClaudeBot, PerplexityBot |
| 16 | Rogers & Hollands (Rogers Enterprises) | rogersandhollands.com | B | salesforce-commerce-cloud |  |  |  |  |  |  |  |  | yes | yes |  |
| 17 | Tiffany & Co. (LVMH) | tiffany.com | unreachable |  |  |  | blocked | blocked |  |  |  |  |  |  |  |
| 18 | Cartier (Richemont) | cartier.com | B | salesforce-commerce-cloud |  |  |  |  |  |  |  |  | yes | yes |  |
| 19 | Van Cleef & Arpels (Richemont) | vancleefarpels.com | unreachable |  |  |  |  |  |  |  |  |  |  |  |  |
| 20 | Bulgari (LVMH) | bulgari.com | unreachable |  |  |  | blocked | blocked |  |  |  |  |  |  |  |
| 21 | Harry Winston (Swatch Group) | harrywinston.com | unreachable |  |  |  |  |  |  |  |  |  |  |  |  |
| 22 | Boucheron (Kering) | boucheron.com | unreachable |  |  |  |  |  |  |  |  |  |  |  |  |
| 23 | David Yurman | davidyurman.com | B | salesforce-commerce-cloud |  |  |  |  |  |  |  |  | yes | yes |  |
| 24 | Mayors (Watches of Switzerland Group) | mayors.com | B | sap-commerce |  |  |  |  |  |  |  |  | yes | yes |  |
| 25 | JTV (Multimedia Commerce Group) | jtv.com | unreachable |  |  |  |  |  |  |  |  |  |  |  |  |
| 26 | Ross-Simons (Nonantum Capital Partners) | ross-simons.com | A | shopify | yes | Shopify-hosted (MCP live) | real:template | real |  |  |  |  | yes |  |  |
| 27 | Shane Co. | shaneco.com | B |  |  |  |  |  |  |  |  |  | yes |  |  |
| 28 | Robbins Brothers | robbinsbrothers.com | B | magento |  |  |  |  |  |  |  |  | yes | yes |  |
| 29 | Riddle's Jewelry | riddlesjewelry.com | B | shopify | yes | Shopify-hosted (MCP live) | real:template | real:template |  |  |  |  | yes |  |  |
| 30 | Hannoush Jewelers | hannoush.com | B | shopify | yes | Shopify-hosted (MCP live) | real:template | real:template |  |  |  |  | yes | yes |  |
| 31 | Morgan Jewelers (Morgan Management) | morganjewelers.com | unreachable |  |  |  |  |  |  |  |  |  |  |  |  |
| 32 | Jensen Jewelers | jensenjewelers.com | B | woocommerce |  |  |  | real:template |  |  |  |  |  |  |  |
| 33 | Harry Ritchie's Jewelers | harryritchies.com | B | shopify | yes | Shopify-hosted (MCP live) | real:template | real:template |  |  |  |  | yes |  |  |
| 34 | Saslow's Jewelers (S. Saslow Inc.) | saslows.com | unreachable |  |  |  |  |  |  |  |  |  |  |  |  |
| 35 | Fink's Jewelers | finks.com | B | shopify | yes | Shopify-hosted (MCP live) | real:template | real:template |  |  |  |  | yes |  |  |
| 36 | The Jewelry Exchange (Goldenwest Diamond Corp.) | jewelryexchange.com | B | woocommerce |  |  |  | real:template |  |  |  |  | yes |  |  |
| 37 | International Diamond Center | shopidc.com | B | shopify | yes | Shopify-hosted (MCP live) | real:template | real:template |  |  |  |  | yes |  | GPTBot, ClaudeBot, Google-Extended, CCBot, Bytespider, Applebot-Extended, meta-externalagent |
| 38 | Michaels Jewelers (The Michaels Group) | michaelsjewelers.com | B | shopify | yes | Shopify-hosted (MCP live) | real:template | real:template |  |  |  |  |  |  |  |
| 39 | DeVons Jewelers | devonsjewelers.com | unreachable |  |  |  |  |  |  |  |  |  |  |  |  |
| 40 | Lee Michaels Fine Jewelry | lmfj.com | unreachable |  |  |  | blocked | blocked |  |  |  |  |  |  |  |
| 41 | Schiffman's Jewelers (The Schiffman Group) | schiffmans.com | B | shopify | yes | Shopify-hosted (MCP live) | real:template | real:template |  |  |  |  | yes | yes | GPTBot, ClaudeBot, Google-Extended, CCBot, Bytespider, Applebot-Extended, meta-externalagent |
| 42 | Ritani | ritani.com | unreachable |  |  |  | blocked |  |  |  |  |  |  |  |  |
| 43 | VRAI (Diamond Foundry) | vrai.com | A | shopify | yes |  |  | real |  |  |  |  | yes |  |  |
| 44 | Clean Origin | cleanorigin.com | unreachable |  |  |  | blocked | blocked |  |  |  |  |  |  |  |
| 45 | With Clarity | withclarity.com | B | shopify | yes | Shopify-hosted (MCP live) | real:template | real:template |  |  |  |  | yes |  |  |
| 46 | Grown Brilliance | grownbrilliance.com | A |  |  |  |  | real |  |  |  |  |  |  | GPTBot, ClaudeBot, anthropic-ai, CCBot |
| 47 | Ada Diamonds | adadiamonds.com | A |  |  | merchant | real | real | yes | yes |  |  |  |  | GPTBot, OAI-SearchBot, ClaudeBot, anthropic-ai, PerplexityBot, Google-Extended, CCBot, Bytespider, Applebot-Extended, meta-externalagent |
| 48 | Rare Carat | rarecarat.com | A |  |  |  |  | real |  |  |  |  | yes |  |  |
| 49 | Whiteflash | whiteflash.com | A |  |  |  |  | real |  |  |  |  | yes |  |  |
| 50 | Adiamor | adiamor.com | B |  |  |  |  |  |  |  |  |  | yes |  |  |
| 51 | Allurez | allurez.com | B | shopify | yes | Shopify-hosted (MCP live) | real:template | real:template |  |  |  |  | yes |  |  |
| 52 | Angara | angara.com | A |  |  |  |  | real |  |  |  |  | yes | yes |  |
| 53 | Catbird | catbirdnyc.com | B |  |  |  |  |  |  |  |  |  | yes |  |  |
| 54 | Brian Gavin Diamonds | briangavindiamonds.com | B | shopify | yes | Shopify-hosted (MCP live) | real:template | real:template |  |  |  |  | yes |  |  |
| 55 | Abe Mor | abemor.com | unreachable |  |  |  |  |  |  |  |  |  |  |  |  |
| 56 | Leibish & Co. | leibish.com | B | shopify | yes | Shopify-hosted (MCP live) | real:template | real:template |  |  |  |  | yes |  |  |
| 57 | Pompeii3 | pompeii3.com | A | bigcommerce |  | merchant |  | real |  |  |  |  |  |  |  |
| 58 | The Clear Cut | theclearcut.co | B | shopify | yes | Shopify-hosted (MCP live) | real:template | real:template |  |  |  |  | yes |  |  |
| 59 | Melanie Casey | melaniecasey.com | B | shopify | yes | Shopify-hosted (MCP live) | real:template | real:template |  |  |  |  | yes | yes |  |
| 60 | Stag & Finch | stagandfinch.com | B | shopify | yes | Shopify-hosted (MCP live) | real:template | real:template |  |  |  |  | yes |  |  |
| 61 | Olive Ave Jewelry | oliveavejewelry.com | unreachable | shopify | yes |  |  |  |  |  |  |  |  |  |  |
| 62 | Jewelry by Johan | jewelrybyjohan.com | unreachable |  |  |  | blocked | blocked |  |  |  |  |  |  |  |
| 63 | Keyzar Jewelry | keyzarjewelry.com | B | shopify | yes | Shopify-hosted (MCP live) |  |  |  |  |  |  |  |  |  |
| 64 | Frank Darling | frankdarling.com | unreachable | shopify | yes |  |  |  |  |  |  |  |  |  |  |
| 65 | Jean Dousset | jeandousset.com | B | shopify | yes | Shopify-hosted (MCP live) | real:template | real:template |  |  |  |  | yes | yes |  |
| 66 | Gabriel & Co. | gabrielny.com | A |  |  |  |  | real |  |  |  |  | yes | yes |  |
| 67 | Tacori | tacori.com | B | shopify | yes |  |  |  |  |  |  |  | yes |  |  |
| 68 | Verragio | verragio.com | unreachable |  |  |  | blocked | blocked |  |  |  |  |  |  |  |
| 69 | Hearts On Fire | heartsonfire.com | B | salesforce-commerce-cloud |  |  |  |  |  |  |  |  | yes |  |  |
| 70 | Kwiat | kwiat.com | unreachable |  |  |  | blocked | blocked |  |  |  |  |  |  | GPTBot, ClaudeBot, Google-Extended, CCBot, Bytespider, Applebot-Extended, meta-externalagent |
| 71 | Ring Concierge | ringconcierge.com | B | shopify | yes | Shopify-hosted (MCP live) | real:template | real:template |  |  |  |  |  |  |  |
| 72 | Anna Sheffield | annasheffield.com | B | shopify | yes | Shopify-hosted (MCP live) | real:template | real:template |  |  |  |  | yes |  |  |
| 73 | AUrate New York | auratenewyork.com | B | shopify | yes | Shopify-hosted (MCP live) | real:template | real:template |  |  |  |  | yes | yes |  |
| 74 | Noemie | noemie.com | unreachable |  |  |  |  |  |  |  |  |  |  |  |  |
| 75 | Brilliance | brilliance.com | unreachable |  |  |  | blocked |  |  |  |  |  |  |  |  |
| 76 | Kobelli | kobelli.com | B | shopify | yes | Shopify-hosted (MCP live) | real:template | real:template |  |  |  |  | yes | yes |  |
| 77 | SuperJeweler | superjeweler.com | A |  |  |  |  | real |  |  |  |  |  |  |  |
| 78 | Szul | szul.com | unreachable |  |  |  |  |  |  |  |  |  |  |  |  |
| 79 | MiaDonna | miadonna.com | B | shopify | yes | Shopify-hosted (MCP live) | real:template | real:template |  |  |  |  | yes |  |  |
| 80 | Do Amore | doamore.com | B | shopify-referenced |  |  |  |  |  |  |  |  | yes |  |  |
| 81 | Bario Neal | barioneal.com (domain forwards to bario-neal.com) | B | woocommerce |  |  |  | real:template |  |  |  |  | yes |  |  |
| 82 | Marrow Fine | marrowfine.com | B | shopify | yes | Shopify-hosted (MCP live) | real:template | real:template |  |  |  |  | yes |  |  |
| 83 | Ken & Dana Design | kenanddanadesign.com | B | shopify | yes | Shopify-hosted (MCP live) | real:template | real:template |  |  |  |  | yes |  |  |
| 84 | EraGem | eragem.com | B | magento |  |  |  |  |  |  |  |  | yes | yes |  |
| 85 | Lang Antique & Estate Jewelry | langantiques.com | A | magento |  |  |  | real |  |  |  |  | yes | yes |  |
| 86 | Borsheims | borsheims.com | A |  |  |  |  | real |  |  |  |  | yes | yes |  |
| 87 | Tapper's | tappers.com | B | shopify | yes | Shopify-hosted (MCP live) | real:template | real:template |  |  |  |  | yes | yes |  |
| 88 | Day's Jewelers | daysjewelers.com | B | shopify | yes | Shopify-hosted (MCP live) | real:template | real:template |  |  |  |  | yes |  |  |
| 89 | Long's Jewelers | longsjewelers.com | B | shopify | yes | Shopify-hosted (MCP live) | real:template | real:template |  |  |  |  | yes |  |  |
| 90 | Mervis Diamond Importers | mervisdiamond.com | B | shopify | yes | Shopify-hosted (MCP live) | real:template | real:template |  |  |  |  |  |  |  |
| 91 | Steven Singer Jewelers | stevensingerjewelers.com (domain forwards to ihatestevensinger.com) | B | shopify | yes | Shopify-hosted (MCP live) | real:template | real:template |  |  |  |  | yes |  |  |
| 92 | London Jewelers | londonjewelers.com | A |  |  |  | blocked | real |  |  |  |  |  |  | CCBot, Bytespider |
| 93 | Greenwich St. Jewelers | greenwichjewelers.com | B | shopify | yes | Shopify-hosted (MCP live) | real:template | real:template |  |  |  |  |  |  |  |
| 94 | Lumera Diamonds | lumeradiamonds.com | unreachable |  |  |  |  |  |  |  |  |  |  |  |  |
| 95 | Graff | graff.com | unreachable | salesforce-commerce-cloud |  |  |  |  |  |  |  |  |  |  |  |
| 96 | Chopard | chopard.com | unreachable | salesforce-commerce-cloud |  |  |  |  |  |  |  |  |  |  |  |
| 97 | De Beers Jewellers | debeers.com | B | salesforce-commerce-cloud |  |  |  |  |  |  |  |  | yes |  |  |
| 98 | Lauren B | laurenb.com (domain forwards to laurenbjewelry.com) | unreachable |  |  |  | blocked |  |  |  |  |  |  |  |  |
| 99 | Bernie Robbins Jewelers | bernierobbins.com | unreachable |  |  |  |  |  |  |  |  |  |  |  |  |
| 100 | Stienhardt | stienhardt.com | A | shopify | yes | Shopify-hosted (MCP live) | real | real | yes |  |  |  | yes | yes |  |

Column notes: "Shopify checkout" is set only when the storefront shows Shopify theme or header signals. "UCP" says who hosts the /.well-known/ucp profile. agents.md and llms.txt show "real" for merchant content, "real:template" for a shared template, "blocked" when the site refused the fetch, and blank when absent or a soft 404. "Product JSON-LD" and "GTIN/MPN" refer to the one sampled product page (URL in data/probe-summary.csv). "MCP Registry" is a match in the official registry; whether the matched entry's remote endpoint answered a read-only tools/list is in the Tier A table and in the registry_remote_live column of the CSV.

## Methodology, in plain language

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

