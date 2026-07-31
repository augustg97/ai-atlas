# Source survey — AI Atlas

*Surveyed 2026-07-30/31, before any app code was written. This is Phase 2 of `/model-kickoff`.
Counts are as of the kickoff inventory and change daily by design.*

The single most important fact: **the primary source is one corpus August already owns and
maintains** — the wiki in August's Vault — so the usual survey risk (frames silently differing
between upstream datasets) concentrates into two places: (1) the *date kinds* inside the vault,
and (2) the *witnesses* used to score the model. Both are handled in
`Research/modeling/frames.py` with selftests.

---

## 1. What data exists, per layer

Primary source path: `~/Library/Mobile Documents/com~apple~CloudDocs/August's Vault` —
**read-only to this project except `Wiki/_meta/queue/`** (approved feedback loop). Not a git
repo; its own audit log is the history.

| layer | source | format | resolution / count at survey | licence | access |
|---|---|---|---|---|---|
| entities + windows | `Wiki/{companies,models,legislation,litigation,entities,concepts,government,industries,standards}/` frontmatter | YAML + markdown | 1,135 pages | August's own work — shippable | file read at emit |
| event strikes | `New Developments Log/*.md` | prose items with `<sup>[n](url)</sup>` footnotes + `## Sources` lists | 201 files · 2,698 items · 2026-04-24 → now, twice daily | shippable (text is August's; URLs cited) | file read at emit |
| quantitative series | `## Snapshot` tables on 91 pages | markdown tables, newest-first | 444 ISO-dated rows | shippable | file read at emit |
| typed arcs | `## Relationships` sections | `- **type:** [[slug]]` bullets | ~6,200 edges, 20+ types | shippable | file read at emit |
| link weight / prominence | `[[wikilinks]]` in bodies | markdown | 31,681 links, median 13/page, ~1.3% dangling | shippable | file read at emit |
| positions (datum) | `embeddings/lance/wiki.lance` + `backend.json` | LanceDB · voyage-3-large · 1024-d · chunk-level · kinds wiki/raw/devlog | 257 MB; checksums 1,611 entries; **stale since ~2026-05-16** | derived from August's text — shippable in reduced form | refresh via `bin/build-embedding-index.py` (needs `VOYAGE_API_KEY`), then read |
| node-table bootstrap | `Wiki/_meta/site.nosync/search.js` | `var PAGES=[…]` JSON | 1,785 records, rebuilt by the vault's Stop hook | shippable | strip prefix, parse |
| wiki-time (knowledge horizon) | `Wiki/_meta/log.md` + `log-archive/` | dated operation entries | 650 entries, 2026-04-13 → now | shippable | parse H2/H3 headings |
| chapters / era grounding | `Wiki/analysis/` (23) + `Wiki/_meta/briefings/` (85) | markdown | — | shippable | file read |
| confidence / honesty | universal frontmatter | `confidence` high/medium/low/contested + decay windows 3/6/12 mo | 798 / 820 / 73 / 4 | shippable | frontmatter |
| deep spine pre-2026 | `Wiki/sources/` `date:` | ISO | 562/564 pages, 2003-04 → now | shippable (kind=`published`) | frontmatter |
| 2012–2020 model spine | **Epoch AI notable-models dataset** | CSV | landmark systems back through AlexNet, with dates/developers/compute | **CC-BY 4.0 — shippable with attribution**; doubles as witness | download; URL + schema verified in round 1 (P1-3) |

## 2. Frames

| source | coordinates | calendar / dating | naming | administrative vintage |
|---|---|---|---|---|
| wiki frontmatter | — | ISO mostly; `filed:` has non-ISO variants; `founded:` bare years | slugs | tags: us/eu/uk/china/global |
| dev-log | — | **filename = digest publication date; in-text dates = event dates** (curated by the vault's source-fidelity rule); footnotes carry their own publication dates | 13 stable H2 sections | — |
| log.md | — | operation dates = ingest dates | slugs in wikilinks | — |
| Snapshot tables | — | mixed precision: `YYYY-MM-DD`, `YYYY-MM`, bare year | — | — |
| embeddings | 1024-d voyage space | index build time | chunk ids → slugs | — |
| Epoch dataset | — | ISO release dates | Epoch's model names → wiki slugs (mapping table, tested) | — |
| trackers / dockets (witnesses) | jurisdictions | enactment vs effective; filed vs decided — **kinds kept distinct** | statute + case names | current |

**Canonical frame chosen** (SCOPE §5): **datum v1** unit-square positions (frozen, seeded,
versioned; Procrustes-aligned rebases only) · **ISO-8601 dates each carrying a kind** —
`event` / `published` / `ingested` / `checked`, event-date primacy · **wiki slugs** as IDs ·
**ISO 3166-1 + US-XX** jurisdictions · the 13 dev-log sections as territory taxonomy.
**Conversions:** `Research/modeling/frames.py`, with selftests; unparseable values go to
needs-review with a count — never guessed.

Known hygiene defects normalised there (all found in the kickoff inventory): duplicate
`status:` key in `litigation/musk-v-altman.md`; inline `#` comments on ~7 `entity_type` values;
undocumented-but-real enum values (`entity_type: government-agency` ×22, `company_type: defense`
×4); one `date: 1970-01-01` sentinel; `New Developments Log/SCHEMA.md` describes a format only
1/201 files uses — **never parse against it**; two site dirs — `site/` is dead, use
`site.nosync/`; `last_updated` is not edit history (June 2026 mass restamp) — wiki-time comes
from `log.md` only.

## 3. Where the record stops

- **2012-09** — the chosen floor (decision of record); a closed, labelled "prehistory" band
  before it.
- **2026-04-13** — the wiki horizon: sub-daily coverage begins. Before it the model runs on the
  deep spine (frontmatter dates + Epoch + round-1 authored era events); the UI renders
  pre-horizon eras in a sparser register labelled "reconstructed from the record".
- **Today** — the hard right edge; advances daily; no forecast pixels exist.
- **Edge dates** — relationships carry no start dates; drawn while both endpoints exist, stated
  in About. Wiki-time before 2026-04-13 does not exist (the wiki's birth).

## 4. Where the sources disagree

| disagreement | shape | how the model will handle it |
|---|---|---|
| valuations, revenue, users, market share | amount | ranges from Snapshot rows; confidence + decay rendered; never one confident number where the wiki holds a range |
| policy positions | interpretation | `contested` → "What the sources say", both sides, house style |
| litigation posture | state-in-time | allegation vs holding distinct; `last_status_check` surfaced; docket witness audit |
| relationship polarity (`contradicts` vs `supports`) | existence | both drawn, distinct registers; never silently resolved |

## 5. The independent witness

Three, all genuinely independent of the wiki, all scriptable at audit time:

1. **Epoch AI notable-models dataset** (CC-BY) — model existence + dates, both directions.
2. **A named US state-AI-law tracker** (IAPP or MultiState; pick and name in round 1) —
   legislation counts by status at spot dates. Measure-against-only.
3. **CourtListener dockets** (public records; already connected via MCP in August's
   environment) — status of all 41 tracked cases. Measure-against-only.

Stanford AI Index annually, at rebase points, for aggregate sanity. **The wiki is never its own
witness.**

## 6. Layers with no usable source (authored, deliberately)

- **2012–2020 era events** beyond Epoch's model rows — authored as wiki pages *via the approved
  queue loop* (the wiki ingests them with citations; the Atlas emits them like everything
  else). The wiki stays the single source of truth.
- **Era/chapter boundaries and names** — authored, grounded in `Wiki/analysis/`.
- **Curated card exceptions** — hand-written, `exception: true`, audit-protected.
- **Territory display names** — the 13 sections, authored by the vault already.

## 7. Licensing summary

| class | items |
|---|---|
| shippable | vault text (August's work product); Epoch CSV (CC-BY, attributed); emitted derived data; model-authored schematic SVGs |
| measure-against-only | tracker pages; AI Index; visual-standard reference screenshots (gitignored `reference/`) |
| excluded v1 | all third-party images (no card-image pipeline; Aztec's licence machinery exists to copy when that changes) |
| secrets | `VOYAGE_API_KEY` (embedding refresh), `ANTHROPIC_API_KEY` (Ask the Atlas T2, worker-side only) — never committed |
