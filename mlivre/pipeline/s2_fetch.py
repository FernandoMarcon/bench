"""Etapa 2: enriquece cada resultado da busca.

- Página do anúncio (Playwright): Características do produto, meios de pagamento, vendedor.
- MCP: Descrição (get_listing_description) e frete/prazo para o CEP (get_shipping_options).

Uso: python -m pipeline.s2_fetch out/<slug>/s1_search.json [--cep 01234567] [--headed]
Saída: out/<slug>/s2_items.json
"""

import argparse
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

from . import mcp_client
from .browser import open_context



def default_cep():
    """CEP de entrega: $MLIVRE_CEP ou ~/.config/mlivre/pipeline.json {"cep": "..."} (fora do git)."""
    cep = os.environ.get("MLIVRE_CEP")
    if not cep:
        cfg = Path.home() / ".config" / "mlivre" / "pipeline.json"
        if cfg.exists():
            cep = json.loads(cfg.read_text()).get("cep")
    return re.sub(r"\D", "", cep) if cep else None


CEP = default_cep()

PAGE_JS = """() => {
  const clean = t => (t || '').replace(/\\s+/g, ' ').trim();
  const specs = {};
  for (const tr of document.querySelectorAll('.ui-vpp-striped-specs tr, table.andes-table tr')) {
    const k = clean(tr.querySelector('th')?.innerText), v = clean(tr.querySelector('td')?.innerText);
    if (k && v && !(k in specs)) specs[k] = v;
  }
  const highlights = [...document.querySelectorAll('.ui-vpp-highlighted-specs__features-list li, .ui-pdp-features li')]
    .map(li => clean(li.innerText)).filter(Boolean);
  return {
    specs, highlights,
    pagamento: clean(document.querySelector('.ui-vip-payment_methods')?.innerText),
    vendedor: clean(document.querySelector('.ui-seller-data-header__title, .ui-pdp-seller__header__title')?.innerText),
    reputacao: clean(document.querySelector('.ui-seller-data-status, .ui-pdp-seller__status-info')?.innerText),
    vendidos: clean(document.querySelector('.ui-pdp-subtitle')?.innerText),
    descricao_pagina: clean(document.querySelector('.ui-pdp-description__content')?.innerText),
  };
}"""


def scrape_page(page, url):
    page.goto(url, wait_until="domcontentloaded")
    if "account-verification" in page.url:
        raise RuntimeError("Bloqueado pela verificação anti-bot")
    try:
        page.wait_for_selector(".ui-pdp-title, h1", timeout=15000)
    except Exception:
        pass
    btn = page.query_selector("button:has-text('Ver todas as características')")
    if btn:
        try:
            btn.click(timeout=3000)
            page.wait_for_timeout(500)
        except Exception:
            pass
    return page.evaluate(PAGE_JS)


def dias_ate(iso):
    if not iso:
        return None
    return (datetime.fromisoformat(iso).date() - date.today()).days


def shipping(item_id, cep):
    """Resume as opções de frete: a recomendada, a mais barata e a mais rápida."""
    data = mcp_client.call("mercado_libre_get_shipping_options",
                           {"item_id": item_id, "zip_code": cep, "quantity": 1})
    opts = []
    for o in data.get("options", []):
        edt = o.get("estimated_delivery_time") or {}
        opts.append({"tipo": o.get("shipping_method_type") or o.get("name"),
                     "custo": o.get("cost"), "custo_lista": o.get("list_cost"),
                     "prazo_dias": dias_ate(edt.get("date")), "display": o.get("display")})
    if not opts:
        return {"frete": None, "prazo_dias": None, "opcoes_frete": []}
    valid = [o for o in opts if o["custo"] is not None]
    rec = next((o for o in valid if o["display"] == "recommended"), None)
    cheapest = min(valid, key=lambda o: (o["custo"], o["prazo_dias"] if o["prazo_dias"] is not None else 99))
    fastest = min((o for o in valid if o["prazo_dias"] is not None), key=lambda o: (o["prazo_dias"], o["custo"]), default=None)
    base = rec or cheapest
    return {
        "frete": base["custo"], "prazo_dias": base["prazo_dias"], "frete_tipo": base["tipo"],
        "frete_min": cheapest["custo"], "prazo_frete_min": cheapest["prazo_dias"],
        "prazo_min": fastest["prazo_dias"] if fastest else None, "frete_prazo_min": fastest["custo"] if fastest else None,
        "opcoes_frete": opts,
    }


def description(item_id):
    d = mcp_client.call("mercado_libre_get_listing_description", {"item_id": item_id})
    return (d.get("plain_text") or d.get("text") or "").strip() if isinstance(d, dict) else str(d)


def safe(fn, *a):
    try:
        return fn(*a), None
    except Exception as e:  # registra o erro e segue para o próximo item
        return None, f"{fn.__name__}: {str(e)[:200]}"


def fetch(results, cep=CEP, headless=True):
    out = []
    with sync_playwright() as pw:
        ctx = open_context(pw, headless=headless)
        page = ctx.new_page()
        for i, r in enumerate(results, 1):
            item, errs = dict(r), []
            pg, e = safe(scrape_page, page, r["url"]); errs.append(e)
            desc, e = safe(description, r["item_id"]); errs.append(e)
            ship, e = safe(shipping, r["item_id"], cep); errs.append(e)
            item.update(pg or {})
            item["descricao"] = desc or (pg or {}).get("descricao_pagina")
            item.update(ship or {})
            item.pop("descricao_pagina", None)
            item["erros"] = [x for x in errs if x]
            out.append(item)
            print(f"[{i}/{len(results)}] {r['item_id']} specs={len(item.get('specs') or {})} "
                  f"desc={len(item['descricao'] or '')} frete={item.get('frete')} prazo={item.get('prazo_dias')} "
                  f"{'ERROS: ' + '; '.join(item['erros']) if item['erros'] else ''}", file=sys.stderr)
        ctx.close()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("s1_json")
    ap.add_argument("--cep", default=CEP)
    ap.add_argument("--n", type=int, default=None, help="processa só os N primeiros (teste)")
    ap.add_argument("--headed", action="store_true")
    a = ap.parse_args()
    if not a.cep:
        ap.error("informe --cep ou configure MLIVRE_CEP / ~/.config/mlivre/pipeline.json")
    src = Path(a.s1_json)
    s1 = json.loads(src.read_text())
    items = fetch(s1["results"][: a.n], a.cep, headless=not a.headed)
    dst = src.with_name("s2_items.json")
    dst.write_text(json.dumps({"query": s1["query"], "cep": a.cep, "items": items}, ensure_ascii=False, indent=1))
    print(f"{len(items)} itens -> {dst}", file=sys.stderr)


if __name__ == "__main__":
    main()
