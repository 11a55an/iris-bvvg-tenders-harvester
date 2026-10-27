from app.parsers.bvvg_detail_parser import parse_detail_page


def test_parse_detail_page_extracts_all_fields(detail_graeben_in_betzin_2_html):
    record = parse_detail_page(detail_graeben_in_betzin_2_html)

    assert record.source_id == "BB68-1800-045626"
    assert record.title == "Gräben in Betzin 2"
    assert record.canonical_url == "https://www.bvvg.de/objekte/graeben-in-betzin-2/"
    assert record.bundesland == "Brandenburg"
    assert record.kreis == "Ostprignitz-Ruppin"
    assert record.gemeinde == "Fehrbellin"
    assert record.gemarkung == "Betzin"
    assert record.objektart_label == "Acker und Grünland"
    assert record.size_hectares_raw == "3,02 ha"
    assert record.marketing_type_label == "Kauf"
    assert record.price_raw == "nach Gebot"
    assert (record.tender_end_day, record.tender_end_month, record.tender_end_year) == (
        12,
        11,
        2026,
    )
    assert (record.tender_end_hour, record.tender_end_minute) == (8, 0)
    assert record.coordinate is not None
    assert record.coordinate.latitude == 52.7368
    assert record.coordinate.longitude == 12.7287
    assert record.coordinate.is_approximate is True
    assert len(record.attachment_urls) == 4
    assert any(url.endswith("_ausschreibungsbedingungen.pdf") for url in record.attachment_urls)


def test_parse_detail_page_handles_missing_optional_fields(tests_fixtures_dir):
    html = (tests_fixtures_dir / "detail_minimal_missing_fields.html").read_text(
        encoding="utf-8"
    )

    record = parse_detail_page(html)

    assert record.source_id == "ZZ00-0000-000000"
    assert record.bundesland == "Sachsen"
    assert record.size_hectares_raw is None
    assert record.price_raw is None
    assert record.tender_end_day is None
    assert record.coordinate is None
    assert record.attachment_urls == []


def test_parse_detail_page_recognizes_peatland_keyword_listing(
    tests_fixtures_dir,
):
    html = (tests_fixtures_dir / "detail_peatland_keyword.html").read_text(encoding="utf-8")

    record = parse_detail_page(html)

    assert record.source_id == "PE01-1800-000111"
    assert record.objektart_label == "Kompensationsflächen"
    assert "Niedermoor" in record.description
    assert record.coordinate is not None
    assert record.coordinate.latitude == 51.05
    assert record.coordinate.longitude == 13.74


def test_parse_detail_page_on_empty_html_returns_all_none_fields():
    record = parse_detail_page("")

    assert record.source_id is None
    assert record.title is None
    assert record.coordinate is None
    assert record.attachment_urls == []
