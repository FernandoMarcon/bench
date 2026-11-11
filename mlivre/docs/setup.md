# Setup

Placeholders usados abaixo:

| Placeholder | Exemplo | O que é |
|---|---|---|
| `<ui-host>` | `anythingmcp.exemplo.com` | hostname público da interface do AnythingMCP (porta 3000) |
| `<api-host>` | `mcp.exemplo.com` | hostname público do backend/MCP do AnythingMCP (porta 4000) |
| `<server-id>` | `cmw...` | id do servidor MCP no AnythingMCP (página do servidor) |

## 1. AnythingMCP (self-hosted, Docker)

Instalado com o quickstart do projeto (<https://github.com/HelpCode-ai/anythingmcp#run-it-yourself>):

```bash
mkdir anythingmcp && cd anythingmcp
curl -fsSLo docker-compose.yml \
  https://raw.githubusercontent.com/HelpCode-ai/anythingmcp/main/docker-compose.quickstart.yml
printf 'JWT_SECRET=%s\nENCRYPTION_KEY=%s\n' "$(openssl rand -hex 32)" "$(openssl rand -hex 32)" > .env
docker compose up -d
```

Guarde o `.env`: o `ENCRYPTION_KEY` descriptografa as credenciais dos conectores.

### URLs públicas (obrigatório atrás de proxy/túnel)

O quickstart fixa `SERVER_URL`, `FRONTEND_URL`, `CORS_ORIGIN` e `NEXT_PUBLIC_API_URL` em `localhost`.
Com isso o AnythingMCP manda `redirect_uri=http://localhost:4000/...` para o Mercado Livre, e o login
OAuth falha (no nosso caso, um 403 do CloudFront em `auth.mercadolivre.com.br`).
Correção: `docker-compose.override.yml` ao lado do `docker-compose.yml`:

```yaml
services:
  app:
    environment:
      SERVER_URL: https://<api-host>
      FRONTEND_URL: https://<ui-host>
      CORS_ORIGIN: https://<ui-host>
      NEXT_PUBLIC_API_URL: https://<api-host>
      # MCP_AUTH_MODE: both   # opcional: aceita OAuth (claude.ai/ChatGPT por URL) além de API key
```

```bash
docker compose up -d --force-recreate
```

`MCP_AUTH_MODE`: o quickstart usa `legacy` (só API key). Valores: `oauth2`, `legacy`, `both`, `none`.
Para o Claude Code, `legacy` com API key é suficiente.

## 2. Túneis Cloudflare Zero Trust

Duas "published applications" no mesmo túnel:

| Hostname | Service URL |
|---|---|
| `<ui-host>` | `http://localhost:3000` |
| `<api-host>` | `http://localhost:4000` |

O túnel serve na porta 443, então **nunca** use `:4000` nas URLs públicas.
Não coloque `<api-host>` atrás do Cloudflare Access: clientes MCP remotos não passam pelo login do Access.

## 3. App no devcenter do Mercado Livre

<https://developers.mercadolivre.com.br/devcenter> → criar aplicação.

- **URI de redirect**: `https://<api-host>/api/mcp-oauth/callback` (exatamente, sem porta).
  Confira o valor mostrado pelo AnythingMCP na tela do conector depois do passo 1.
- **Fluxos OAuth**: Authorization Code + Refresh Token (Client Credentials não é necessário).
- **Permissões**: com tudo em "Sem acesso", **toda** leitura de anúncio de terceiros volta
  `403 PolicyAgent / PA_UNAUTHORIZED_RESULT_FROM_POLICIES`. Coloque pelo menos **Leitura** em:
  - Publicação e sincronização (`/items/.../description`, `/products/...`)
  - Venda e envios de um produto (`/items/.../shipping_options`)
  - Métricas do negócio
- **Tópicos / notificações**: deixar vazio.

Depois de mudar permissões é preciso **reautorizar** ("Save and sign in to Mercado" no conector) para o
token ganhar os novos escopos.

## 4. Conector Mercado Libre no AnythingMCP

Na UI: adicionar o conector Mercado Libre, informar App ID, Secret Key e o site
(`mercadolivre.com.br`), e clicar em **Save and sign in to Mercado**.

### Ferramentas de escrita desativadas

O pipeline só lê. Ficaram desativadas: `add_item_to_promotion`, `close_listing`, `create_listing`,
`post_answer`, `remove_item_from_promotion`, `update_listing`, `set_listing_status`,
`add_listing_description`, `update_listing_description` (e opcionalmente `validate_listing`).

### Ferramenta própria: `mercado_libre_get_shipping_options`

Criada em *MCP Tools → Add Tool* (o conector original não tem frete do ponto de vista do comprador):

| Campo | Valor |
|---|---|
| Tool Name | `mercado_libre_get_shipping_options` |
| Description | `Get the buyer-side shipping options of a listing to a zip code (CEP): cost, free shipping, discounts and estimated delivery time for each option.` |
| Method / Path | `GET /items/{item_id}/shipping_options` |
| Parâmetros | `item_id` (string, Path, obrigatório), `zip_code` (string, Query, obrigatório), `quantity` (number, Query) |
| Cache TTL | 300 s |
| Response Mapping | Off |

## 5. MCP no Claude Code

Gere uma API key na página do servidor (**Default** → API keys; uma por máquina, para poder revogar
individualmente) e registre com escopo de usuário:

```bash
claude mcp add -s user --transport http mercadolivre \
  https://<api-host>/mcp/<server-id> \
  --header "X-API-Key: mcp_..."
claude mcp list   # mercadolivre: ... ✔ Connected
```

O `pipeline/mcp_client.py` lê URL e chave dessa mesma entrada em `~/.claude.json`
(ou de `MLIVRE_MCP_URL` / `MLIVRE_MCP_KEY`). Requisições sem `User-Agent` de navegador/cliente são
bloqueadas pelo Cloudflare (403), por isso o cliente envia `User-Agent: mlivre-pipeline/0.1`.

## 6. Ambiente Python e login no Mercado Livre

```bash
cd mlivre
python3 -m venv .venv
.venv/bin/pip install playwright
.venv/bin/playwright install chromium
.venv/bin/python -m pipeline.browser    # abre o Chromium: faça login e FECHE a janela
```

A sessão fica em `mlivre/.browser-profile/` (fora do git). Sem login, `lista.mercadolivre.com.br`
redireciona para `/gz/account-verification` (anti-bot). Se isso voltar a acontecer, rode o login de novo.

## 7. CEP de entrega

Fora do git, em `~/.config/mlivre/pipeline.json`:

```json
{"cep": "01234567"}
```

ou `export MLIVRE_CEP=01234567`, ou `--cep` na linha de comando.

## 8. Claude CLI

A etapa 3 chama `claude -p --json-schema ...` e usa a assinatura do Claude Code (não precisa de
`ANTHROPIC_API_KEY`). O `claude` precisa estar no `PATH`.
