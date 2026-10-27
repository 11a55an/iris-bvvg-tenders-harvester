import pytest

from app.transformers.signal_record import _parse_size_hectares


def test_parse_size_hectares_with_simple_decimal_comma():
    issues = []
    assert _parse_size_hectares("3,02 ha", issues) == pytest.approx(3.02)
    assert issues == []


def test_parse_size_hectares_with_thousands_separator():
    issues = []
    assert _parse_size_hectares("1.234,56 ha", issues) == pytest.approx(1234.56)
    assert issues == []


def test_parse_size_hectares_converts_square_meters_to_hectares():
    issues = []
    assert _parse_size_hectares("859.803 m²", issues) == pytest.approx(85.9803)
    assert issues == []


def test_parse_size_hectares_converts_square_meters_ascii_unit():
    issues = []
    assert _parse_size_hectares("2.247.145 m2", issues) == pytest.approx(224.7145)
    assert issues == []


def test_parse_size_hectares_missing_value_adds_issue():
    issues = []
    assert _parse_size_hectares(None, issues) is None
    assert issues == ["missing size_hectares"]


def test_parse_size_hectares_unrecognized_unit_adds_issue():
    issues = []
    assert _parse_size_hectares("3,02 acres", issues) is None
    assert "unrecognized size unit" in issues[0]
