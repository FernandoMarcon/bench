# pipeline — busca de componentes no Mercado Livre

Query (item da lista de peças) → busca → detalhes → match exato (Claude) → CSV por custo-benefício.

| Etapa | Arquivo | Fonte | Saída |
|---|---|---|---|
| 1. Busca | `s1_search.py` | Playwright: `lista.mercadolivre.com.br` | `s1_search.json` |
| 2. Detalhes | `s2_fetch.py` | Playwright (características, pagamento, vendedor) + MCP (descrição, frete/prazo p/ CEP) | `s2_items.json` |
| 3. Match | `s3_match.py` | `claude -p --json-schema` | `s3_matched.json` |
| 4. Ranking | `s4_rank.py` | — | `resultado.csv` |

Por que híbrido: a API do ML bloqueia `/sites/MLB/search` e `/items/{id}` para apps de terceiros (403).
Descrição (`get_listing_description`), frete (`mercado_libre_get_shipping_options`, ferramenta criada no
AnythingMCP), `get_product` e `list_product_items` funcionam.

## Setup (uma vez)

```bash
python3 -m venv .venv && .venv/bin/pip install playwright && .venv/bin/playwright install chromium
.venv/bin/python -m pipeline.browser     # login no ML; feche a janela ao terminar
```

O CEP de entrega vem de `--cep`, `$MLIVRE_CEP` ou `~/.config/mlivre/pipeline.json` (`{"cep": "01234567"}`).
O MCP é lido de `~/.claude.json` (servidor `mercadolivre`) ou de `MLIVRE_MCP_URL` / `MLIVRE_MCP_KEY`.

## Uso

```bash
# tudo de uma vez
.venv/bin/python -m pipeline.run "Servo Horn metálico 25T" --qtd 3 --contexto "para MG996R, braço único"

# etapa por etapa (cada uma lê o JSON da anterior)
.venv/bin/python -m pipeline.s1_search "Servo Horn metálico 25T"
.venv/bin/python -m pipeline.s2_fetch  out/servo-horn-metalico-25t/s1_search.json [--cep 01234567]
.venv/bin/python -m pipeline.s3_match  out/servo-horn-metalico-25t/s2_items.json [--contexto "..."]
.venv/bin/python -m pipeline.s4_rank   out/servo-horn-metalico-25t/s3_matched.json [--qtd 3] [--todos]
```

## Score (0–100)

`50·precisão + 30·(1−total_norm) + 10·(1−preço_norm) + 10·(1−prazo_norm)`, normalizado entre os itens com
match exato. `total = ceil(qtd/unidades)·preço + frete`. Pesos em `s4_rank.PESOS`.
