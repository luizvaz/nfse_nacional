"""
Script auxiliar para executar os testes
"""

import subprocess
import sys
from pathlib import Path


def main():
    """Executa os testes com pytest"""
    project_root = Path(__file__).parent.parent

    # Verifica se o XSD existe
    xsd_path = project_root / "schemas" / "DPS_v1.00.xsd"
    if not xsd_path.exists():
        print("⚠️  AVISO: Arquivo XSD não encontrado em schemas/DPS_v1.00.xsd")
        print("   Alguns testes podem ser pulados.")
        print()

    # Executa os testes
    cmd = [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"]

    # Adiciona opções extras se fornecidas
    if len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])

    result = subprocess.run(cmd, cwd=project_root)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
