"""Etapa 1: query -> lista de anúncios da página de busca do Mercado Livre.

Uso: python -m pipeline.s1_search "horn aluminio 25t servo" [--n 20] [--headed]
Saída: out/<slug>/s1_search.json
"""

import argparse
import json
import re
import sys
import unicodedata
import urllib.parse
from pathlib import Path

from playwright.sync_api import sync_playwright

from .browser import open_context

OUT = Path(__file__).resolve().parent.parent / "out"


def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def search_url(query):
    return f"https://lista.mercadolivre.com.br/{slugify(query)}"


def parse_ids(href):
    """Extrai (item_id, catalog_product_id) do link de um card."""
    url = urllib.parse.unquote(href or "")
    item = re.search(r"(?:wid=|item_id[:=])(MLB\d+)", url) or re.search(r"/(MLB)-(\d+)", url)
    if item and item.lastindex == 2:
        item_id = item.group(1) + item.group(2)
    else:
        item_id = item.group(1) if item else None
    cat = re.search(r"/p/(MLB\d+)", url)
    return item_id, cat.group(1) if cat else None


def money(el):
    """Converte um bloco andes-money-amount em float."""
    if not el:
        return None
    frac = el.query_selector(".andes-money-amount__fraction")
    cents = el.query_selector(".andes-money-amount__cents")
    if not frac:
        return None
    val = frac.inner_text().replace(".", "")
    return float(f"{val}.{cents.inner_text() if cents else '00'}")


def text(card, sel):
    el = card.query_selector(sel)
    if not el:
        return None
    t = " ".join(el.inner_text().split())
    t = re.sub(r"(\d) , (\d)", r"\1,\2", t)          # "136 , 80" -> "136,80"
    t = re.sub(r"\b(.+?) \1\b", r"\1", t)             # "Frete grátis Frete grátis" -> "Frete grátis"
    return t


def parse_card(card):
    link = card.query_selector("a.poly-component__title") or card.query_selector("a")
    href = link.get_attribute("href") if link else None
    item_id, catalog_id = parse_ids(href)
    return {
        "item_id": item_id,
        "catalog_product_id": catalog_id,
        "titulo": " ".join(link.inner_text().split()) if link else None,
        "preco": money(card.query_selector(".poly-price__current .andes-money-amount")),
        "preco_original": money(card.query_selector(".andes-money-amount--previous")),
        "desconto": text(card, ".poly-price__discount-polylabel, .andes-money-amount__discount"),
        "parcelas": text(card, ".poly-price__installments"),
        "frete_card": text(card, ".poly-component__shipping-v2, .poly-component__shipping"),
        "internacional": bool(card.query_selector(".poly-component__cbt")),
        "patrocinado": bool(card.query_selector(".poly-component__ads-promotions")),
        "url": clean_url(href, item_id),
    }


def clean_url(href, item_id):
    """Remove o rastreamento de clique dos anúncios patrocinados."""
    url = (href or "").split("#")[0]
    if "click1.mercadolivre" in url and item_id:
        return f"https://produto.mercadolivre.com.br/MLB-{item_id[3:]}"
    return url


def search(query, n=20, headless=True):
    with sync_playwright() as pw:
        ctx = open_context(pw, headless=headless)
        page = ctx.new_page()
        page.goto(search_url(query), wait_until="domcontentloaded")
        if "account-verification" in page.url:
            raise RuntimeError(f"Bloqueado pela verificação anti-bot: {page.url}")
        page.wait_for_selector(".poly-card, .ui-search-rescue", timeout=20000)
        cards = page.query_selector_all("li.ui-search-layout__item .poly-card") or page.query_selector_all(".poly-card")
        results = [parse_card(c) for c in cards]
        ctx.close()
    seen, unique = set(), []
    for r in results:
        key = r["item_id"] or r["url"]
        if key and key not in seen:
            seen.add(key)
            unique.append(r)
    return unique[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--headed", action="store_true")
    a = ap.parse_args()
    res = search(a.query, a.n, headless=not a.headed)
    out = OUT / slugify(a.query)
    out.mkdir(parents=True, exist_ok=True)
    (out / "s1_search.json").write_text(json.dumps({"query": a.query, "results": res}, ensure_ascii=False, indent=1))
    for r in res:
        print(f"{r['item_id'] or '?':15} {r['catalog_product_id'] or '-':12} R$ {r['preco'] or '?':>8}  {(r['titulo'] or '')[:70]}")
    print(f"\n{len(res)} resultados -> {out / 's1_search.json'}", file=sys.stderr)


if __name__ == "__main__":
    main()
