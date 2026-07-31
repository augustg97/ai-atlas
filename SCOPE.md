# SCOPE — AI Atlas

The contract. Produced by the scoping interview at kickoff; every later "was that in scope?" is
settled by reading this file. Amend it deliberately, with a date, rather than drifting.

*Scoped 2026-07-31. The interview ran across the options document
(claude.ai artifact "Charting the AI Wiki", 2026-07-30) and August's decision message; the five
decisions below are recorded verbatim in §11.*

---

## 1. The claim

**The AI world is not a news feed. It is a landscape of ideas with real geography — capability
ranges, regulatory borders, contested marches — deforming under pressure, and it can be watched
moving, day by day.** Capability advances, capital concentrates, institutions respond, and every
response redraws the terrain the next advance crosses. The viewer should walk away understanding
that AI development and AI governance are one coupled system with structure — not a stream of
disconnected headlines — and that the wiki behind this model knows exactly how well each part of
that structure is evidenced.

## 2. Extent

| | |
|---|---|
| time | **2012-09 (AlexNet; the deep-learning era) → today**, the right edge advancing daily |
| stored step | dated events (windowed features) across the whole range; field keyframes **weekly** across the range, **daily** inside the trailing 90 days |
| shown step | any date; features windowed, fields interpolated between bracketing keyframes |
| space | **the idea plane** — a fixed 2-D projection of the wiki's embedding space, unit square; secondary: a world map (jurisdiction view) of the same state |
| finest legible thing | a single entity's card and its arcs, legible at full zoom inside its territory; on the substrate, per-pixel terrain detail that survives zoom (see §3) |
| projection / substrate | **datum v1** (frozen semantic projection, §5) rendered as a WebGL field-composited surface; jurisdiction view uses a fixed equal-area world projection with a matched basemap |

Pre-2012 is out of scope for v1: a single closed "prehistory" band at the timeline's left edge,
labelled, non-navigable. (Extensible later; see non-goals.)

## 3. The layer table

Every layer, and which of the four it is. A layer that cannot be put in one of these boxes is not
yet designed. **Rule for this project: every visual channel appears in this table with a stated
mechanism, or it does not ship — terrain that means nothing is decoration, and the audit enforces
the difference.**

| layer | kind | mechanism (if modelled) or source (if authored) | engine |
|---|---|---|---|
| Territory terrain (relief, substrate colour, texture) | modelled | page/chunk density in datum v1 shapes relief; substrate texture keyed to territory id + per-page material coordinates so detail does not slide under its terrain; procedural micro-detail grown per pixel from corpus statistics (§7 visual standard) | field (GLSL) |
| Territory boundaries + names | modelled, labelled by authored taxonomy | clusters in datum v1; named and bounded by the dev-log's 13 section taxonomy | field + feature |
| Attention heat / weather | modelled | kernel density of dated dev-log items (2,698 at kickoff) at their embedded positions; weekly keyframes, daily in the trailing window, interpolated; rendered as luminance/weather on the surface, not as dots | field (GLSL) |
| Entities: companies, models, legislation, litigation, orgs, standards, concepts (~1,100 at kickoff) | authored windows, modelled positions | windows from `founded` / `release_date` / `filed` / enacted / first-mention; positions from datum v1; drawn as **grown structures** (footprints, settlements, monuments — not dots; §7) | feature over field |
| Growth footprints | modelled | company/entity footprint generated from the wiki's dated Snapshot series (valuation, ARR, users, compute — 444 rows at kickoff); the Territorial-US city pattern, rendered as procedural urban fabric | feature + procedural |
| Typed arcs | authored | the wiki's `## Relationships` edges (~6,200 at kickoff); `contradicts` in its own visual register; drawn between datum positions as flowing filaments, windowed by both endpoints' existence | feature |
| Event strikes | authored | dev-log items ripple at their topic position on their **in-text event date**, URL-cited; intensity by section volume | feature over field |
| Eras & chapters | authored | bands on the scrubber + illustrated chapter cards, grounded in the wiki's analysis pages (deep-learning era → transformer era → scaling era → ChatGPT shock → regulatory response → agentic/IPO era; final naming in round 1) | — |
| Jurisdiction view | derived | the same emitted state re-projected: legislation at jurisdiction, litigation at venue (`court`), companies at HQ (`hq_country`); choropleth of regulatory posture from legislation statuses | feature over static basemap |
| Knowledge horizon (wiki-time) | authored | `Wiki/_meta/log.md` operations (650 at kickoff): what the wiki knew at *t*; a toggle that dims the unlearned; doubles as the coverage-honesty layer | feature |
| Readout | derived | computed from the same emitted state: date, era, frontier count, laws in force, active cases, day's event count, largest valuation, wiki pages known | — |
| People | authored, **cards only** | person entities render as cards reachable from events, arcs and other cards — never as map features (decision §11.3) | card system |
| Ask the Atlas (chatbot) | derived | tiered: T0 semantic find→fly-to (client-side over the emitted quantized index); T2 synthesis with enforced card citations via a small worker endpoint; see §12 | panel |

