"""
Script de ejemplo para ejecutar la simulación de tráfico.
"""

import sys
from pathlib import Path

# Añadir el directorio padre al path para importar el módulo src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.traffic_simulation import TrafficSimulation
import matplotlib.pyplot as plt


def example_1_basic_simulation():
    """Ejemplo básico: simulación con densidad media."""
    print("=" * 60)
    print("EJEMPLO 1: Simulación básica con densidad media")
    print("=" * 60)
    
    # Crear simulación
    sim = TrafficSimulation(
        graph_file='data/map_reduced.osm',
        cell_length=7.5,  # metros por celda (≈ longitud de un auto)
        v_max=5,          # velocidad máxima (celdas por paso de tiempo)
        p_slow=0.3        # probabilidad de desaceleración aleatoria
    )
    
    # Inicializar vehículos con densidad del 20%
    sim.initialize_vehicles(density=0.2)
    
    # Ejecutar algunos pasos
    print("\nEjecutando 50 pasos de simulación...")
    for i in range(50):
        sim.step()
        if (i + 1) % 10 == 0:
            print(f"  Paso {i + 1}/50 completado")
    
    # Visualizar estado final
    print("\nVisualizando estado final...")
    sim.plot_state()
    plt.savefig('simulation_state.png', dpi=150, bbox_inches='tight')
    print("Estado guardado en 'simulation_state.png'")
    plt.show()
    
    # Mostrar estadísticas
    sim.plot_statistics()
    plt.savefig('simulation_stats.png', dpi=150, bbox_inches='tight')
    print("Estadísticas guardadas en 'simulation_stats.png'")
    plt.show()


def example_2_animation():
    """Ejemplo 2: Crear una animación de la simulación."""
    print("\n" + "=" * 60)
    print("EJEMPLO 2: Animación de la simulación")
    print("=" * 60)
    
    # Crear simulación
    sim = TrafficSimulation(
        graph_file='data/map.osm',
        cell_length=7.5,
        v_max=5,
        p_slow=0.3
    )
    
    # Inicializar vehículos
    sim.initialize_vehicles(density=0.001)
    
    # Crear animación
    print("\nCreando animación (esto puede tardar un momento)...")
    print("Cierra la ventana de la animación para continuar.")
    sim.animate(steps=100, interval=100, save_as='traffic_animation.gif')


def example_3_compare_densities():
    """Ejemplo 3: Comparar diferentes densidades de tráfico."""
    print("\n" + "=" * 60)
    print("EJEMPLO 3: Comparación de diferentes densidades")
    print("=" * 60)
    
    densities = [0.1, 0.3, 0.5]
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    
    for idx, density in enumerate(densities):
        print(f"\nSimulando densidad {density:.0%}...")
        
        # Crear simulación
        sim = TrafficSimulation(
            graph_file='data/map_reduced.osm',
            cell_length=7.5,
            v_max=5,
            p_slow=0.3
        )
        
        # Inicializar vehículos
        sim.initialize_vehicles(density=density)
        
        # Ejecutar simulación
        for _ in range(50):
            sim.step()
        
        # Visualizar
        sim.plot_state(ax=axes[idx])
        axes[idx].set_title(f'Densidad: {density:.0%}\n'
                           f'Velocidad promedio: {sim.avg_velocities[-1]:.2f}')
    
    plt.tight_layout()
    plt.savefig('density_comparison.png', dpi=150, bbox_inches='tight')
    print("\nComparación guardada en 'density_comparison.png'")
    plt.show()


