"""
Script de prueba rápido para verificar la instalación y funcionalidad básica.
"""

import sys
from pathlib import Path

# Añadir el directorio padre al path para importar el módulo src
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_imports():
    """Verifica que todas las dependencias estén instaladas."""
    print("Verificando dependencias...")
    
    required_modules = {
        'osmnx': 'OSMnx',
        'networkx': 'NetworkX',
        'numpy': 'NumPy',
        'matplotlib': 'Matplotlib',
        'PIL': 'Pillow'
    }
    
    missing = []
    for module, name in required_modules.items():
        try:
            __import__(module)
            print(f"  ✓ {name} instalado")
        except ImportError:
            print(f"  ✗ {name} NO instalado")
            missing.append(name)
    
    if missing:
        print(f"\nFaltan dependencias: {', '.join(missing)}")
        print("Instala con: pip install -r requirements.txt")
        return False
    
    print("\n✓ Todas las dependencias están instaladas")
    return True


def quick_test():
    """Ejecuta una prueba rápida de la simulación."""
    print("\n" + "=" * 60)
    print("PRUEBA RÁPIDA DE LA SIMULACIÓN")
    print("=" * 60)
    
    try:
        from src.traffic_simulation import TrafficSimulation
        
        print("\nCreando simulación...")
        sim = TrafficSimulation(
            graph_file='data/map_reduced.osm',
            cell_length=7.5,
            v_max=5,
            p_slow=0.3
        )
        print("  ✓ Simulación creada correctamente")
        
        print("\nInicializando vehículos (densidad 15%)...")
        sim.initialize_vehicles(density=0.15)
        print(f"  ✓ {len(sim.vehicles)} vehículos inicializados")
        
        print("\nEjecutando 10 pasos de simulación...")
        for i in range(10):
            sim.step()
        print(f"  ✓ Simulación ejecutada hasta el paso {sim.time_step}")
        
        if sim.avg_velocities:
            print(f"  ✓ Velocidad promedio: {sim.avg_velocities[-1]:.2f}")
        
        print("\n" + "=" * 60)
        print("✓ PRUEBA EXITOSA")
        print("=" * 60)
        print("\nLa simulación funciona correctamente.")
        print("Ejecuta 'python examples/run_simulation.py' para ver ejemplos completos.")
        
        return True
        
    except FileNotFoundError as e:
        print(f"\n✗ Error: No se encuentra el archivo {e.filename}")
        print("Asegúrate de tener 'data/map_reduced.osm' en el directorio correcto.")
        return False
        
    except Exception as e:
        print(f"\n✗ Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Función principal."""
    print("=" * 60)
    print("TEST DE INSTALACIÓN - SIMULACIÓN DE TRÁFICO")
    print("=" * 60)
    print()
    
    # Verificar dependencias
    if not check_imports():
        sys.exit(1)
    
    # Ejecutar prueba rápida
    if not quick_test():
        sys.exit(1)
    
    print("\n✓ Todo listo para usar la simulación!")


if __name__ == '__main__':
    main()
