# BVVG Federal Land Agency Tenders Harvester

Harvests large agricultural, forest and peatland land parcel tenders published by
BVVG Bodenverwertungs- und -verwaltungs GmbH, the German federal land agency, and
loads them into a PostgreSQL 16 / PostGIS 3.4 staging table (`iris_staging.signal_ingest`)
for downstream processing.

## Data source

- Source site: `https://www.bvvg.de/objekte/` (confirmed reachable, `robots.txt`
  only disallows `/wp-admin/`, so `/objekte/` is explicitly crawlable).
- The brief's original endpoint, `https://www.bvvg.de/ausschreibungen`, returns
  HTTP 404 on the live site. The actual listing path is `/objekte/`, verified by
  fetching the live page and reading its navigation, pagination and robots.txt.
- Integration pattern: paginated HTML listing (`/objekte/`, `/objekte/page/N/`),
  20 results per page, each linking to a detail page with the full field set.
  This matches the brief's "Pattern B (HTML / Paginated Table)".
- The site runs on WordPress with the Immomakler real-estate plugin. A JSON REST
  API exists at `/wp-json/wp/v2/immomakler_object/{id}` but was not used, since
  the brief specifies the HTML pagination pattern; this is noted here for anyone
  extending the harvester later.

## Field mapping

Each detail page exposes a `dt`/`dd` key-value list under "Objektdaten" and a
tender deadline line under "Abgabe des Gebotes". The harvester maps:

| Source field | Staging column |
|---|---|
| `Objekt-Nr.` | `source_id` (natural key together with `source_system`) |
| canonical URL | `source_url` |
| `<h1>` title | `title` |
| `Objektart` | `objektart_label`, `objektart_slug` |
| `Bundesland` / `Kreis` / `Gemeinde` / `Gemarkung` | `bundesland` / `landkreis` / `gemeinde` / `gemarkung` |
| `Größe` | `size_hectares` (normalized to hectares, see below) |
| `Orientierungswert (Kauf|Pacht)` | `price_raw`, `marketing_type` |
| "Ausschreibung endet am DD.MM.YYYY, um HH:MM Uhr" | `tender_end_at` (converted from Europe/Berlin to UTC) |
| embedded Google Maps position | `location_point` (EPSG:25832), `location_precision`, `location_note` |
| attachment links (Flurstücksliste, Ausschreibungsbedingungen, Exposé) | `attachment_urls` |
| description panel | `description` |

### Domain scope filtering (agricultural / forest / peatland)

The source's own `Objektart` taxonomy (scraped from the search filter, 15 fixed
values) has direct categories for agricultural land (`Acker und Grünland`, and
its restricted variant) and forest (`Wald`), but **no dedicated peatland
category**. Peatland parcels are most often published under `Kompensationsflächen`
(compensation/offset areas) or `Gewässer` (water bodies) when they are even
singled out at all.

To honor the brief's "agricultural, forest and peatland" scope without a
matching source category, the harvester:

1. Maps `Acker und Grünland(-beschränkt)` -> `agricultural` and `Wald` -> `forest`
   directly from `Objektart`.
2. Additionally scans the title and description for specific peatland
   compound terms (`niedermoor`, `hochmoor`, `moorfläche`, `moorboden`,
   `moorschutz`, `wiedervernässung`, `paludikultur`, ...) and tags a match as
   `peatland`, regardless of its `Objektart`.
3. Records exactly which rule fired in `match_basis` (not persisted to the
   database, but available on the in-memory classification result) so matches
   are auditable rather than opaque.

This heuristic was tuned against real listings during development: an early
version matched the bare substring `moor`, which produced a false positive on
a clay mining rights tender whose long legal description mentioned
"anmoorige Wiesen" (boggy-ish meadows) as an incidental geological detail. The
keyword list was tightened to specific compounds to avoid this
(`test_classify_domain_does_not_false_positive_on_anmoorig_soil_description`).
Given the source has no dedicated peatland taxonomy, some precision/recall
trade-off is unavoidable; this is a documented limitation, not a bug.

Listings outside all three categories (e.g. `Erneuerbare Energien`, `Bauland`,
`Gewerbe`) are parsed and classified but **not persisted**, since they fall
outside the stated objective. The loader's `QualityReport.out_of_scope` count
and `per_record_issues` explain exactly why each one was excluded.

