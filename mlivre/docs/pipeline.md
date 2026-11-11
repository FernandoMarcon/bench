# Pipeline

Cada etapa lê o JSON da anterior e grava o seu em `out/<slug-da-query>/`, para poder testar e
re-executar uma etapa isoladamente.

```
query ─► s1_search ─► s1_search.json ─► s2_fetch ─► s2_items.json ─► s3_match ─► s3_matched.json ─► s4_rank ─► resultado.csv
          Playwright                    Playwright+MCP                 claude -p
```

## Comandos

```bash
.venv/bin/python -m pipeline.run "<peça>" [--n 20] [--qtd 1] [--contexto "..."] [--cep ...] [--model sonnet] [--todos]

.venv/bin/python -m pipeline.s1_search "<peça>" [--n 20] [--headed]
.venv/bin/python -m pipeline.s2_fetch  out/<slug>/s1_search.json [--cep ...] [--n N] [--headed]
.venv/bin/python -m pipeline.s3_match  out/<slug>/s2_items.json [--contexto "..."] [--model sonnet]
.venv/bin/python -m pipeline.s4_rank   out/<slug>/s3_matched.json [--qtd 1] [--todos]
```

| Opção | Efeito |
|---|---|
| `--n` | quantos resultados da busca processar (padrão 20, a primeira página) |
| `--qtd` | quantas peças você precisa; muda o custo total quando o anúncio é kit |
| `--contexto` | informação extra para o match (ex.: a coluna Obs da lista de peças) |
| `--todos` | inclui os rejeitados no fim do CSV (score − 100) |
| `--headed` | mostra o navegador (depuração) |

## Etapa 1: busca (`s1_search.py`)

Abre `https://lista.mercadolivre.com.br/<slug>` com o perfil logado e extrai, de cada card:
`item_id`, `catalog_product_id`, `titulo`, `preco`, `preco_original`, `desconto`, `parcelas`,
`frete_card`, `internacional`, `patrocinado`, `url`. Remove duplicados.

## Etapa 2: detalhes (`s2_fetch.py`)

Para cada anúncio:

- **Página (Playwright)**: `specs` (Características do produto, th → td), `highlights`, `pagamento`,
  `vendedor`, `reputacao`, `vendidos` (ex.: `Novo | 2 vendidos`).
- **MCP `get_listing_description`**: `descricao` (com fallback para o texto da página).
- **MCP `mercado_libre_get_shipping_options`** com o CEP: todas as opções em `opcoes_frete` e o resumo:

| Campo | Significado |
|---|---|
| `frete`, `prazo_dias`, `frete_tipo` | opção recomendada pelo ML (a que aparece por padrão) |
| `frete_min`, `prazo_frete_min` | opção mais barata |
| `prazo_min`, `frete_prazo_min` | opção mais rápida |

`prazo_dias` = dias corridos a partir de hoje (0 = chega hoje).
Erros por item ficam em `erros` e não interrompem o lote.

## Etapa 3: match exato (`s3_match.py`)

Lotes de 10 anúncios para `claude -p --model sonnet --output-format json --json-schema <SCHEMA>`.
Para cada anúncio o modelo devolve:

| Campo | Descrição |
|---|---|
| `precisao` | 0–1. 1.0 = todas as specs confirmadas na ficha/descrição |
| `match_exato` | `false` se alguma spec contradiz a query (material, nº de dentes, tensão, modelo...) ou se é outro produto |
| `unidades` | peças por anúncio (kit de 4 → 4) |
| `motivo` | evidência decisiva, em uma frase |

Ordem de confiança das evidências: **Características > Descrição > Título** (descrição truncada em
1500 caracteres). O prompt completo está em `s3_match.PROMPT`.

## Etapa 4: ranking (`s4_rank.py`)

Mantém só `match_exato = true` (ou todos, com `--todos`) e calcula:

```
qtd_anuncios = ceil(qtd / unidades)
custo_total  = qtd_anuncios · preço + frete
score (0–100) = 50·precisão + 30·(1 − custo_total_norm) + 10·(1 − preço_norm) + 10·(1 − prazo_norm)
```

`*_norm` é min-max entre as linhas do CSV (menor é melhor; valor ausente conta como o pior).
Empates: precisão > custo total > preço > prazo. Pesos em `s4_rank.PESOS`.

### Colunas do CSV (UTF-8 com BOM, abre direto no Excel/LibreOffice)

`titulo, score, precisao, match_exato, unidades, qtd_anuncios, custo_total, custo_unitario, preco,
frete, prazo_dias, frete_tipo, frete_min, prazo_frete_min, prazo_min, preco_original, desconto,
parcelas, pagamento, vendedor, vendidos, internacional, patrocinado, motivo, caracteristicas,
descricao, item_id, catalog_product_id, url`

## Desempenho e custo (medido)

| Query | Anúncios | Match exato | Tempo | Custo LLM |
|---|---|---|---|---|
| Servo Horn metálico 25T | 20 | 8 | ~2 min | US$ 0,27 |
| capacitor eletrolítico 1000uF 16V | 12 | 8 | ~1,5 min | US$ 0,20 |

## Limitações conhecidas

- **Frete com `--qtd`**: cotado para 1 unidade; ao comprar vários anúncios o total pode ficar um pouco
  subestimado.
- **Anúncios avulsos** costumam ter 2–3 características (ex.: marca); o match se apoia mais na descrição.
- **Reputação do vendedor**: o seletor ainda volta vazio; não entra no score.
- **Parcelas**: nem todo card mostra parcelamento; `pagamento` (da página) é mais completo.
- **HTML muda**: se o ML alterar classes, `s1_search` / `s2_fetch` podem voltar campos vazios. Use
  `--headed` para inspecionar e atualize os seletores em [api-findings.md](api-findings.md).
- **Sessão expira**: se aparecer `Bloqueado pela verificação anti-bot`, rode `python -m pipeline.browser`.
