from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def read_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


@pytest.fixture
def listing_page_1_html() -> str:
    return read_fixture("listing_page_1.html")


@pytest.fixture
def detail_graeben_in_betzin_2_html() -> str:
    return read_fixture("detail_graeben_in_betzin_2.html")


@pytest.fixture
def tests_fixtures_dir() -> Path:
    return FIXTURES_DIR