def example_4_parameter_study():
    """Ejemplo 4: Estudio de parámetros (probabilidad de desaceleración)."""
    print("\n" + "=" * 60)
    print("EJEMPLO 4: Estudio del parámetro p_slow")
    print("=" * 60)
    
    p_slow_values = [0.0, 0.2, 0.5, 0.8]
    results = []
    
    for p_slow in p_slow_values:
        print(f"\nSimulando con p_slow = {p_slow:.1f}...")
        
        # Crear simulación
        sim = TrafficSimulation(
            graph_file='data/map_reduced.osm',
            cell_length=7.5,
            v_max=5,
            p_slow=p_slow
        )
        
        # Inicializar vehículos
        sim.initialize_vehicles(density=0.25)
        
        # Ejecutar simulación
        for _ in range(100):
            sim.step()
        
        results.append({
            'p_slow': p_slow,
            'avg_velocities': sim.avg_velocities,
            'final_avg': sim.avg_velocities[-1]
        })
    
    # Visualizar resultados
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Evolución temporal
    for result in results:
        axes[0].plot(result['avg_velocities'], 
                    label=f"p_slow = {result['p_slow']:.1f}")
    axes[0].set_xlabel('Paso de tiempo')
    axes[0].set_ylabel('Velocidad promedio')
    axes[0].set_title('Evolución de la velocidad promedio')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # Velocidad final vs p_slow
    p_values = [r['p_slow'] for r in results]
    final_v = [r['final_avg'] for r in results]
    axes[1].plot(p_values, final_v, 'o-', linewidth=2, markersize=8)
    axes[1].set_xlabel('Probabilidad de desaceleración (p_slow)')
    axes[1].set_ylabel('Velocidad promedio final')
    axes[1].set_title('Efecto de p_slow en la velocidad promedio')
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('parameter_study.png', dpi=150, bbox_inches='tight')
    print("\nEstudio de parámetros guardado en 'parameter_study.png'")
    plt.show()


def example_5_custom_scenario():
    """Ejemplo 5: Escenario personalizado con parámetros específicos."""
    print("\n" + "=" * 60)
    print("EJEMPLO 5: Escenario personalizado")
    print("=" * 60)
    
    # Crear simulación con parámetros personalizados
    sim = TrafficSimulation(
        graph_file='data/map_reduced.osm',
        cell_length=5.0,   # Celdas más pequeñas para mayor resolución
        v_max=8,           # Velocidad máxima mayor
        p_slow=0.2         # Menos desaceleración aleatoria
    )
    
    print("\nParámetros personalizados:")
    print(f"  - Longitud de celda: {sim.cell_length}m")
    print(f"  - Velocidad máxima: {sim.v_max} celdas/paso")
    print(f"  - Probabilidad de desaceleración: {sim.p_slow}")
    
    # Inicializar vehículos
    sim.initialize_vehicles(density=0.18)
    
    # Ejecutar simulación
    print("\nEjecutando 80 pasos...")
    for i in range(80):
        sim.step()
        if (i + 1) % 20 == 0:
            print(f"  Paso {i + 1}/80 completado")
    
    # Visualizar
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    sim.plot_state(ax=axes[0])
    
    # Estadísticas
    axes[1].plot(sim.avg_velocities, linewidth=2)
    axes[1].set_xlabel('Paso de tiempo')
    axes[1].set_ylabel('Velocidad promedio')
    axes[1].set_title('Evolución de la velocidad promedio')
    axes[1].grid(True, alpha=0.3)
    axes[1].axhline(y=sim.v_max, color='r', linestyle='--', 
                   label=f'v_max = {sim.v_max}')
    axes[1].legend()
    
    plt.tight_layout()
    plt.savefig('custom_scenario.png', dpi=150, bbox_inches='tight')
    print("\nEscenario personalizado guardado en 'custom_scenario.png'")
    plt.show()


def main():
    """Función principal - ejecuta los ejemplos."""
    print("\n" + "=" * 60)
    print("SIMULACIÓN DE TRÁFICO - MODELO DE NAGEL-SCHRECKENBERG")
    print("=" * 60)
    print("\nEste script demuestra el uso de la simulación de tráfico")
    print("sobre un grafo de calles usando el modelo de Nagel-Schreckenberg.")
    print("\n¿Qué ejemplo deseas ejecutar?")
    print("  1 - Simulación básica con densidad media")
    print("  2 - Animación de la simulación")
    print("  3 - Comparar diferentes densidades")
    print("  4 - Estudio del parámetro p_slow")
    print("  5 - Escenario personalizado")
    print("  0 - Ejecutar todos los ejemplos")
    
    choice = input("\nIngresa el número (0-5): ").strip()
    
    examples = {
        '1': example_1_basic_simulation,
        '2': example_2_animation,
        '3': example_3_compare_densities,
        '4': example_4_parameter_study,
        '5': example_5_custom_scenario,
    }
    
    if choice == '0':
        for func in examples.values():
            func()
    elif choice in examples:
        examples[choice]()
    else:
        print("Opción inválida. Ejecutando ejemplo 1 por defecto...")
        example_1_basic_simulation()
    
    print("\n" + "=" * 60)
    print("SIMULACIÓN COMPLETADA")
    print("=" * 60)


if __name__ == '__main__':
    main()
