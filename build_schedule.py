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
    # Leva 3 (06/09/2026) - foco em Reels educativos + CTA de direct, ver [[project-fichafisio-instagram]]
    {"id": "post-16", "type": "image", "asset": "assets/posts/post-16.png", "caption_file": "assets/posts/legenda-16.txt"},
    {"id": "post-17", "type": "image", "asset": "assets/posts/post-17.png", "caption_file": "assets/posts/legenda-17.txt"},
    {"id": "reels-02", "type": "video_reels", "asset": "assets/reels/fichafisio-reels-02.mp4", "caption_file": "assets/reels/legenda-reels-02.txt"},
    {"id": "post-18", "type": "image", "asset": "assets/posts/post-18.png", "caption_file": "assets/posts/legenda-18.txt"},
    {"id": "reels-03", "type": "video_reels", "asset": "assets/reels/fichafisio-reels-03.mp4", "caption_file": "assets/reels/legenda-reels-03.txt"},
    # Leva 4 (08/09/2026) - visual v2 premium (Manrope/Inter), formatos antes/depois,
    # quebra de objecao, prova social geografica e passo-a-passo. Ver [[project-fichafisio-instagram]]
    {"id": "post-19", "type": "image", "asset": "assets/posts/post-19.png", "caption_file": "assets/posts/legenda-19.txt"},
    {"id": "post-20", "type": "image", "asset": "assets/posts/post-20.png", "caption_file": "assets/posts/legenda-20.txt"},
    {"id": "reels-04", "type": "video_reels", "asset": "assets/reels/fichafisio-reels-04.mp4", "caption_file": "assets/reels/legenda-reels-04.txt"},
    {"id": "post-21", "type": "image", "asset": "assets/posts/post-21.png", "caption_file": "assets/posts/legenda-21.txt"},
    {"id": "reels-05", "type": "video_reels", "asset": "assets/reels/fichafisio-reels-05.mp4", "caption_file": "assets/reels/legenda-reels-05.txt"},
    {"id": "post-22", "type": "image", "asset": "assets/posts/post-22.png", "caption_file": "assets/posts/legenda-22.txt"},
    # Leva 5 (08/09/2026) - caso real recriado (Maria Aparecida, ombro, SPADI 54,6%),
    # telas do app fielmente reproduzidas. Ver [[project-fichafisio-instagram]]
    {"id": "post-23", "type": "image", "asset": "assets/posts/post-23.png", "caption_file": "assets/posts/legenda-23.txt"},
    {"id": "reels-caso-real", "type": "video_reels", "asset": "assets/reels/fichafisio-reels-caso-real.mp4", "caption_file": "assets/reels/legenda-reels-caso-real.txt"},
    {"id": "post-24", "type": "image", "asset": "assets/posts/post-24.png", "caption_file": "assets/posts/legenda-24.txt"},
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
