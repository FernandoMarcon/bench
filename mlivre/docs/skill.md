# Skill do Claude Code: `/mlivre-search`

Permite rodar o pipeline pelo console do Claude Code, em qualquer projeto.

- Fonte: `~/ledot/patterns/mlivre-search/SKILL.md` (versionada no repositório `ledot`)
- Instalação global: link simbólico em `~/.claude/skills/mlivre-search`

```bash
ln -s ~/ledot/patterns/mlivre-search ~/.claude/skills/mlivre-search
```

## Uso

```
/mlivre-search Servo Horn metálico 25T --qtd 3 --contexto "para MG996R, braço único"
/mlivre-search capacitor eletrolítico 1000uF 16V
/mlivre-search @robot_arm/v2RAD/items_list.csv      # uma busca por linha com Status = Falta
```

Também dispara sem o comando, por exemplo: "acha no Mercado Livre um horn de alumínio 25T para o MG996R".

O que a skill faz:

1. Monta a query, a quantidade e o contexto a partir do pedido (ou de cada linha da lista de peças).
   Para listas com mais de 5 itens, mostra as queries e pede confirmação antes.
2. Roda `python -m pipeline.run` em `/data/drive/Projects/mlivre`.
3. Responde com o top 5 (link, score, preço, frete, custo total, prazo, motivo), o resumo dos rejeitados,
   os alertas (internacional, kit com quantidade incerta, precisão < 0,8) e o caminho do CSV.

Pré-requisitos: tudo de [setup.md](setup.md) (venv, login do navegador, CEP, MCP `mercadolivre`).