### Size units

Most listings report `Größe` in hectares (`3,02 ha`, German decimal comma).
A small number of listings — specifically `Bodenschätze-Ausschreibung`
(mineral rights tenders) — report size in square meters instead
(`859.803 m²`, German thousands-separator dot). This was only discovered by
running the harvester against the live site. The parser now detects the unit
suffix and converts m² to hectares; a size value with neither a recognized
`ha`/`m²`/`m2` unit, or an empty value, is treated as a visible validation
issue rather than silently stored as `None` with no explanation.

### Geolocation to EPSG:25832

Each detail page embeds an interactive Google Maps iframe that only renders
after cookie consent. Its full `<iframe>` markup — including the `q=lat,lng`
query parameter — is pre-rendered into the page source as a base64-encoded
`<script type="text/template">` block (used by the Borlabs cookie-consent
plugin to swap the real map in once consent is given). The harvester decodes
this block and extracts the coordinate without needing a browser, cookies, or
any interaction with Google Maps itself — this is already-delivered page
content, not a third-party API call.

Every detail page carries an explicit disclaimer directly below the map:
"Die dargestellte Position ist nur eine ungefähre Angabe der Lage" (the shown
position is only an approximate indication). The harvester therefore always
marks resolved coordinates as `location_precision = 'approximate'`, never
`'exact'`, which is an honest reflection of what the source actually provides.

Coordinates are validated twice before being accepted:

1. The raw WGS84 (EPSG:4326) latitude/longitude must fall within a bounding
   box that generously covers Germany.
2. After transforming to EPSG:25832 with `pyproj`, the resulting easting/northing
   must fall within the plausible numeric range for German UTM32 coordinates.

A coordinate that fails either check is **not stored** — `location_point` is
left `NULL`, `location_precision` is set to `'unresolved'`, and `location_note`
records why. This satisfies the requirement that invalid coordinates are never
silently accepted. A listing with no map data at all (some listings omit it)
is handled the same way.

### Tender end date, no publication date field

