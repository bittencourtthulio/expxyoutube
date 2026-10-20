#!/usr/bin/env python3
"""Imita `node scripts/render.mjs <deck.json> <saida> <ativos>` sem Remotion: grava mp4 e png vazios por slide.

`--version` responde v20.0.0. Com a variável NODE_FALSO_FALHA definida, sai 1 com erro no stderr.
"""
import json
import os
import sys
from pathlib import Path


def main():
    if sys.argv[1:] == ["--version"]:
        print("v20.0.0")
        return 0
    script, deck_arq, saida, ativos = sys.argv[1:5]
    if not script.endswith("render.mjs"):
        print(f"node falso: script inesperado {script}", file=sys.stderr)
        return 2
    if os.environ.get("NODE_FALSO_FALHA"):
        print("Error: render falhou de propósito", file=sys.stderr)
        return 1
    deck = json.loads(Path(deck_arq).read_text(encoding="utf-8"))
    Path(saida).mkdir(parents=True, exist_ok=True)
    Path(saida, "deck-recebido.json").write_text(json.dumps(deck, ensure_ascii=False))
    n = len(deck["slides"])
    for i in range(1, n + 1):
        Path(saida, f"slide-{i:02d}.mp4").write_bytes(b"mp4-falso")
        Path(saida, f"slide-{i:02d}.png").write_bytes(b"\x89PNG-falso")
        print(f"slide {i}/{n} ok", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
