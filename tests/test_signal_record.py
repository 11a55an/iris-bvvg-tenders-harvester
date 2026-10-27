import pytest

from app.parsers.bvvg_detail_parser import parse_detail_page
from app.parsers.bvvg_listing_parser import ListingStub
from app.transformers.signal_record import TransformationError, build_signal_record


def _stub(**overrides) -> ListingStub:
    defaults = dict(
        source_id="BB68-1800-045626",
        title="Gräben in Betzin 2",
        detail_url="https://www.bvvg.de/objekte/graeben-in-betzin-2/",
        region_subtitle="Brandenburg, Ostprignitz-Ruppin",
    )
    defaults.update(overrides)
    return ListingStub(**defaults)


def test_build_signal_record_from_real_fixture_has_no_validation_issues(
    detail_graeben_in_betzin_2_html,
):
    detail = parse_detail_page(detail_graeben_in_betzin_2_html)
    record = build_signal_record(_stub(), detail)

    assert record.source_id == "BB68-1800-045626"
    assert record.size_hectares == pytest.approx(3.02)
    assert record.domain_tags == ["agricultural"]
    assert record.location_precision == "approximate"
    assert record.validation_issues == []
    assert record.tender_end_at is not None
    assert record.tender_end_at.hour == 7


def test_build_signal_record_flags_missing_size_and_unresolved_location(
    tests_fixtures_dir,
):
    html = (tests_fixtures_dir / "detail_minimal_missing_fields.html").read_text(
        encoding="utf-8"
    )
    detail = parse_detail_page(html)
    record = build_signal_record(_stub(source_id="ZZ00-0000-000000"), detail)

    assert record.size_hectares is None
    assert "missing size_hectares" in record.validation_issues
    assert record.location_precision == "unresolved"
    assert any("location unresolved" in issue for issue in record.validation_issues)
    assert any("tender_end_at" in issue for issue in record.validation_issues)


def test_build_signal_record_flags_out_of_scope_listing():
    detail = parse_detail_page(
        """
        <html><head><link rel="canonical" href="https://www.bvvg.de/objekte/wind/"/></head>
        <body>
        <h1 class="property-title">Windpotentialflaeche</h1>
        <div class="property-details panel panel-default"><ul class="list-group">
        <li class="list-group-item"><div class="row"><div class="dt col-sm-5">Objekt-Nr.</div>
        <div class="dd col-sm-7">WP00-0000-000001</div></div></li>
        <li class="list-group-item"><div class="row"><div class="dt col-sm-5">Objektart</div>
        <div class="dd col-sm-7">Erneuerbare Energien</div></div></li>
        </ul></div>
        </body></html>
        """
    )
    record = build_signal_record(_stub(source_id="WP00-0000-000001"), detail)

    assert record.domain_tags == []
    assert "listing does not match agricultural, forest or peatland scope" in (
        record.validation_issues
    )


def test_build_signal_record_raises_without_source_id():
    detail = parse_detail_page("<html></html>")
    stub = _stub(source_id="")

    with pytest.raises(TransformationError):
        build_signal_record(stub, detail)


def test_content_hash_is_stable_for_identical_input(detail_graeben_in_betzin_2_html):
    detail = parse_detail_page(detail_graeben_in_betzin_2_html)
    record_a = build_signal_record(_stub(), detail)
    record_b = build_signal_record(_stub(), detail)

    assert record_a.content_hash == record_b.content_hash


def test_content_hash_changes_when_price_changes(detail_graeben_in_betzin_2_html):
    detail = parse_detail_page(detail_graeben_in_betzin_2_html)
    record_a = build_signal_record(_stub(), detail)

    changed_detail = detail.__class__(**{**detail.__dict__, "price_raw": "150000 EUR"})
    record_b = build_signal_record(_stub(), changed_detail)

    assert record_a.content_hash != record_b.content_hash
