"""Roda as 4 etapas para uma query.

Uso:
  python -m pipeline.run "Servo Horn metálico 25T" --qtd 3 --contexto "para MG996R, braço único"
Saída: out/<slug>/{s1_search.json, s2_items.json, s3_matched.json, resultado.csv}
"""

import argparse
import json
import sys

from . import s1_search, s2_fetch, s3_match, s4_rank


def run(query, n=20, cep=s2_fetch.CEP, qtd=1, contexto="", model="sonnet", todos=False):
    out = s1_search.OUT / s1_search.slugify(query)
    out.mkdir(parents=True, exist_ok=True)

    print(f"[1/4] buscando '{query}'...", file=sys.stderr)
    results = s1_search.search(query, n)
    (out / "s1_search.json").write_text(json.dumps({"query": query, "results": results}, ensure_ascii=False, indent=1))

    print(f"[2/4] detalhando {len(results)} anúncios...", file=sys.stderr)
    items = s2_fetch.fetch(results, cep)
    (out / "s2_items.json").write_text(json.dumps({"query": query, "cep": cep, "items": items}, ensure_ascii=False, indent=1))

    print("[3/4] avaliando match com o Claude...", file=sys.stderr)
    ctx = f"CONTEXTO ADICIONAL: {contexto}\n" if contexto else ""
    items, cost = s3_match.match(query, items, model, ctx)
    (out / "s3_matched.json").write_text(json.dumps({"query": query, "cep": cep, "items": items}, ensure_ascii=False, indent=1))

    print("[4/4] ranqueando...", file=sys.stderr)
    rows = s4_rank.rank(items, qtd, todos)
    s4_rank.to_csv(rows, out / "resultado.csv")
    print(f"{len(rows)} anúncios no CSV (custo LLM US$ {cost:.3f}) -> {out / 'resultado.csv'}", file=sys.stderr)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--cep", default=s2_fetch.CEP)
    ap.add_argument("--qtd", type=int, default=1)
    ap.add_argument("--contexto", default="")
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--todos", action="store_true")
    a = ap.parse_args()
    if not a.cep:
        ap.error("informe --cep ou configure MLIVRE_CEP / ~/.config/mlivre/pipeline.json")
    rows = run(a.query, a.n, a.cep, a.qtd, a.contexto, a.model, a.todos)
    for r in rows[:10]:
        print(f"{r['score']:6.1f}  R$ {r['custo_total'] or 0:8.2f}  {r.get('prazo_dias')}d  {(r['titulo'] or '')[:60]}  {r['url']}")


if __name__ == "__main__":
    main()
