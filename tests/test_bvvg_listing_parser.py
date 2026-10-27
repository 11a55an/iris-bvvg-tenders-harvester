from app.parsers.bvvg_listing_parser import parse_listing_stubs, parse_pagination


def test_parse_listing_stubs_extracts_all_cards(listing_page_1_html):
    stubs = parse_listing_stubs(listing_page_1_html)

    assert len(stubs) == 20
    first = stubs[0]
    assert first.source_id == "AM88-1800-067026"
    assert first.title == "Schmon-Streulage"
    assert first.detail_url == "https://www.bvvg.de/objekte/schmon-streulage/"
    assert first.region_subtitle == "Sachsen-Anhalt, Saalekreis"


def test_parse_listing_stubs_returns_empty_list_for_malformed_html():
    stubs = parse_listing_stubs("<html><body>no listings here</body></html>")

    assert stubs == []


def test_parse_listing_stubs_skips_cards_missing_required_fields():
    html = """
    <div class="property-container" id="xx1-1">
        <h3 class="property-title"><a>missing href</a></h3>
    </div>
    <div class="property-container" id="xx2-2">
        <h3 class="property-title"><a href="/objekte/ok/">Ok Listing</a></h3>
    </div>
    """
    stubs = parse_listing_stubs(html)

    assert len(stubs) == 1
    assert stubs[0].source_id == "XX2-2"


def test_parse_pagination_reads_total_pages_and_results(listing_page_1_html):
    pagination = parse_pagination(listing_page_1_html, requested_page=1)

    assert pagination.current_page == 1
    assert pagination.total_pages == 5
    assert pagination.total_results == 95


def test_parse_pagination_defaults_to_single_page_without_paginator():
    pagination = parse_pagination("<html><body>empty</body></html>", requested_page=1)

    assert pagination.total_pages == 1
    assert pagination.total_results is None