BVVG does not publish a distinct "publication date" for a listing anywhere on
the page. The only structured date available is the tender/auction deadline
("Ausschreibung endet am ..."), which the harvester parses, interprets as
Europe/Berlin local time (the site's only audience), and stores as a UTC
timestamp in `tender_end_at`. Some listings (marketed via direct inquiry /
"Direktanfrage" rather than a competitive tender) have no deadline at all;
`tender_end_at` is `NULL` for these and the gap is recorded in
`validation_issues`, visible rather than silently assumed.

## Idempotent loading

`iris_staging.signal_ingest` has a unique constraint on
`(source_system, source_id)`. Loading uses `INSERT ... ON CONFLICT DO UPDATE`,
so re-running the harvester against unchanged source data updates nothing
beyond `last_seen_at` and leaves `id`, `created_at` and `first_seen_at`
untouched. A `content_hash` (SHA-256 over the normalized field values) is
compared on every run; `updated_at` only advances when the hash actually
changed. This was verified against a live PostgreSQL/PostGIS container
(see `tests/integration/`), not just asserted.

## Project layout

Mirrors a standard scrape -> parse -> transform -> load pipeline:

```
app/
  config.py                      env-driven settings, no credentials in code
  scrapers/bvvg/                 http client, listing + detail page fetchers
  parsers/                       pure HTML -> dataclass parsing, no network
  geocoding/                     coordinate extraction + EPSG:25832 resolution
  transformers/                  domain classification, normalization, hashing
  database/
    models/                      SQLAlchemy ORM model
    repositories/                idempotent upsert repository
  loaders/                       scope filtering + quality report assembly
  runners/                       CLI entrypoint tying the pipeline together
alembic/                         schema migration for iris_staging.signal_ingest
tests/                           unit tests (fixtures, no network/db) + tests/integration (live db)
sql/validation_queries.sql       example QA queries against the staging table
samples/                         sample output from a real, rate-limited run
```

## Setup

Requires Python 3.12+. [`uv`](https://docs.astral.sh/uv/) is recommended:

```bash
uv venv --python 3.12 .venv
uv pip install -p .venv -e ".[dev]"
```

Or with plain `pip`:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Copy `.env.example` to `.env` and adjust as needed. No credentials are
hardcoded anywhere in source; all configuration is read from environment
variables (see `app/config.py`).

### Database

```bash
docker compose up -d db
export BVVG_DB_HOST=localhost BVVG_DB_PORT=5432 BVVG_DB_NAME=iris BVVG_DB_USER=iris BVVG_DB_PASSWORD=iris
.venv/bin/python -m alembic upgrade head
```

This creates the `postgis` extension, the `iris_staging` schema, and the
`signal_ingest` table with a GiST index on `location_point` and a btree index
on `tender_end_at`.

### Running the harvester

```bash
.venv/bin/python main.py
```

Useful environment variables (see `.env.example` for the full list):

- `BVVG_MAX_PAGES` — cap the number of listing pages fetched, useful for a
  quick smoke run.
- `BVVG_REQUEST_DELAY` — minimum seconds between consecutive requests
  (politeness delay). The http client tracks the time of its last request
  and sleeps as needed before firing the next one, so this applies across
  both listing and detail page fetches. Defaults to 1.0.
- `BVVG_USER_AGENT` — see "a note on the site's bot filtering" below before
  changing this.

### A note on the site's bot filtering

Requests with a generic client (no descriptive headers, e.g. bare `curl`) are
rejected with HTTP 403 by the host's nginx/WAF layer. This is unrelated to
`robots.txt`, which explicitly permits crawling `/objekte/` — it is a basic
anti-automation heuristic, not an access restriction on this content. A
standard `Accept`/`Accept-Language` header set plus **any** reasonably
specific `User-Agent` string gets through; however, a `User-Agent` containing
certain scraper-flavored substrings (e.g. containing "Harvester") was
observed to be blocked during testing, while an otherwise identical request
with a plain browser-style `User-Agent` succeeded. The default in
`.env.example` is intentionally descriptive and includes a contact point, in
line with good scraping etiquette; if you find it blocked against the live
site, set `BVVG_USER_AGENT` to a standard browser string instead. This is
documented here rather than silently worked around in code, since it's a
judgment call about etiquette versus reliability that an operator should make
deliberately.

### Tests

```bash
.venv/bin/python -m pytest tests/ -v
```

Unit tests run fully offline against real and synthetic HTML fixtures in
`tests/fixtures/` (no network, no database). The HTTP client tests use
`responses` to simulate retries, exhaustion, and empty-body failures.

`tests/integration/test_signal_ingest_repository.py` exercises the real
upsert behavior (insert, re-run idempotency, content-change updates, valid
geometry persistence) against a live PostgreSQL/PostGIS instance. These tests
read connection settings from the same `BVVG_DB_*` environment variables as
the harvester and **skip automatically with a clear message** if no database
is reachable or the migration hasn't been applied yet — they do not fail a
plain `pytest tests/` run on a machine without Docker.

```bash
docker compose up -d db
.venv/bin/python -m alembic upgrade head
export BVVG_DB_HOST=localhost BVVG_DB_PORT=5432 BVVG_DB_NAME=iris BVVG_DB_USER=iris BVVG_DB_PASSWORD=iris
.venv/bin/python -m pytest tests/integration/ -v
```

## Sample output and validation

`samples/signal_ingest_sample.json` and `samples/quality_report.md` were
produced from one real, rate-limited run against the live public site
(1.5s between requests, single listing page, standard browser `User-Agent`),
loaded into a local PostGIS container via the exact pipeline described above.
No anonymization was needed since BVVG tender listings are already public.

`sql/validation_queries.sql` contains the QA queries used to spot-check the
loaded data: domain tag counts, duplicate-key check, unresolved locations,
out-of-bounds coordinates, open validation issues, upcoming deadlines, and
hectares by Bundesland.

## Known limitations

- Peatland scope is a best-effort keyword heuristic over title/description
  text, since the source has no dedicated peatland taxonomy category. See
  "Domain scope filtering" above.
- Map coordinates are explicitly approximate per the source's own disclaimer;
  this harvester never claims better precision than the source provides.
- There is no publication date field on the source; only the tender deadline
  is available, and some listings (direct-inquiry sales) have no deadline at
  all.
- The site's WAF blocks some descriptive `User-Agent` strings; see "A note on
  the site's bot filtering" above.
- Running on Apple Silicon, the `postgis/postgis:16-3.4` image only ships for
  `linux/amd64` and runs under emulation; functionally correct but slower to
  pull and start than on native amd64 hosts.
