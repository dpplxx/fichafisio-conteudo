"""Publica o proximo item pendente da fila no Instagram (@fichafisio).

Usa a API do Instagram com Login do Instagram (graph.instagram.com) —
o caminho certo quando a conta NAO esta vinculada a uma Pagina do
Facebook. Token de usuario do Instagram, gerado direto na conta.

Le schedule.json direto do GitHub (sempre a versao mais recente),
publica o primeiro item com posted=false via API oficial da Meta,
e grava o resultado de volta no repo via GitHub Contents API
(nao depende de credenciais git — so precisa de um token).

Variaveis de ambiente esperadas:
  IG_ACCESS_TOKEN   token de acesso do usuario do Instagram (longa duracao)
  IG_USER_ID        ID da conta profissional do Instagram (@fichafisio)
  GITHUB_TOKEN      personal access token com escopo de conteudo no repo
  GITHUB_REPO       "dpplxx/fichafisio-conteudo" (default)
"""
import base64
import json
import os
import sys
import time
import urllib.request
import urllib.parse

GRAPH = "https://graph.instagram.com/v21.0"
GITHUB_REPO = os.environ.get("GITHUB_REPO", "dpplxx/fichafisio-conteudo")
SCHEDULE_PATH = "schedule.json"


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


def graph_post(path, params):
    url = f"{GRAPH}/{path}"
    qs = urllib.parse.urlencode(params)
    code, resp = http("POST", f"{url}?{qs}")
    if code >= 300:
        raise RuntimeError(f"Graph API error on POST {path}: {resp}")
    return resp


def graph_get(path, params):
    url = f"{GRAPH}/{path}?{urllib.parse.urlencode(params)}"
    code, resp = http("GET", url)
    if code >= 300:
        raise RuntimeError(f"Graph API error on GET {path}: {resp}")
    return resp


def fetch_schedule():
    token = os.environ["GITHUB_TOKEN"].strip()
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{SCHEDULE_PATH}"
    code, resp = http("GET", url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    })
    if code >= 300:
        raise RuntimeError(f"Falha ao buscar schedule.json: {resp}")
    content = base64.b64decode(resp["content"]).decode("utf-8")
    return json.loads(content), resp["sha"]


def push_schedule(items, sha, message):
    token = os.environ["GITHUB_TOKEN"].strip()
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{SCHEDULE_PATH}"
    encoded = base64.b64encode(json.dumps(items, ensure_ascii=False, indent=2).encode("utf-8")).decode("ascii")
    code, resp = http("PUT", url, data={
        "message": message,
        "content": encoded,
        "sha": sha,
    }, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    })
    if code >= 300:
        raise RuntimeError(f"Falha ao atualizar schedule.json: {resp}")


def publish_image(ig_user_id, access_token, item):
    container = graph_post(f"{ig_user_id}/media", {
        "image_url": item["image_url"],
        "caption": item["caption"],
        "access_token": access_token,
    })
    creation_id = container["id"]
    result = graph_post(f"{ig_user_id}/media_publish", {
        "creation_id": creation_id,
        "access_token": access_token,
    })
    return result


def publish_reels(ig_user_id, access_token, item):
    container = graph_post(f"{ig_user_id}/media", {
        "media_type": "REELS",
        "video_url": item["video_url"],
        "caption": item["caption"],
        "access_token": access_token,
    })
    creation_id = container["id"]

    # video precisa processar antes de publicar - poll ate FINISHED (timeout 5 min)
    deadline = time.time() + 300
    while time.time() < deadline:
        status = graph_get(creation_id, {"fields": "status_code", "access_token": access_token})
        code = status.get("status_code")
        if code == "FINISHED":
            break
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Processamento do video falhou: {status}")
        time.sleep(10)
    else:
        raise RuntimeError("Timeout esperando o video processar (5 min)")

    result = graph_post(f"{ig_user_id}/media_publish", {
        "creation_id": creation_id,
        "access_token": access_token,
    })
    return result


def main():
    ig_user_id = os.environ["IG_USER_ID"].strip()
    access_token = os.environ["IG_ACCESS_TOKEN"].strip()

    items, sha = fetch_schedule()
    pending = next((it for it in items if not it["posted"]), None)

    if pending is None:
        print("Fila vazia — nada pendente pra publicar.")
        return

    print(f"Publicando: {pending['id']} ({pending['type']})")

    if pending["type"] == "image":
        result = publish_image(ig_user_id, access_token, pending)
    elif pending["type"] == "video_reels":
        result = publish_reels(ig_user_id, access_token, pending)
    else:
        raise RuntimeError(f"Tipo desconhecido: {pending['type']}")

    print(f"Publicado com sucesso: {result}")

    pending["posted"] = True
    pending["posted_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    pending["media_id"] = result.get("id")

    push_schedule(items, sha, f"chore: marca {pending['id']} como publicado")
    print("schedule.json atualizado no repositorio.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERRO: {e}", file=sys.stderr)
        sys.exit(1)
