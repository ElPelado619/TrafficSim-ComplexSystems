#!/usr/bin/env python
"""
Script de ayuda para ejecutar comandos comunes del proyecto.
"""

import sys
import os
from pathlib import Path

def print_help():
    """Muestra la ayuda del script."""
    print("""
╔════════════════════════════════════════════════════════════════╗
║   SIMULACIÓN DE TRÁFICO - MODELO DE NAGEL-SCHRECKENBERG       ║
╚════════════════════════════════════════════════════════════════╝

Comandos disponibles:

  python run.py test          - Ejecutar tests de instalación
  python run.py examples      - Ejecutar ejemplos básicos
  python run.py advanced      - Ejecutar análisis avanzados
  python run.py help          - Mostrar esta ayuda

Estructura del proyecto:

  src/                        - Código fuente
  examples/                   - Scripts de ejemplo
  tests/                      - Tests
  data/                       - Mapas OSM
  docs/                       - Documentación

Documentación:

  README.md                   - Documentación principal
  docs/QUICKSTART.md          - Guía de inicio rápido
  docs/TECHNICAL_NOTES.md     - Notas técnicas

Para más información, consulta el README.md
    """)

def run_test():
    """Ejecuta los tests de instalación."""
    print("\n🧪 Ejecutando tests de instalación...\n")
    os.system(f"{sys.executable} tests/test_installation.py")

def run_examples():
    """Ejecuta los ejemplos básicos."""
    print("\n📊 Ejecutando ejemplos básicos...\n")
    os.system(f"{sys.executable} examples/run_simulation.py")

def run_advanced():
    """Ejecuta los análisis avanzados."""
    print("\n🔬 Ejecutando análisis avanzados...\n")
    os.system(f"{sys.executable} examples/advanced_examples.py")

def main():
    """Función principal."""
    if len(sys.argv) < 2:
        print_help()
        return
    
    command = sys.argv[1].lower()
    
    commands = {
        'test': run_test,
        'examples': run_examples,
        'advanced': run_advanced,
        'help': print_help,
        '-h': print_help,
        '--help': print_help,
    }
    
    if command in commands:
        commands[command]()
    else:
        print(f"\n❌ Comando desconocido: {command}")
        print("   Usa 'python run.py help' para ver los comandos disponibles.\n")

if __name__ == '__main__':
    main()
