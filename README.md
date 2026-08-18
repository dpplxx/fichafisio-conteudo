# fichafisio-conteudo

Repositório de conteúdo e automação de publicação do Instagram [@fichafisio](https://instagram.com/fichafisio).

## Estrutura

- `assets/posts/` — artes prontas (1080x1080)
- `assets/reels/` — vídeos verticais pro Reels
- `schedule.json` — fila de publicação (cada item tem `posted: false/true`)
- `build_schedule.py` — gera/atualiza `schedule.json` a partir de novos posts adicionados em `assets/`
- `publish.py` — publica o próximo item pendente da fila via API oficial da Meta (Instagram Graph API). É o que a rotina automática roda.

## Como a automação funciona

Uma rotina agendada (Claude Code) roda `publish.py` 3x por semana. O script:
1. Busca `schedule.json` direto do GitHub (sempre a versão mais recente)
2. Pega o primeiro item com `posted: false`
3. Publica no Instagram via Graph API (imagem ou Reels)
4. Marca o item como publicado e salva de volta no repositório

Nunca publica duas vezes o mesmo item, e nunca precisa de senha do Instagram — só um token de acesso oficial da Meta, gerado uma vez em developers.facebook.com.

## Adicionar uma nova leva de conteúdo

1. Colocar as novas imagens/vídeos em `assets/`
2. Adicionar as entradas correspondentes em `NEW_ENTRIES` dentro de `build_schedule.py`
3. Rodar `python build_schedule.py`
4. Commit + push
