# Quality report: sample run

Produced by a single real run against `https://www.bvvg.de/objekte/` (page 1,
20 listings, `BVVG_MAX_PAGES=1`, 1.5s delay between requests), loaded into a
local PostgreSQL 16 / PostGIS 3.4 container via `docker-compose.yml` and the
`0001_create_signal_ingest` migration. Run date: 2026-10-27.

## Summary

| Metric | Value |
|---|---|
| Listings scraped from page 1 | 20 |
| In scope (agricultural / forest / peatland) | 15 |
| Out of scope (filtered out, not persisted) | 5 |
| Inserted | 15 |
| Updated | 0 |
| Unchanged | 0 |
| Unresolved locations | 0 |
| Network errors | 0 |
| Malformed / unparsable records | 0 |
| Duplicate records in staging table | 0 |

All 15 in-scope listings resolved to an `agricultural` domain tag with an
`approximate` EPSG:25832 point geometry (no peatland or forest listings
happened to be on this particular page; both categories are covered by
synthetic fixtures in `tests/fixtures/` and exercised by
`tests/test_land_type_classifier.py`).

## Out-of-scope listings (filtered, not persisted)

| Source ID | Title | Reason |
|---|---|---|
| MS76-2800-113423 | Grundstück in Horst bei Boizenburg/Elbe | Objektart `Grundstück`, no agricultural/forest/peatland match |
| BB62-2800-036426 | Flächen zur potenziellen Windenergienutzung bei Redlin | Objektart `Erneuerbare Energien` |
| MS76-2800-023824 | Windpotentialflächen – Gemarkung Woosten | Objektart `Erneuerbare Energien` |
| VV81-2450-003223-AUS | (mineral rights tender) | Objektart `Bodenschätze-Ausschreibung` |
| VV71-2450-004116-AUS | Ausschreibung Bergwerkseigentum Göhren, Tonrohstoffe | Objektart `Bodenschätze-Ausschreibung`; see the `anmoorig` false-positive note below |

## Visible data quality issues

| Source ID | Title | Issue |
|---|---|---|
| BB25-1800-031126 | Flächen in Crostwitz und Caseritz | Missing tender end date (listing uses direct-inquiry marketing, no fixed deadline) |
| MS74-1800-031426 | Acker 23974 Neuburg OT Ilow | Missing tender end date (same reason) |

Both are visible, explained gaps rather than silent `NULL`s: the source page
for each genuinely has no "Ausschreibung endet am ..." section, confirmed by
inspecting the raw page (it shows a "Direktanfrage" panel instead of
"Abgabe des Gebotes").

## Issues found and fixed during this run

Two real data-shape issues only surfaced by running against live data, not
anticipated from the fixture alone:

1. **Size unit variance.** `Bodenschätze-Ausschreibung` listings report size
   in square meters (`859.803 m²`) rather than hectares. Fixed by detecting
   the unit suffix and converting m² to hectares
   (`app/transformers/signal_record.py::_parse_size_hectares`).
2. **Peatland keyword false positive.** The bare substring `moor` matched
   "anmoorigen" (boggy-ish soil) inside a mineral-rights tender's long legal
   description, incorrectly tagging it `peatland`. Fixed by replacing the
   generic substrings with specific compound keywords
   (`app/transformers/land_type_classifier.py`), with a regression test
   (`test_classify_domain_does_not_false_positive_on_anmoorig_soil_description`).

## Idempotency verification

Re-running the harvester against the same page with no source changes
produced `inserted=0, updated=0, unchanged=15` on the second pass, with the
row count in `iris_staging.signal_ingest` staying at 15. See
`tests/integration/test_signal_ingest_repository.py` for the automated
version of this check against a live database.

## Validation queries

See `sql/validation_queries.sql`. Results against this sample:

- Duplicate key check: 0 rows (no duplicates).
- Out-of-bounds coordinate check: 0 rows (no invalid geometry stored).
- Unresolved location check: 0 rows (every in-scope listing on this page had
  a usable map coordinate).
- Hectares by Bundesland: Mecklenburg-Vorpommern 27.51 ha (5 listings),
  Brandenburg 18.01 ha (4), Sachsen 8.50 ha (3), Sachsen-Anhalt 3.55 ha (3).
