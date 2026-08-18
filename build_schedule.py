"""Monta schedule.json a partir dos arquivos de legenda + imagens em assets/.
Rodar uma vez sempre que uma nova leva de conteudo for adicionada ao repo.
Nao mexe em entradas ja existentes (preserva o campo 'posted').
"""
import json
import os

REPO_RAW_BASE = "https://raw.githubusercontent.com/dpplxx/fichafisio-conteudo/main"
SCHEDULE_PATH = "schedule.json"

NEW_ENTRIES = [
    {"id": "reels-01", "type": "video_reels", "asset": "assets/reels/fichafisio-reels-completo.mp4", "caption_file": "assets/reels/legenda-reels-01.txt"},
    {"id": "post-10", "type": "image", "asset": "assets/posts/post-10.png", "caption_file": None},
    {"id": "post-11", "type": "image", "asset": "assets/posts/post-11.png", "caption_file": None},
    {"id": "post-12", "type": "image", "asset": "assets/posts/post-12.png", "caption_file": None},
    {"id": "post-13", "type": "image", "asset": "assets/posts/post-13.png", "caption_file": None},
    {"id": "post-14", "type": "image", "asset": "assets/posts/post-14.png", "caption_file": None},
    {"id": "post-15", "type": "image", "asset": "assets/posts/post-15.png", "caption_file": None},
]

LEGEND_SRC_DIR = r"C:\Users\Desktop\Videos\fichafisio-instagram\posts\legendas"


def load_caption(entry):
    if entry["caption_file"]:
        path = entry["caption_file"]
    else:
        num = entry["id"].split("-")[1]
        path = os.path.join(LEGEND_SRC_DIR, f"legenda-{num}.txt")
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def main():
    existing = {}
    if os.path.exists(SCHEDULE_PATH):
        with open(SCHEDULE_PATH, "r", encoding="utf-8") as f:
            for item in json.load(f):
                existing[item["id"]] = item

    result = []
    for entry in NEW_ENTRIES:
        if entry["id"] in existing:
            result.append(existing[entry["id"]])
            continue
        caption = load_caption(entry)
        result.append({
            "id": entry["id"],
            "type": entry["type"],
            "image_url" if entry["type"] == "image" else "video_url": f"{REPO_RAW_BASE}/{entry['asset']}",
            "caption": caption,
            "posted": False,
            "posted_at": None,
        })

    with open(SCHEDULE_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"schedule.json com {len(result)} itens.")


if __name__ == "__main__":
    main()
