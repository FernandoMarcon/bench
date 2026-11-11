"""Etapa 3: avalia, com o Claude, se cada anúncio corresponde exatamente à query.

Usa `claude -p` (assinatura do Claude Code) com saída estruturada.
Prioridade das evidências: Características do produto > Descrição > Título.

Uso: python -m pipeline.s3_match out/<slug>/s2_items.json [--model sonnet]
Saída: out/<slug>/s3_matched.json
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

BATCH = 10
DESC_MAX = 1500

SCHEMA = {
    "type": "object",
    "properties": {
        "avaliacoes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item_id": {"type": "string"},
                    "precisao": {"type": "number", "minimum": 0, "maximum": 1},
                    "match_exato": {"type": "boolean"},
                    "unidades": {"type": "integer", "minimum": 1},
                    "motivo": {"type": "string"},
                },
                "required": ["item_id", "precisao", "match_exato", "unidades", "motivo"],
            },
        }
    },
    "required": ["avaliacoes"],
}

PROMPT = """Você avalia anúncios do Mercado Livre para uma lista de compras de componentes de um projeto.

ITEM PROCURADO (query): {query}
{contexto}
Para CADA anúncio abaixo, decida se o produto vendido corresponde EXATAMENTE ao item procurado.

Regras:
- Evidências em ordem de confiança: 1) "caracteristicas" (ficha técnica), 2) "descricao", 3) "titulo".
  Se houver conflito, vale a fonte de maior confiança. Títulos costumam ser genéricos ou cheios de palavras-chave.
- Todas as especificações da query devem bater (ex.: material, número de dentes/estrias, tensão, dimensão, modelo).
  Uma especificação contraditória (ex.: plástico em vez de metálico, 24T em vez de 25T) => match_exato=false.
- Especificação não confirmada em nenhuma fonte reduz a precisão, mas não elimina sozinha.
- Produto de outra categoria (ex.: o servo em vez do horn do servo) => precisao perto de 0.
- precisao: 1.0 = todas as specs confirmadas na ficha/descrição; 0.7–0.9 = compatível, com alguma spec só no título
  ou não confirmada; <0.5 = provavelmente outro produto.
- unidades: quantas peças do item procurado vêm no anúncio (kit de 4 => 4). Se não estiver claro, 1.
- motivo: uma frase curta em português citando a evidência decisiva.

Devolva uma avaliação por anúncio, com o mesmo item_id.

ANÚNCIOS (JSON):
{itens}
"""


def compact(it):
    specs = dict(it.get("specs") or {})
    return {
        "item_id": it["item_id"],
        "titulo": it.get("titulo"),
        "caracteristicas": specs,
        "destaques": it.get("highlights") or [],
        "descricao": (it.get("descricao") or "")[:DESC_MAX],
    }


def judge(query, batch, model, contexto=""):
    prompt = PROMPT.format(query=query, contexto=contexto,
                           itens=json.dumps([compact(i) for i in batch], ensure_ascii=False, indent=1))
    proc = subprocess.run(
        ["claude", "-p", "--model", model, "--output-format", "json", "--json-schema", json.dumps(SCHEMA)],
        input=prompt, capture_output=True, text=True, timeout=600,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-500:] or proc.stdout[-500:])
    out = json.loads(proc.stdout)
    if out.get("is_error") or not out.get("structured_output"):
        raise RuntimeError(str(out.get("result"))[:500])
    return out["structured_output"]["avaliacoes"], out.get("total_cost_usd", 0)


def match(query, items, model="sonnet", contexto=""):
    by_id, cost = {}, 0.0
    for i in range(0, len(items), BATCH):
        batch = items[i:i + BATCH]
        avals, c = judge(query, batch, model, contexto)
        cost += c or 0
        by_id.update({a["item_id"]: a for a in avals})
        print(f"lote {i // BATCH + 1}: {len(avals)} avaliações (US$ {c:.3f})", file=sys.stderr)
    out = []
    for it in items:
        a = by_id.get(it["item_id"], {"precisao": None, "match_exato": None, "unidades": 1, "motivo": "sem avaliação"})
        out.append({**it, **{k: a[k] for k in ("precisao", "match_exato", "unidades", "motivo")}})
    return out, cost


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("s2_json")
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--contexto", default="", help="informação extra sobre o item (ex.: observação da lista)")
    a = ap.parse_args()
    src = Path(a.s2_json)
    s2 = json.loads(src.read_text())
    ctx = f"CONTEXTO ADICIONAL: {a.contexto}\n" if a.contexto else ""
    items, cost = match(s2["query"], s2["items"], a.model, ctx)
    dst = src.with_name("s3_matched.json")
    dst.write_text(json.dumps({**{k: v for k, v in s2.items() if k != "items"}, "items": items},
                              ensure_ascii=False, indent=1))
    for it in sorted(items, key=lambda x: -(x["precisao"] or 0)):
        flag = "✔" if it["match_exato"] else "✘"
        print(f"{flag} {it['precisao']:.2f} x{it['unidades']:<3} {it['item_id']:14} {(it['titulo'] or '')[:55]:55} | {it['motivo'][:90]}")
    print(f"\n{sum(1 for i in items if i['match_exato'])}/{len(items)} com match exato; custo US$ {cost:.3f} -> {dst}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
