# API do Mercado Livre: o que funciona para um app de terceiros

Testado em 2026-11 com um app próprio (escopo pessoal) via AnythingMCP, token OAuth do usuário,
permissões de leitura ligadas (ver [setup.md](setup.md#3-app-no-devcenter-do-mercado-livre)).

| Endpoint | Ferramenta MCP | Resultado | Uso no pipeline |
|---|---|---|---|
| `GET /sites/MLB/search?q=` | — (o conector não tem) | **403** sempre, até sem token | substituído por Playwright |
| `GET /items/{id}` | `get_item` | **403 `access_denied`** para anúncios de terceiros | substituído por Playwright |
| `GET /items?ids=` | `get_items` | **403** por item | — |
| `GET /items/{id}/description` | `get_listing_description` | ✔ | Descrição |
| `GET /items/{id}/shipping_options?zip_code=` | `mercado_libre_get_shipping_options` (própria) | ✔ | frete e prazo por modalidade |
| `GET /products/{id}` | `get_product` | ✔ | (catálogo) características oficiais |
| `GET /products/{id}/items` | `list_product_items` | ✔ | (catálogo) outros vendedores, preço, `original_price` |
| `GET /users/me` | `get_user` | ✔ | teste de OAuth |

## Erros observados e significado

| Erro | Causa | Correção |
|---|---|---|
| 403 CloudFront em `auth.mercadolivre.com.br` | `redirect_uri` com `http://localhost...` | URLs públicas no AnythingMCP (override) |
| `403 PolicyAgent / PA_UNAUTHORIZED_RESULT_FROM_POLICIES` | permissões do app em "Sem acesso" | ligar Leitura e **reautorizar** |
| `403 access_denied` em `/items/{id}` | restrição da plataforma para anúncios de terceiros | sem correção; usar a página do anúncio |
| 403 do Cloudflare no MCP via Python | `User-Agent` padrão do `urllib` bloqueado | enviar `User-Agent` próprio |
| `lista.mercadolivre.com.br` → `/gz/account-verification` | anti-bot para acesso sem sessão | navegador com perfil logado |

## Produtos de catálogo

O Mercado Livre mantém fichas únicas de produto (`/p/MLB12345678`) nas quais vários vendedores
anunciam. Para eles `get_product` e `list_product_items` funcionam. Muita peça genérica (horns,
insertos, cabos) é anúncio avulso, sem catálogo, por isso a busca e a ficha técnica vêm da página.

## Página do anúncio (HTML)

Seletores usados (`pipeline/s2_fetch.py`, `pipeline/s1_search.py`):

| Dado | Seletor |
|---|---|
| card de resultado | `li.ui-search-layout__item .poly-card` |
| título / link | `a.poly-component__title` |
| preço / preço original | `.poly-price__current .andes-money-amount`, `.andes-money-amount--previous` |
| desconto | `.poly-price__discount-polylabel` |
| parcelas | `.poly-price__installments` |
| frete (card) | `.poly-component__shipping-v2` |
| internacional / patrocinado | `.poly-component__cbt`, `.poly-component__ads-promotions` |
| Características do produto | `.ui-vpp-striped-specs tr`, `table.andes-table tr` (th → td) |
| meios de pagamento | `.ui-vip-payment_methods` |
| vendedor | `.ui-seller-data-header__title` |

Links de anúncios patrocinados passam por `click1.mercadolivre.com.br`; o pipeline os troca por
`https://produto.mercadolivre.com.br/MLB-<número>`.