## 4. The evidence boundary

Three boundaries, each with a designed UI behaviour:

1. **The wiki horizon — 2026-04-13.** Sub-daily coverage (dev-log + audit log) begins here.
   Before it, the model runs on the deep spine only: frontmatter dates (56 model releases from
   2020-11, 41 filings, 137 foundings, 562 source publication dates back to 2003) plus
   round-1-authored era events for 2012–2020. **UI:** pre-horizon eras render in a visibly
   sparser register (fewer strikes, calmer surface) and the readout labels the era
   "reconstructed from the record"; post-horizon labels "observed daily".
2. **Now.** The model stops at today and advances with the vault. **UI:** the right edge is a
   hard, visible edge with the daily update line attached; no forecast pixels exist.
3. **The construction boundary.** Semantic position is computed, not observed. **UI:** the About
   page owes the reader *"What distance on this map is, and is not"* — adjacency means the
   wiki's language places two things in one conversation; it does not mean alliance, similarity
   of view, or causation. Every card's position row says "placed by the model".

Where the sources disagree, and the shape of the disagreement:

| disagreement | shape | how the model handles it |
|---|---|---|
| valuations, revenue, user counts, market share | amount | ranges from the Snapshot rows; `confidence` + decay rendered on the card; never a single confident number where the wiki holds a range |
| policy positions and their characterisation | interpretation | wiki `contested` confidence → card renders "What the sources say" with both sides, per house style |
| active-litigation posture | state-in-time | allegation vs holding kept distinct on cards; `last_status_check` shown; witness audit against dockets |
| whether a relationship exists (`contradicts` vs `supports`) | existence | both edges drawn, in different registers; never resolved silently |

## 5. The canonical frame

