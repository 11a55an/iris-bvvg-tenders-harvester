from app.transformers.land_type_classifier import classify_domain


def test_classify_domain_matches_agricultural_objektart():
    result = classify_domain("Acker und Grünland", "Irgendein Titel", None)

    assert result.in_scope is True
    assert result.domain_tags == ["agricultural"]
    assert "objektart:acker-und-gruenland" in result.match_basis


def test_classify_domain_matches_forest_objektart():
    result = classify_domain("Wald", "Waldflaeche bei Beispielstadt", None)

    assert result.in_scope is True
    assert result.domain_tags == ["forest"]


def test_classify_domain_matches_peatland_by_keyword_despite_other_objektart():
    result = classify_domain(
        "Kompensationsflächen", "Niedermoor Renaturierung", "Wiedervernässung einer Moorfläche"
    )

    assert result.in_scope is True
    assert "peatland" in result.domain_tags


def test_classify_domain_excludes_renewable_energy_listings():
    result = classify_domain("Erneuerbare Energien", "Windpotentialflaechen Woosten", None)

    assert result.in_scope is False
    assert result.domain_tags == []


def test_classify_domain_handles_missing_objektart_label():
    result = classify_domain(None, "Titel ohne Objektart", "Beschreibung ohne Hinweise")

    assert result.in_scope is False
    assert result.objektart_slug is None
