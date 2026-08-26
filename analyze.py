"""Coleta metricas (curtidas/comentarios) de TODOS os posts do perfil
@fichafisio (inclusive os publicados manualmente antes da automacao existir,
como os posts 01-09) e gera um relatorio comparando desempenho por formato.

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

MEDIA_FIELDS = "id,caption,media_type,media_product_type,timestamp,permalink,like_count,comments_count"


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


def fetch_sha(path, token):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    code, resp = http("GET", url, headers=gh_headers(token))
    return resp["sha"] if code < 300 else None


def push_to_repo(path, text, sha, message, token):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    data = {"message": message, "content": encoded}
    if sha:
        data["sha"] = sha
    code, resp = http("PUT", url, data=data, headers=gh_headers(token))
    if code >= 300:
        raise RuntimeError(f"Falha ao atualizar {path}: {resp}")


def fetch_all_media(ig_user_id, access_token):
    media = []
    url = f"{GRAPH}/{ig_user_id}/media?fields={MEDIA_FIELDS}&limit=50&access_token={access_token}"
    while url:
        code, resp = http("GET", url)
        if code >= 300:
            raise RuntimeError(f"Falha ao listar posts do Instagram: {resp}")
        media.extend(resp.get("data", []))
        url = resp.get("paging", {}).get("next")
    return media


def classify_format(item):
    if item.get("media_product_type") == "REELS":
        return "Reels"
    if item.get("media_type") == "CAROUSEL_ALBUM":
        return "Carrossel"
    if item.get("media_type") == "VIDEO":
        return "Video"
    return "Imagem"


def build_report(media_list, pendentes):
    lines = ["# Desempenho @fichafisio\n"]
    lines.append(f"_Atualizado automaticamente em {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}_\n")

    if not media_list:
        lines.append("Nenhum post publicado ainda.\n")
        return "\n".join(lines)

    ordenado = sorted(media_list, key=lambda m: m.get("timestamp", ""))
    agora = time.time()
    MATURACAO_DIAS = 3

    def idade_dias(m):
        ts = m.get("timestamp", "")
        try:
            t = time.mktime(time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S"))
            return (agora - t) / 86400
        except ValueError:
            return 999

    by_format = {}
    by_format_maduro = {}
    lines.append("## Por post\n")
    lines.append("| Data | Formato | Curtidas | Comentarios | Link |")
    lines.append("|---|---|---|---|---|")
    for m in ordenado:
        formato = classify_format(m)
        likes = m.get("like_count", 0)
        comments = m.get("comments_count", 0)
        data = m.get("timestamp", "")[:10]
        link = m.get("permalink", "")
        lines.append(f"| {data} | {formato} | {likes} | {comments} | {link} |")
        by_format.setdefault(formato, []).append(likes + comments)
        if idade_dias(m) >= MATURACAO_DIAS:
            by_format_maduro.setdefault(formato, []).append(likes + comments)

    lines.append("\n## Media de engajamento por formato\n")
    lines.append(f"_Considera so posts com {MATURACAO_DIAS}+ dias no ar, pra nao comparar um post recem-publicado (que ainda esta ganhando alcance) com um que ja maturou._\n")
    if by_format_maduro:
        for formato, valores in by_format_maduro.items():
            media = sum(valores) / len(valores)
            lines.append(f"- **{formato}**: media de {media:.1f} (curtidas + comentarios) em {len(valores)} post(s)")
        if len(by_format_maduro) > 1:
            melhor = max(by_format_maduro.items(), key=lambda kv: sum(kv[1]) / len(kv[1]))
            lines.append(f"\n**Recomendacao:** formato **{melhor[0]}** esta performando melhor ate agora — priorizar nas proximas levas de conteudo.")
        else:
            lines.append("\nAinda so ha um formato maduro o suficiente pra avaliar — falta comparacao.")
    else:
        lines.append("Nenhum post maduro (3+ dias) ainda pra comparar com confianca.")

    recentes = [m for m in ordenado if idade_dias(m) < MATURACAO_DIAS]
    if recentes:
        lines.append(f"\n_Fora da comparacao acima (ainda ganhando alcance, <{MATURACAO_DIAS} dias): {', '.join(classify_format(m) + ' de ' + m.get('timestamp', '')[:10] for m in recentes)}._")

    lines.append("\n## Fila de publicacao automatica\n")
    lines.append(f"- Total de posts no perfil: {len(media_list)}")
    lines.append(f"- Pendentes na fila automatica: {len(pendentes)} ({', '.join(pendentes) if pendentes else 'fila vazia'})")
    if len(pendentes) <= 2:
        lines.append("\n**Atencao:** a fila esta acabando — hora de gerar uma nova leva de conteudo.")

    return "\n".join(lines)


def main():
    ig_user_id = os.environ["IG_USER_ID"].strip()
    access_token = os.environ["IG_ACCESS_TOKEN"].strip()
    github_token = os.environ["GITHUB_TOKEN"].strip()

    schedule, _ = fetch_json_from_repo(SCHEDULE_PATH, github_token)
    pendentes = [it["id"] for it in (schedule or []) if not it.get("posted")]

    media_list = fetch_all_media(ig_user_id, access_token)

    history, history_sha = fetch_json_from_repo(HISTORY_PATH, github_token)
    if history is None:
        history = []
    history.append({
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "media": media_list,
    })

    report = build_report(media_list, pendentes)
    report_sha = fetch_sha(REPORT_PATH, github_token)

    push_to_repo(HISTORY_PATH, json.dumps(history, ensure_ascii=False, indent=2), history_sha, "chore: atualiza historico de metricas", github_token)
    push_to_repo(REPORT_PATH, report, report_sha, "chore: atualiza relatorio de desempenho", github_token)

    print(report)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERRO: {e}", file=sys.stderr)
        sys.exit(1)
