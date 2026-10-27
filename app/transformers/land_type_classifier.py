from dataclasses import dataclass, field

OBJEKTART_LABEL_TO_SLUG: dict[str, str] = {
    "Acker und Grünland": "acker-und-gruenland",
    "Acker und Grünland (beschränkt)": "acker-und-gruenland-beschraenkt",
    "Bau- und Bauerwartungsland": "bau-und-bauerwartungsland",
    "Bauland": "bauland",
    "Bodenschätze-Ausschreibung": "bodenschaetze-ausschreibung",
    "Bodenschätze-Interessenbekundung": "bodenschaetze-interessenbekundung",
    "Erneuerbare Energien": "erneuerbare-energien",
    "Garten/Erholung/Freizeit": "garten-erholung-freizeit",
    "Gebäude/Häuser": "gebaeude-haeuser",
    "Gewässer": "gewaesser",
    "Gewerbe": "gewerbe",
    "Grundstück": "grundstueck",
    "Jagdausübungsrechte": "jagdausuebungsrechte",
    "Kompensationsflächen": "kompensationsflaechen",
    "Wald": "wald",
}

OBJEKTART_SLUG_TO_DOMAIN_TAG: dict[str, str] = {
    "acker-und-gruenland": "agricultural",
    "acker-und-gruenland-beschraenkt": "agricultural",
    "wald": "forest",
}

PEATLAND_KEYWORDS = (
    "moor",
    "torf",
    "niedermoor",
    "hochmoor",
    "wiedervernässung",
    "paludikultur",
    "vernässungsfläche",
)


@dataclass(frozen=True)
class ClassificationResult:
    objektart_slug: str | None
    domain_tags: list[str] = field(default_factory=list)
    match_basis: list[str] = field(default_factory=list)

    @property
    def in_scope(self) -> bool:
        return len(self.domain_tags) > 0


def classify_domain(
    objektart_label: str | None,
    title: str | None,
    description: str | None,
) -> ClassificationResult:
    slug = OBJEKTART_LABEL_TO_SLUG.get(objektart_label) if objektart_label else None

    tags: set[str] = set()
    basis: list[str] = []

    if slug in OBJEKTART_SLUG_TO_DOMAIN_TAG:
        tags.add(OBJEKTART_SLUG_TO_DOMAIN_TAG[slug])
        basis.append(f"objektart:{slug}")

    searchable_text = " ".join(
        part for part in (title, description, objektart_label) if part
    ).lower()

    for keyword in PEATLAND_KEYWORDS:
        if keyword in searchable_text:
            tags.add("peatland")
            basis.append(f"keyword:{keyword}")

    return ClassificationResult(
        objektart_slug=slug,
        domain_tags=sorted(tags),
        match_basis=basis,
    )
