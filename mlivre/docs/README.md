# mlivre — busca de componentes no Mercado Livre

Dado o nome de uma peça de uma lista de componentes (ex.: `Servo Horn metálico 25T`), o pipeline:

1. busca a peça no Mercado Livre;
2. coleta, para cada anúncio, título, id, preço, desconto, Características do produto, Descrição,
   frete e prazo para o CEP de entrega, parcelas e meios de pagamento;
3. usa o Claude para decidir quais anúncios correspondem **exatamente** à peça;
4. ordena os aprovados por custo-benefício e grava um CSV.

```bash
cd mlivre
.venv/bin/python -m pipeline.run "Servo Horn metálico 25T" --qtd 3 --contexto "para MG996R, braço único"
# -> out/servo-horn-metalico-25t/resultado.csv
```

Também existe a skill global do Claude Code `/mlivre-search`, que roda o mesmo pipeline a partir do
console do Claude (ver [skill.md](skill.md)).

## Documentos

| Arquivo | Conteúdo |
|---|---|
| [setup.md](setup.md) | Infraestrutura: AnythingMCP, túneis Cloudflare, app do Mercado Livre, ferramenta de frete, Claude Code, login do navegador |
| [api-findings.md](api-findings.md) | O que a API do Mercado Livre libera ou bloqueia para apps de terceiros e por que o pipeline é híbrido |
| [pipeline.md](pipeline.md) | As 4 etapas, campos coletados, prompt de match, fórmula do score, colunas do CSV, custos e limitações |
| [skill.md](skill.md) | A skill `/mlivre-search` do Claude Code |

## Estrutura

```
mlivre/
  pipeline/
    browser.py      # Chromium (Playwright) com perfil persistente; `python -m pipeline.browser` = login
    mcp_client.py   # cliente JSON-RPC mínimo para o MCP do AnythingMCP
    s1_search.py    # etapa 1: busca (Playwright)
    s2_fetch.py     # etapa 2: detalhes (Playwright + MCP)
    s3_match.py     # etapa 3: match exato (claude -p)
    s4_rank.py      # etapa 4: score + CSV
    run.py          # orquestra as 4 etapas
  docs/             # esta documentação
  out/              # resultados por query (fora do git)
  .browser-profile/ # sessão logada do Mercado Livre (fora do git)
```
