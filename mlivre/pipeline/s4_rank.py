"""Etapa 4: filtra os matches exatos, calcula o score de custo-benefício e grava o CSV.

score (0–100) = 50·precisão + 30·(1−total_norm) + 10·(1−preço_norm) + 10·(1−prazo_norm)
  total = ceil(qtd/unidades)·preço + frete   (custo para comprar a quantidade necessária)
  *_norm = min-max entre os itens filtrados (menor é melhor)

Uso: python -m pipeline.s4_rank out/<slug>/s3_matched.json [--qtd 3] [--todos]
Saída: out/<slug>/resultado.csv
"""

import argparse
import csv
import json
import math
import sys
from pathlib import Path

PESOS = {"precisao": 50, "total": 30, "preco": 10, "prazo": 10}

COLUNAS = [
    "titulo", "score", "precisao", "match_exato", "unidades", "qtd_anuncios", "custo_total", "custo_unitario",
    "preco", "frete", "prazo_dias", "frete_tipo", "frete_min", "prazo_frete_min", "prazo_min",
    "preco_original", "desconto", "parcelas", "pagamento", "vendedor", "vendidos", "internacional",
    "patrocinado", "motivo", "caracteristicas", "descricao", "item_id", "catalog_product_id", "url",
]


def norm(values):
    """Normaliza para 0..1 (None vira 1 = pior). Se todos iguais, 0."""
    known = [v for v in values if v is not None]
    if not known:
        return [1.0 for _ in values]
    lo, hi = min(known), max(known)
    return [1.0 if v is None else (0.0 if hi == lo else (v - lo) / (hi - lo)) for v in values]


def rank(items, qtd=1, todos=False):
    rows = [dict(i) for i in items if todos or i.get("match_exato")]
    for r in rows:
        un = max(int(r.get("unidades") or 1), 1)
        r["qtd_anuncios"] = math.ceil(qtd / un)
        frete = r.get("frete") or 0
        r["custo_total"] = round(r["qtd_anuncios"] * (r.get("preco") or 0) + frete, 2) if r.get("preco") else None
        r["custo_unitario"] = round(r["preco"] / un, 2) if r.get("preco") else None
    n_total = norm([r["custo_total"] for r in rows])
    n_preco = norm([r.get("preco") for r in rows])
    n_prazo = norm([r.get("prazo_dias") for r in rows])
    for r, t, p, d in zip(rows, n_total, n_preco, n_prazo):
        r["score"] = round(PESOS["precisao"] * (r.get("precisao") or 0) + PESOS["total"] * (1 - t)
                           + PESOS["preco"] * (1 - p) + PESOS["prazo"] * (1 - d), 1)
        if not r.get("match_exato"):
            r["score"] = round(r["score"] - 100, 1)  # rejeitados sempre no fim (com --todos)
    # desempate explícito: precisão > total > preço > prazo
    rows.sort(key=lambda r: (-r["score"], -(r.get("precisao") or 0), r["custo_total"] or 1e9,
                             r.get("preco") or 1e9, r.get("prazo_dias") if r.get("prazo_dias") is not None else 99))
    return rows


def to_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig: abre certo no Excel/LibreOffice
        w = csv.DictWriter(f, fieldnames=COLUNAS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            r = dict(r)
            r["caracteristicas"] = "; ".join(f"{k}: {v}" for k, v in (r.get("specs") or {}).items())
            r["descricao"] = " ".join((r.get("descricao") or "").split())
            w.writerow(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("s3_json")
    ap.add_argument("--qtd", type=int, default=1, help="quantidade de peças necessária")
    ap.add_argument("--todos", action="store_true", help="inclui os rejeitados no fim do CSV")
    a = ap.parse_args()
    src = Path(a.s3_json)
    s3 = json.loads(src.read_text())
    rows = rank(s3["items"], a.qtd, a.todos)
    dst = src.with_name("resultado.csv")
    to_csv(rows, dst)
    for r in rows:
        print(f"{r['score']:6.1f}  prec {r['precisao']:.2f}  x{r['unidades']:<2} total R$ {r['custo_total'] or 0:8.2f}  "
              f"preço {r['preco'] or 0:7.2f}  frete {r.get('frete') or 0:5.2f}  {r.get('prazo_dias')}d  {(r['titulo'] or '')[:45]}")
    print(f"\n{len(rows)} linhas -> {dst}", file=sys.stderr)


if __name__ == "__main__":
    main()
