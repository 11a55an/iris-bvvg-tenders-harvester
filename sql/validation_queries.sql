-- Row counts by domain tag, confirms domain filtering matches the objective scope.
select unnest(domain_tags) as domain_tag, count(*)
from iris_staging.signal_ingest
group by 1
order by 1;

-- Duplicate check on the natural key, must always return zero rows.
select source_system, source_id, count(*)
from iris_staging.signal_ingest
group by source_system, source_id
having count(*) > 1;

-- Listings with an unresolved or missing location, for manual geocoding review.
select source_id, title, bundesland, landkreis, gemeinde, location_precision, location_note
from iris_staging.signal_ingest
where location_precision = 'unresolved'
order by source_id;

-- Coordinate sanity check, flags anything stored outside the plausible German
-- EPSG:25832 envelope even though the loader should already reject these.
select source_id, title, ST_AsText(location_point)
from iris_staging.signal_ingest
where location_point is not null
  and not (
    ST_X(location_point) between 100000 and 900000
    and ST_Y(location_point) between 5200000 and 6100000
  );

-- Records with open data quality issues, for the error and quality report.
select source_id, title, validation_issues
from iris_staging.signal_ingest
where array_length(validation_issues, 1) > 0
order by source_id;

-- Upcoming tender deadlines, most urgent first.
select source_id, title, bundesland, size_hectares, tender_end_at
from iris_staging.signal_ingest
where tender_end_at is not null
order by tender_end_at asc;

-- Total hectares in scope by Bundesland, for a quick coverage sanity check.
select bundesland, count(*) as listing_count, round(sum(size_hectares), 2) as total_hectares
from iris_staging.signal_ingest
where size_hectares is not null
group by bundesland
order by total_hectares desc;
