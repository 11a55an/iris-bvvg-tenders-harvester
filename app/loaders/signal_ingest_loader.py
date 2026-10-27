from dataclasses import dataclass, field

from app.database.repositories.signal_ingest_repository import SignalIngestRepository
from app.transformers.signal_record import SignalRecord


@dataclass
class QualityReport:
    total_candidates: int = 0
    in_scope: int = 0
    out_of_scope: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    unresolved_locations: int = 0
    per_record_issues: dict[str, list[str]] = field(default_factory=dict)


class SignalIngestLoader:
    def __init__(self, repository: SignalIngestRepository):
        self._repository = repository

    def load(self, records: list[SignalRecord]) -> QualityReport:
        report = QualityReport(total_candidates=len(records))
        in_scope_records: list[SignalRecord] = []

        for record in records:
            if record.validation_issues:
                report.per_record_issues[record.source_id] = list(record.validation_issues)

            if record.location_precision == "unresolved":
                report.unresolved_locations += 1

            if record.domain_tags:
                report.in_scope += 1
                in_scope_records.append(record)
            else:
                report.out_of_scope += 1

        summary = self._repository.upsert_many(in_scope_records)
        report.inserted = summary.inserted
        report.updated = summary.updated
        report.unchanged = summary.unchanged

        return report
