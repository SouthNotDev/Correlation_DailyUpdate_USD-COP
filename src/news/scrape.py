"""Scraper ligero para obtener artículos relevantes sobre USD/COP.

Briefing rápido:
- `load_sources_csv` lee la lista de medios (`info_sources.csv`).
- `find_candidate_links` explora cada homepage y devuelve enlaces únicos.
- `extract_article` descarga un enlace y extrae título, resumen y cuerpo.
- `scrape_sources` es la función principal; filtra enlaces por keywords,
  descarga los artículos, los guarda en JSONL y retorna la lista.
- `main` expone un CLI simple para ejecutar el scraper de forma aislada.

La meta es mantener un flujo claro y eficiente que produzca datos listos para
el briefing diario sin añadir dependencias complejas.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
import unicodedata
from pathlib import Path
from typing import Iterable

import requests
from bs4 import BeautifulSoup

from src.utils.io import ensure_dir


# Cabecera sencilla para que los sitios respondan como si fuera un navegador.
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122 Safari/537.36"
}


def strip_accents(s: str) -> str:
    """Elimina acentos del texto para facilitar el matching de palabras clave."""

    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def load_sources_csv(path: str | Path) -> list[dict]:
    """Carga el CSV de fuentes y devuelve una lista de diccionarios simples."""

    out = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = (row.get("url") or "").strip()
            if not url:
                continue
            out.append({"source": row.get("source", "unknown"), "url": url})
    return out


def find_candidate_links(html: str, base_url: str) -> list[tuple[str, str]]:
    """Devuelve enlaces únicos (href, texto) encontrados dentro del HTML."""

    soup = BeautifulSoup(html, "lxml")
    links: list[tuple[str, str]] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = (a.get_text(strip=True) or "").strip()
        if not href:
            continue
        if href.startswith("/") and base_url:
            href = base_url.rstrip("/") + href  # Construir URL absoluta.
        if not href.startswith("http"):
            continue
        links.append((href, text))

    seen = set()
    uniq: list[tuple[str, str]] = []
    for href, text in links:
        if href in seen:
            continue
        seen.add(href)
        uniq.append((href, text))
    return uniq


def keyword_match(text: str, keywords_norm: set[str]) -> bool:
    """Indica si alguna keyword normalizada está contenida en el texto dado."""

    t = strip_accents(text.lower())
    for k in keywords_norm:
        if k in t:
            return True
    return False


def extract_article(url: str, timeout: int = 10) -> dict | None:
    """Descarga un artículo y devuelve un dict con campos básicos para el briefing."""

    try:
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        if r.status_code != 200:
            return None
    except Exception:
        return None

    soup = BeautifulSoup(r.text, "lxml")

    # Título
    title = None
    for key in ["og:title", "twitter:title"]:
        tag = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
        if tag and tag.get("content"):
            title = tag["content"].strip()
            break
    if not title and soup.title and soup.title.string:
        title = soup.title.string.strip()

    # Descripción o bajada
    desc = None
    for key in ["og:description", "twitter:description", "description"]:
        tag = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
        if tag and tag.get("content"):
            desc = tag["content"].strip()
            break

    # Fecha de publicación (best-effort)
    pub = None
    for key in [
        ("meta", {"property": "article:published_time"}),
        ("meta", {"name": "date"}),
        ("time", {"datetime": True}),
    ]:
        tag = soup.find(key[0], attrs=key[1])
        if tag:
            pub = tag.get("content") or tag.get("datetime") or tag.get("value")
            if pub:
                pub = pub.strip()
                break

    # Cuerpo del artículo
    text_blocks: list[str] = []
    article_tag = soup.find("article")
    if article_tag:
        text_blocks = [p.get_text(" ", strip=True) for p in article_tag.find_all("p")]
    if not text_blocks:
        text_blocks = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    text = "\n".join([t for t in text_blocks if t])

    return {
        "url": url,
        "title": title,
        "description": desc,
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
    """Orquesta el scraping completo y guarda un `articles.jsonl` en `out_dir`."""

    ensure_dir(out_dir)
    sources = load_sources_csv(sources_csv)
    kw_norm = {strip_accents(k.lower()) for k in keywords}
    all_items: list[dict] = []

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
        filtered: list[str] = []
        for url in candidates:
            if url in seen:
                continue
            seen.add(url)
            filtered.append(url)

        filtered = filtered[:max_per_source]

        for url in filtered:
            item = extract_article(url, timeout=timeout)
            if not item:
                continue
            item["source"] = source.get("source")
            all_items.append(item)
            time.sleep(0.5)  # Pequeña pausa para no abusar de las fuentes.

    out_path = Path(out_dir) / "articles.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for item in all_items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    return all_items


def main() -> None:
    """CLI minimalista para ejecutar el scraper desde la terminal."""

    parser = argparse.ArgumentParser(description="Scrape news from sources CSV with keyword filtering.")
    parser.add_argument("--sources", required=True, help="Path to info_sources.csv")
    parser.add_argument("--keywords", nargs="*", default=["peso", "dólar", "USDCOP"]) 
    parser.add_argument("--out", required=True, help="Output directory for JSONL")
    args = parser.parse_args()

    scrape_sources(args.sources, args.keywords, args.out)


if __name__ == "__main__":
    main()
