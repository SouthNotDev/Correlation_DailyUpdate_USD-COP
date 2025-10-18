"""Lightweight scraper that collects news relevant to USD/COP movements.

Key features:
- Load a list of sources from `info_sources.csv`.
- Discover candidate links on each source homepage.
- Fetch articles defensively, skipping binary responses such as PDFs.
- Score articles for currency relevance, rewarding FX terms and penalising noise.
- Clean output text to strip control characters before saving JSONL.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
import unicodedata
from pathlib import Path
from typing import Iterable

import requests
from bs4 import BeautifulSoup

from src.utils.io import ensure_dir


DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122 Safari/537.36"
}

# Relevance keywords
KEYWORDS_STRONG = {
    "usd/cop",
    "usdcop",
    "usd cop",
    "trm",
    "tasa representativa",
    "peso colombiano",
    "dolar en colombia",
    "tipo de cambio",
    "devaluacion",
    "revaluacion",
}

KEYWORDS_DOLLAR = {
    "dolar",
    "usd",
    "billete verde",
}

KEYWORDS_MACRO = {
    "banrep",
    "banco de la republica",
    "inflacion",
    "tasas",
    "interes",
    "mercado cambiario",
    "divisas",
    "emergentes",
    "fed",
    "riesgo pais",
    "bonos",
    "tes",
}

KEYWORDS_NEGATIVE = {
    "gafas",
    "tecnologia",
    "videojuego",
    "moda",
    "celebridad",
    "futbol",
    "baloncesto",
    "musica",
    "entretenimiento",
    "espectaculo",
    "smartphone",
    "gadget",
}

RELEVANCE_THRESHOLD = 3


def strip_accents(value: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", value) if unicodedata.category(ch) != "Mn")


def load_sources_csv(path: str | Path) -> list[dict]:
    rows: list[dict] = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            url = (row.get("url") or "").strip()
            if not url:
                continue
            rows.append({"source": row.get("source", "unknown"), "url": url})
    return rows


def find_candidate_links(html: str, base_url: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    out: list[tuple[str, str]] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        text = (anchor.get_text(strip=True) or "").strip()
        if not href:
            continue
        if href.startswith("/") and base_url:
            href = base_url.rstrip("/") + href
        if not href.startswith("http"):
            continue
        out.append((href, text))

    seen = set()
    uniq: list[tuple[str, str]] = []
    for href, text in out:
        if href in seen:
            continue
        seen.add(href)
        uniq.append((href, text))
    return uniq


def keyword_match(text: str, keywords_norm: set[str]) -> bool:
    norm = strip_accents(text.lower())
    return any(term in norm for term in keywords_norm)


def clean_text(value: str | None) -> str | None:
    if not value:
        return value
    cleaned = "".join(ch for ch in value if ch.isprintable() or ch in "\n\r\t")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\r?\n\s*", "\n", cleaned)
    return cleaned.strip()


def count_terms(text: str, terms: set[str]) -> int:
    norm = strip_accents(text.lower())
    return sum(norm.count(term) for term in terms)


def score_article(item: dict) -> int:
    title = clean_text(item.get("title") or "") or ""
    desc = clean_text(item.get("description") or "") or ""
    text = clean_text(item.get("text") or "") or ""
    head = f"{title} {desc}"
    combined = f"{head} {text}"

    strong_hits = count_terms(combined, KEYWORDS_STRONG)
    dollar_hits = count_terms(combined, KEYWORDS_DOLLAR)
    macro_hits = count_terms(combined, KEYWORDS_MACRO)
    negative_head = count_terms(head, KEYWORDS_NEGATIVE)
    negative_text = count_terms(text[:400], KEYWORDS_NEGATIVE)

    score = strong_hits * 3
    score += min(dollar_hits, 3) * 2
    score += min(macro_hits, 3)
    if dollar_hits and macro_hits:
        score += 2
    score -= negative_head * 2
    score -= negative_text

    if not title:
        score -= 1
    if len(text.split()) < 40:
        score -= 1
    return score


def extract_article(url: str, timeout: int = 10) -> dict | None:
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    except Exception:
        return None
    if resp.status_code != 200:
        return None

    content_type = resp.headers.get("Content-Type", "").lower()
    if not content_type.startswith("text/") and "html" not in content_type:
        return None

    soup = BeautifulSoup(resp.text, "lxml")

    title = None
    for key in ("og:title", "twitter:title"):
        tag = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
        if tag and tag.get("content"):
            title = tag["content"].strip()
            break
    if not title and soup.title and soup.title.string:
        title = soup.title.string.strip()

    desc = None
    for key in ("og:description", "twitter:description", "description"):
        tag = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
        if tag and tag.get("content"):
            desc = tag["content"].strip()
            break

    pub = None
    for selector in (("meta", {"property": "article:published_time"}), ("meta", {"name": "date"}), ("time", {"datetime": True})):
        tag = soup.find(selector[0], attrs=selector[1])
        if tag:
            pub = tag.get("content") or tag.get("datetime") or tag.get("value")
            if pub:
                pub = pub.strip()
                break

    text_blocks: list[str] = []
    article_tag = soup.find("article")
    if article_tag:
        text_blocks = [p.get_text(" ", strip=True) for p in article_tag.find_all("p")]
    if not text_blocks:
        text_blocks = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    text = "\n".join([t for t in text_blocks if t])

    text = clean_text(text)
    if not text:
        return None

    return {
        "url": url,
        "title": clean_text(title),
        "description": clean_text(desc),
        "published": pub,
        "text": text,
    }


def scrape_sources(
    sources_csv: str | Path,
    keywords: Iterable[str],
    out_dir: str | Path,
    max_per_source: int = 20,
    timeout: int = 10,
) -> list[dict]:
    ensure_dir(out_dir)
    sources = load_sources_csv(sources_csv)
    kw_norm = {strip_accents(k.lower()) for k in keywords}
    collected: list[dict] = []

    for source in sources:
        base = source["url"].rstrip("/")
        try:
            resp = requests.get(base, headers=DEFAULT_HEADERS, timeout=timeout)
            if resp.status_code != 200:
                continue
        except Exception:
            continue

        links = find_candidate_links(resp.text, base)

        candidates: list[str] = []
        for href, text in links:
            parts = [text or "", Path(href).name.replace("-", " ")]
            joined = " ".join(parts)
            if keyword_match(joined, kw_norm):
                candidates.append(href)

        seen = set()
        unique_candidates: list[str] = []
        for href in candidates:
            if href in seen:
                continue
            seen.add(href)
            unique_candidates.append(href)

        for url in unique_candidates[:max_per_source]:
            item = extract_article(url, timeout=timeout)
            if not item:
                continue
            score = score_article(item)
            if score < RELEVANCE_THRESHOLD:
                continue
            item["source"] = source.get("source")
            item["relevance_score"] = score
            collected.append(item)
            time.sleep(0.5)

    out_path = Path(out_dir) / "articles.jsonl"
    with open(out_path, "w", encoding="utf-8") as fh:
        for item in collected:
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")
    return collected


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape news from sources CSV with keyword filtering.")
    parser.add_argument("--sources", required=True, help="Path to info_sources.csv")
    parser.add_argument("--keywords", nargs="*", default=["peso", "dolar", "USDCOP"])
    parser.add_argument("--out", required=True, help="Output directory for JSONL")
    args = parser.parse_args()

    scrape_sources(args.sources, args.keywords, args.out)


if __name__ == "__main__":
    main()
