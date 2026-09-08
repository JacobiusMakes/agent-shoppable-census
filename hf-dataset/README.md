---
pretty_name: Agent-Shoppable Census
license: cc-by-4.0
language:
  - en
tags:
  - agentic-commerce
  - ai-shopping
  - ecommerce
  - jewelry
  - mcp
  - structured-data
  - web-census
size_categories:
  - n<1K
configs:
  - config_name: summary
    data_files:
      - split: train
        path: data/probe-summary.csv
  - config_name: domains
    data_files:
      - split: train
        path: data/domains.csv
---

# Agent-Shoppable Census

Can an AI agent buy a ring here?

This is a reproducible census of 100 US online sellers of engagement rings and
diamond jewelry. It tests public agent-readiness signals and separates them into
two tiers so that default ecommerce-platform features do not inflate the result.

The September 2026 snapshot reports 18 Tier A sellers with merchant-built agent
signals, 52 Tier B sellers with platform-inherited signals, and 30 sellers that
were unreachable to the read-only probe. These labels describe the public
technical surface observed on the run date. They do not grade business quality.

Published by [Stienhardt](https://stienhardt.com/?utm_source=huggingface&utm_medium=dataset_repository&utm_campaign=agent_shoppable_census),
a New York City lab-grown diamond and engagement ring retailer. Stienhardt is
one of the 100 rows, is identified as the publisher, and is scored by the same
script and rubric as every other seller.

## Configurations

- `summary`: one row per seller with observed agent-readiness, ecommerce,
  structured-data, crawler, and endpoint fields.
- `domains`: the 100-domain sampling frame, seller name, source code, and notes.

## Reproducibility and raw evidence

The [GitHub repository](https://github.com/JacobiusMakes/agent-shoppable-census)
contains the read-only probe, results renderer, full methodology, raw HTTP
evidence, run metadata, cited domain-source table, known limits, and licenses.

The [fixed v0.2 release](https://github.com/JacobiusMakes/agent-shoppable-census/releases/tag/v0.2)
packages the September domain list, summary, raw evidence, run metadata, and
rendered results. GitHub publishes a SHA-256 digest for every release asset.

## Tier summary

- Tier A, merchant-built: at least one seller-controlled agent signal, such as
  a qualifying MCP Registry entry, a live custom MCP endpoint, substantive
  `agents.md` or `llms.txt`, an ACP endpoint, or a merchant-hosted UCP profile.
- Tier B, platform-inherited: signals supplied by a platform or theme, such as
  Shopify-hosted UCP, template-generated agent files, or Product and Offer
  JSON-LD.
- Unreachable: neither tier was observed by the read-only probe. The repository
  records bot walls, HTTP failures, and connection failures separately.

## Important limits

- This is a dated web census. Public endpoints can change after the run.
- One product page is sampled per seller.
- A blocked fetch does not prove the seller has no agent infrastructure.
- The list is a documented public-source approximation, not a precise ranking
  by ecommerce revenue.

## License

The summary tables, domain list, and prose are CC BY 4.0. Probe and rendering
code in the GitHub repository are MIT licensed. See the repository for the
complete license boundaries and third-party cache exclusions.

## Citation

```bibtex
@dataset{stienhardt_agent_shoppable_census_2026,
  title  = {Agent-Shoppable Census: agent readiness among 100 US online jewelry sellers},
  author = {{Stienhardt}},
  year   = {2026},
  month  = {9},
  url    = {https://github.com/JacobiusMakes/agent-shoppable-census},
  note   = {Version 0.2, CC BY 4.0}
}
```