| dimension | canonical choice | sources that differ, and the conversion |
|---|---|---|
| position | **datum v1**: unit-square coordinates from a frozen, seeded 2-D projection of voyage-3-large page vectors (built after an embedding refresh; method chosen in round 1). New pages are projected *into* the frozen datum. Re-basing is a deliberate, versioned event (datum v2, …) with Procrustes alignment to minimise apparent motion, announced in the update log — never a nightly re-fit | LanceDB chunk vectors → page vector (weighted mean) → frozen transform → (x,y). The transform's parameters ship with the data and are stamped with the datum version |
| dates | **ISO-8601 event dates**, with every date carrying its kind: `event` / `published` / `ingested` / `checked`. Event-date primacy everywhere; the three kinds are never conflated (the vault's own source-fidelity rule, promoted to schema) | dev-log filename dates = digest publication, NOT event dates — parse in-text event dates; `last_updated` frontmatter is unreliable as edit time (June 2026 restamp) — wiki-time comes from `log.md` only; litigation `filed:` non-ISO variants normalised at emit, unparseable → needs-review, never guessed |
| names | **wiki slugs** are canonical IDs (`companies/anthropic`); page titles for display; territory names from the 13 dev-log section headers | search.js `h` paths and retrieval-index rows both resolve to slugs; broken/bare-slug links resolved with the dashboard's own `build_backlinks()` logic, ~1.3% dangling edges dropped with a count reported |
| jurisdictions | ISO 3166-1 alpha-2 + `US-XX` state codes | wiki tags (`us`, `eu`, `uk`, `china`, …) and `hq_country` map to codes at emit; unmapped → needs-review |
| taxonomy | the dev-log's 13 sections as territory labels; wiki tag families as facets (open vocabulary tolerated, families used for faceting only) | — |

Conversions live in `Research/modeling/frames.py` (datum, dates, slugs, jurisdictions) with
selftests. **Never combine two sources without checking they are in the same frame.**

## 6. The card contract

Every card carries:

- eyebrow (page type), title
- 2–4 fact rows from frontmatter (typed per page type: developer/release/parameters;
  court/filed/status; founded/HQ/type; …)
- prose **for the current time** — `eras: [{from, to, text}]`, generated from the wiki page's
  dated material at emit, tiling the entity's life without gaps (audited)
- the era span, shown to the reader
- **confidence badge with its decay state** (the wiki's `confidence` + decay windows, rendered,
  not buried)
- citations — the wiki page (deep link into the vault's live dashboard) and the page's own
  sources; litigation cards keep allegation vs holding distinct
- position row labelled "placed by the model"

Fallback tiers, and the heading each is shown under:

1. curated exception → **"About this one specifically"** (hand-written, `exception: true`,
   audit-protected)
2. model-derived → **"From the record at this date"** (era-keyed emit from the wiki page)
3. generic → **"Typical of this territory in this era"** — **the heading must say it is
   interval-wide, not specific.**

Approximate counts at kickoff: ~1,100 entity cards + 13 territory cards + ~10 chapter cards +
saga context cards (EU AI Act, NYT v. OpenAI, chip export controls, AI bubble, …) + person cards
on demand. All generated; curated exceptions are the only hand-written tier.

## 7. The standard for done

Named reference artefacts a result is compared against, at a stated scale:

- **Witness audits (scriptable, run by the gate):** Epoch AI's notable-models dataset (CC-BY) —
  release existence and dates, coverage both directions; a named US state-AI-law tracker —
  legislation counts by status at spot dates; CourtListener dockets — status of all tracked
  cases. Baselines recorded; the ratchet turns one way.
- **Frame stability:** between successive emits, unchanged pages move < ε in datum coordinates
  (ε set in round 1, audited nightly).
- **The ChatGPT-shock test (qualitative, named):** scrubbing across 2022-11 must visibly
  propagate activity into every territory within weeks of model time. If the surface does not
  show it, the attention layer has failed regardless of statistics.
- **Visual standard:** five reference framings at stated zooms, captured at v0.2 and kept in
  `reference/` (gitignored, measured against); every entity clickable; first frame < 1 MB and
  < 1 s locally; smooth pan/scrub on this Mac.
- **The visual-fidelity bar (decision §11, verbatim requirement):** the substrate must read as a
  **living, breathing surface** — per-pixel composed terrain with relief, texture and weather —
  not dots and symbols on a flat ground. Tectonic Earth is the named bar. Acceptance check per
  round: a full-frame screenshot must be assessable as *"a rendered landscape"* rather than
  *"a chart"*, and the register records the assessment honestly.

The independent witnesses are the three named above; the wiki itself is never its own witness.

## 8. Sensitivities

This is August's professional field, dense with living people, active litigation and contested
policy. Carried **in the substance, distributed through the layers**:

- Living people → cards only, never map features (decision §11.3); only documented, cited,
  neutral facts; no inferred person-to-person networks; person cards inherit the wiki's
  house-style neutrality.
- Active litigation → allegation vs holding distinct on every card; status dated
  (`last_status_check` surfaced); witness-audited against public dockets.
- Contested policy claims → `contested` confidence renders "What the sources say"; nothing the
  record disputes is stated flatly (the Aztec `accounts:` rule, generalised).
- Editorial neutrality of the map itself → **the map must not editorialise by geometry**:
  proximity is a property of the corpus, the About page says so plainly, and no visual channel
  encodes a judgment that is not in the layer table with a mechanism.
- The wiki's own blind spots → the knowledge-horizon layer makes coverage visible instead of
  implying omniscience; the queue feedback loop (§9 of the options doc; approved) files gaps
  back to the wiki rather than papering over them.

Naming convention and why: wiki slugs and titles govern; jurisdictions by ISO code; territory
names from the dev-log taxonomy — every name on the map traces to a name August's own corpus
already uses.

## 9. Non-goals

- No forecasting; nothing renders past today.
- No sentiment, social-media or engagement layers.
- No person dots on the map, v1 (cards only).
- No sub-daily update cadence (the vault updates twice daily; the model emits nightly).
- No in-app autonomous web research: Ask the Atlas answers from the emitted corpus only and
  says when the corpus is silent.
- Pre-2012 history: closed band only, v1.
- No card images pipeline, v1 (the licence machinery exists in the Aztec project to copy later;
  schematic SVGs by the model's own hand are allowed).
- Not a general Obsidian-vault viewer; this is a model of the AI world, not a notes browser.

## 10. Budget and delivery

| | |
|---|---|
| delivery | static site, GitHub Pages `augustg97/ai-atlas`, Pages serves `main:/docs`; the vault remains the single source of truth, read-only to the model except `Wiki/_meta/queue/` (approved feedback loop) |
| total bytes over the wire | core (entities+events+arcs+series+eras+datum) ≤ 25 MB; field keyframes fetched lazily, current-window-first |
| time to first usable frame | < 1 MB and < 1 s local; two-keyframe lazy load from day one (never an eager loader) |
| offline / `file://` required? | no (Pages + localhost); Tier-0 chatbot must work fully static |
| pipeline? | yes: `Research/modeling/emit.py` (vault → staged), `Research/modeling/audit_all.py` (the gate), `build/build_site.py` (stamp → docs/), nightly after the vault's 09:22 cycle; three unattended correct mornings = v1.0 acceptance |

## 11. Decisions of record (August, 2026-07-31, verbatim)

1. *"Let's try Plate I as you recommend"* — the semantic-terrain Atlas, absorbing the
   jurisdiction view and the typed-arc layer.
2. *"Let's go back to 2012/deep learning era"* — time floor 2012-09.
3. *"We'll keep people as cards and not map dots for now."*
4. *"AI Atlas is good, as well as the repo and Pages names."*
5. *"Queue feedback loop approved."*

Plus two charter-level requirements from the same message:

- *"Let's see if we can incorporate or replicate the chatbot and make it better. I haven't used
  the existing chatbot since its creation."* → §12.
- *"This final product should be visually highly detailed and striking… The Aztec and US models
  are subpar because they primarily rely on dots and symbols, and do not present a living,
  breathing surface. The Tectonic Earth is much better… We need to aim for that quality, and
  focus on visualization."* → the visual-fidelity bar in §7, and subject rule 6 in README §2.

## 12. Ask the Atlas (the chatbot, in scope)

Why the existing one went unused: it lives in a terminal (`bin/ask.py`) and its index went stale
(untouched since 2026-05-16). The redesign removes both failure modes:

- **Tier 0 — semantic navigation (fully static, always works):** the nightly emit ships a
  compact quantized page-vector index (~1,700 pages × reduced dims ≈ a few hundred KB);
  querying embeds nothing server-side — the query goes through the same frozen datum transform
  client-side where feasible, or lexical + tag fallback — and the answer is *the map itself*:
  matching cards highlighted, camera flown, timeline seeked.
- **Tier 2 — grounded synthesis (small worker endpoint):** retrieval as Tier 0, then a worker
  (Cloudflare, matching the vault's existing worker infrastructure) holding the API key calls
  Claude with the retrieved wiki context; **every claim in the answer must carry a card
  citation, enforced by the response schema**; answers can drive the map ("show me" seeks and
  flies). Multi-turn with prompt caching. When the corpus is silent it says so and offers to
  file the gap into the wiki's queue — the same approved feedback loop.
- **Freshness by construction:** the index is rebuilt by the nightly emit, so it can never be
  months stale again.
- Tier 1 (extractive display without synthesis) falls out of Tier 2's retrieval and ships
  whenever Tier 2 does.

Dependencies to flag honestly: Tier 2 needs a deployed worker and an API key (August's), and its
per-query cost is bounded by a token budget. Tier 0 has no dependencies and ships first.
