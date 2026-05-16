"""
setup_data.py — Download dos dados processados (Parquet) do Google Drive
=========================================================================
Use este script para baixar os arquivos Parquet já processados e evitar
executar toda a pipeline localmente.

Como usar:
    python setup_data.py

Pré-requisito:
    pip install gdown

ANTES DE COMPARTILHAR:
    1. Compacte a pasta data/processed/ em um arquivo ZIP
    2. Faça upload para o Google Drive
    3. Compartilhe o arquivo com "Qualquer pessoa com o link pode visualizar"
    4. Copie o ID do arquivo do link (parte entre /d/ e /view)
    5. Substitua FILE_ID abaixo pelo ID copiado
"""

import sys
import zipfile
from pathlib import Path

# ── CONFIGURAÇÃO: substitua pelo ID real do seu arquivo no Google Drive ───────
FILE_ID = "COLE_AQUI_O_ID_DO_ARQUIVO_NO_GOOGLE_DRIVE"
# Exemplo: "1aBcDeFgHiJkLmNoPqRsTuVwXyZ_abcdefgh"
# ─────────────────────────────────────────────────────────────────────────────

DEST_ZIP = Path("data/processed_data.zip")
DEST_DIR = Path("data/processed")

def main() -> None:
    try:
        import gdown
    except ImportError:
        print("Instalando gdown...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "gdown"])
        import gdown

    if FILE_ID == "COLE_AQUI_O_ID_DO_ARQUIVO_NO_GOOGLE_DRIVE":
        print(
            "\n[ERRO] FILE_ID não configurado.\n"
            "Edite setup_data.py e substitua FILE_ID pelo ID do arquivo no Google Drive.\n"
        )
        sys.exit(1)

    print("Baixando dados processados do Google Drive...")
    gdown.download(id=FILE_ID, output=str(DEST_ZIP), quiet=False)

    print("\nExtraindo arquivos...")
    with zipfile.ZipFile(DEST_ZIP, "r") as zf:
        zf.extractall("data/")

    DEST_ZIP.unlink()
    print(f"\nDados extraídos em: {DEST_DIR.resolve()}")
    print("Pronto! Execute: streamlit run app/dashboard.py")


if __name__ == "__main__":
    main()
