from __future__ import annotations

from urllib.parse import unquote

from bs4 import BeautifulSoup


def extract_href_links(html: str) -> list[str]:
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")

    return [
        href.strip()
        for tag in soup.find_all("a", href=True)
        if (href := tag.get("href"))
    ]


def extract_mailto_links(html: str) -> list[str]:
    values: list[str] = []

    for href in extract_href_links(html):
        if not href.lower().startswith("mailto:"):
            continue

        value = unquote(href[7:])
        value = value.split("?", 1)[0].split("#", 1)[0].strip()

        if value:
            values.append(value)

    return values


def extract_tel_links(html: str) -> list[str]:
    values: list[str] = []

    for href in extract_href_links(html):
        if not href.lower().startswith("tel:"):
            continue

        value = unquote(href[4:]).strip()

        if value:
            values.append(value)

    return values