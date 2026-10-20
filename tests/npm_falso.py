#!/usr/bin/env python3
"""Imita `npm install`: cria node_modules/.instalado no cwd e registra a chamada em NPM_FALSO_LOG, se definida."""
import os
import sys
from pathlib import Path


def main():
    Path("node_modules").mkdir(exist_ok=True)
    Path("node_modules", ".instalado").write_text(" ".join(sys.argv[1:]))
    if os.environ.get("NPM_FALSO_LOG"):
        with open(os.environ["NPM_FALSO_LOG"], "a") as f:
            f.write(" ".join(sys.argv[1:]) + "\n")
    print("npm falso: instalado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
