# fichafisio-conteudo

Repositório de conteúdo e automação de publicação do Instagram [@fichafisio](https://instagram.com/fichafisio).

## Estrutura

- `assets/posts/` — artes prontas (1080x1080)
- `assets/reels/` — vídeos verticais pro Reels
- `schedule.json` — fila de publicação (cada item tem `posted: false/true`)
- `build_schedule.py` — gera/atualiza `schedule.json` a partir de novos posts adicionados em `assets/`
- `publish.py` — publica o próximo item pendente da fila via API oficial da Meta (Instagram Graph API). Roda 3x/semana via GitHub Actions.
- `analyze.py` — coleta curtidas/comentários dos posts já publicados e gera `analytics/report.md`. Roda 1x/semana via GitHub Actions.
- `analytics/report.md` — relatório de desempenho sempre atualizado (curtidas/comentários por post, média por formato, recomendação de qual formato priorizar).
- `analytics/history.json` — histórico bruto de todas as coletas (uma entrada por execução).

## Como a automação funciona

**Publicação** (`.github/workflows/publish.yml`, seg/qua/sex 19h Brasília): busca `schedule.json` do GitHub, pega o primeiro item com `posted: false`, publica no Instagram via Graph API (imagem ou Reels), marca como publicado e salva de volta no repositório.

**Análise** (`.github/workflows/analyze.yml`, domingo à noite): busca os posts já publicados, consulta curtidas/comentários de cada um via Graph API, e regrava `analytics/report.md` comparando o desempenho de imagem vs. Reels — sem precisar ninguém pedir.

Nenhum dos dois precisa de senha do Instagram — só o token de acesso oficial da Meta, gerado uma vez em developers.facebook.com.

## Adicionar uma nova leva de conteúdo

1. Colocar as novas imagens/vídeos em `assets/`
2. Adicionar as entradas correspondentes em `NEW_ENTRIES` dentro de `build_schedule.py`
3. Rodar `python build_schedule.py`
4. Commit + push
