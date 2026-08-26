"""Coleta metricas (curtidas/comentarios) dos posts ja publicados e gera um
relatorio comparando desempenho por formato (imagem vs reels).

Roda automaticamente 1x por semana via GitHub Actions (analyze.yml).
Nao publica nada, so le o Instagram e escreve o resultado no repositorio:
  analytics/history.json  -> uma "foto" por execucao, guarda o historico
  analytics/report.md     -> relatorio legivel, sempre com os dados mais recentes

Variaveis de ambiente esperadas (mesmas do publish.py):
  IG_ACCESS_TOKEN, IG_USER_ID, GITHUB_TOKEN, GITHUB_REPO
"""
import base64
import json
import os
import sys
import time
import urllib.request
import urllib.parse
import urllib.error

GRAPH = "https://graph.instagram.com/v21.0"
GITHUB_REPO = os.environ.get("GITHUB_REPO", "dpplxx/fichafisio-conteudo")
SCHEDULE_PATH = "schedule.json"
HISTORY_PATH = "analytics/history.json"
REPORT_PATH = "analytics/report.md"


def http(method, url, data=None, headers=None):
    headers = headers or {}
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8") if not isinstance(data, bytes) else data
        headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.getcode(), json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def gh_headers(token):
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}


def fetch_json_from_repo(path, token):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    code, resp = http("GET", url, headers=gh_headers(token))
    if code == 404:
        return None, None
    if code >= 300:
        raise RuntimeError(f"Falha ao buscar {path}: {resp}")
    content = base64.b64decode(resp["content"]).decode("utf-8")
    return json.loads(content), resp["sha"]


def push_to_repo(path, text, sha, message, token):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    data = {"message": message, "content": encoded}
    if sha:
        data["sha"] = sha
    code, resp = http("PUT", url, data=data, headers=gh_headers(token))
    if code >= 300:
        raise RuntimeError(f"Falha ao atualizar {path}: {resp}")


def fetch_media_stats(media_id, access_token):
    url = f"{GRAPH}/{media_id}?fields=like_count,comments_count,media_type,timestamp,permalink&access_token={access_token}"
    code, resp = http("GET", url)
    if code >= 300:
        return {"error": resp}
    return resp


def build_report(items, history):
    lines = ["# Desempenho @fichafisio\n"]
    lines.append(f"_Atualizado automaticamente em {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}_\n")

    posted = [it for it in items if it.get("posted") and it.get("media_id")]
    if not posted:
        lines.append("Nenhum post publicado ainda.\n")
        return "\n".join(lines)

    by_type = {}
    lines.append("## Por post\n")
    lines.append("| Post | Formato | Curtidas | Comentarios | Link |")
    lines.append("|---|---|---|---|---|")
    for it in posted:
        stats = it.get("_stats", {})
        likes = stats.get("like_count")
        comments = stats.get("comments_count")
        link = stats.get("permalink", "")
        formato = "Reels" if it["type"] == "video_reels" else "Imagem"
        lines.append(f"| {it['id']} | {formato} | {likes if likes is not None else '?'} | {comments if comments is not None else '?'} | {link} |")
        if likes is not None and comments is not None:
            by_type.setdefault(it["type"], []).append(likes + comments)

    lines.append("\n## Media de engajamento por formato\n")
    if by_type:
        for tipo, valores in by_type.items():
            nome = "Reels" if tipo == "video_reels" else "Imagem"
            media = sum(valores) / len(valores)
            lines.append(f"- **{nome}**: media de {media:.1f} (curtidas + comentarios) em {len(valores)} post(s)")
        if len(by_type) > 1:
            melhor = max(by_type.items(), key=lambda kv: sum(kv[1]) / len(kv[1]))
            nome_melhor = "Reels" if melhor[0] == "video_reels" else "Imagem"
            lines.append(f"\n**Recomendacao:** formato **{nome_melhor}** esta performando melhor ate agora — priorizar nas proximas levas de conteudo.")
    else:
        lines.append("Ainda sem dados suficientes pra comparar formatos.")

    lines.append(f"\n## Fila\n")
    pendentes = [it["id"] for it in items if not it.get("posted")]
    lines.append(f"- Publicados: {len(posted)}")
    lines.append(f"- Pendentes na fila: {len(pendentes)} ({', '.join(pendentes) if pendentes else 'fila vazia'})")
    if len(pendentes) <= 2:
        lines.append("\n**Atencao:** a fila esta acabando — hora de gerar uma nova leva de conteudo.")

    return "\n".join(lines)


def main():
    access_token = os.environ["IG_ACCESS_TOKEN"].strip()
    github_token = os.environ["GITHUB_TOKEN"].strip()

    items, _ = fetch_json_from_repo(SCHEDULE_PATH, github_token)
    if items is None:
        raise RuntimeError("schedule.json nao encontrado")

    snapshot_items = []
    for it in items:
        if it.get("posted") and it.get("media_id"):
            stats = fetch_media_stats(it["media_id"], access_token)
            it["_stats"] = stats
            snapshot_items.append({
                "id": it["id"],
                "type": it["type"],
                "media_id": it["media_id"],
                **{k: v for k, v in stats.items() if k != "error"},
            })
            time.sleep(1)

    history, history_sha = fetch_json_from_repo(HISTORY_PATH, github_token)
    if history is None:
        history = []
    history.append({
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "items": snapshot_items,
    })

    report = build_report(items, history)

    # report.md nao e JSON, entao busca o sha direto (sem passar por fetch_json_from_repo)
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{REPORT_PATH}"
    code, resp = http("GET", url, headers=gh_headers(github_token))
    report_sha = resp["sha"] if code < 300 else None

    push_to_repo(HISTORY_PATH, json.dumps(history, ensure_ascii=False, indent=2), history_sha, "chore: atualiza historico de metricas", github_token)
    push_to_repo(REPORT_PATH, report, report_sha, "chore: atualiza relatorio de desempenho", github_token)

    print(report)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERRO: {e}", file=sys.stderr)
        sys.exit(1)
