import re
from dataclasses import dataclass

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class ListingStub:
    source_id: str
    title: str
    detail_url: str
    region_subtitle: str | None


@dataclass(frozen=True)
class PaginationInfo:
    current_page: int
    total_pages: int
    total_results: int | None


class ListingPageParseError(Exception):
    pass


def parse_listing_stubs(html: str) -> list[ListingStub]:
    soup = BeautifulSoup(html, "html.parser")
    containers = soup.select("div.property-container")

    stubs: list[ListingStub] = []
    for container in containers:
        source_id = container.get("id")
        title_link = container.select_one("h3.property-title a")
        subtitle_tag = container.select_one("div.property-subtitle")

        if not source_id or not title_link or not title_link.get("href"):
            continue

        stubs.append(
            ListingStub(
                source_id=source_id.strip().upper(),
                title=title_link.get_text(strip=True),
                detail_url=title_link["href"].strip(),
                region_subtitle=(
                    subtitle_tag.get_text(strip=True) if subtitle_tag else None
                ),
            )
        )

    return stubs


def parse_pagination(html: str, requested_page: int) -> PaginationInfo:
    soup = BeautifulSoup(html, "html.parser")
    paginator = soup.select_one("div.paginator")

    if not paginator:
        return PaginationInfo(
            current_page=requested_page, total_pages=requested_page, total_results=None
        )

    total_results = None
    num_posts = paginator.select_one("div.num-posts")
    if num_posts:
        match = re.search(r"von\s+(\d+)", num_posts.get_text())
        if match:
            total_results = int(match.group(1))

    page_numbers = [
        int(tag.get_text(strip=True))
        for tag in paginator.select("a.page-numbers, span.page-numbers")
        if tag.get_text(strip=True).isdigit()
    ]
    total_pages = max(page_numbers) if page_numbers else requested_page

    return PaginationInfo(
        current_page=requested_page,
        total_pages=total_pages,
        total_results=total_results,
    )
