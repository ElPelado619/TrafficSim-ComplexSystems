"""
Ejemplos avanzados de uso de la simulación de tráfico.
"""

import sys
from pathlib import Path

# Añadir el directorio padre al path para importar el módulo src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.traffic_simulation import TrafficSimulation
import matplotlib.pyplot as plt
import numpy as np


def fundamental_diagram():
    """
    Genera el diagrama fundamental del tráfico: flujo vs densidad.
    Este es un resultado clásico de la teoría de tráfico.
    """
    print("=" * 60)
    print("DIAGRAMA FUNDAMENTAL DEL TRÁFICO")
    print("=" * 60)
    
    densities = np.linspace(0.05, 0.95, 10)
    flows = []
    velocities = []
    
    for density in densities:
        print(f"\nSimulando densidad {density:.2%}...")
        
        sim = TrafficSimulation(
            graph_file='data/map_reduced.osm',
            cell_length=7.5,
            v_max=5,
            p_slow=0.3
        )
        
        sim.initialize_vehicles(density=density)
        
        # Fase de calentamiento
        for _ in range(50):
            sim.step()
        
        # Fase de medición
        measured_flows = []
        measured_velocities = []
        
        for _ in range(50):
            sim.step()
            
            if sim.vehicles:
                avg_v = np.mean([v.velocity for v in sim.vehicles.values()])
                measured_velocities.append(avg_v)
                
                # Flujo = densidad × velocidad
                flow = density * avg_v
                measured_flows.append(flow)
        
        flows.append(np.mean(measured_flows))
        velocities.append(np.mean(measured_velocities))
    
    # Visualizar diagrama fundamental
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    # Flujo vs Densidad
    axes[0].plot(densities, flows, 'o-', linewidth=2, markersize=8)
    axes[0].set_xlabel('Densidad (ρ)', fontsize=12)
    axes[0].set_ylabel('Flujo (J = ρ × v)', fontsize=12)
    axes[0].set_title('Diagrama Fundamental: Flujo vs Densidad', fontsize=14)
    axes[0].grid(True, alpha=0.3)
    
    # Velocidad vs Densidad
    axes[1].plot(densities, velocities, 'o-', linewidth=2, markersize=8, color='red')
    axes[1].set_xlabel('Densidad (ρ)', fontsize=12)
    axes[1].set_ylabel('Velocidad promedio (v)', fontsize=12)
    axes[1].set_title('Velocidad vs Densidad', fontsize=14)
    axes[1].grid(True, alpha=0.3)
    
    # Flujo vs Velocidad
    axes[2].plot(velocities, flows, 'o-', linewidth=2, markersize=8, color='green')
    axes[2].set_xlabel('Velocidad promedio (v)', fontsize=12)
    axes[2].set_ylabel('Flujo (J)', fontsize=12)
    axes[2].set_title('Flujo vs Velocidad', fontsize=14)
    axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('fundamental_diagram.png', dpi=150, bbox_inches='tight')
    print("\n✓ Diagrama fundamental guardado en 'fundamental_diagram.png'")
    plt.show()


def phase_transition():
    """
    Estudia la transición de fase entre flujo libre y congestionado.
    """
    print("\n" + "=" * 60)
    print("TRANSICIÓN DE FASE: FLUJO LIBRE ↔ CONGESTIÓN")
    print("=" * 60)
    
    # Densidades cerca de la transición de fase
    densities = [0.10, 0.20, 0.25, 0.30, 0.40]
    
    fig, axes = plt.subplots(len(densities), 1, figsize=(12, 3*len(densities)))
    
    for idx, density in enumerate(densities):
        print(f"\nSimulando densidad {density:.0%}...")
        
        sim = TrafficSimulation(
            graph_file='data/map_reduced.osm',
            cell_length=7.5,
            v_max=5,
            p_slow=0.3
        )
        
        sim.initialize_vehicles(density=density)
        
        # Simular más tiempo para observar la transición
        for _ in range(200):
            sim.step()
        
        # Graficar evolución
        axes[idx].plot(sim.avg_velocities, linewidth=2)
        axes[idx].set_ylabel('Velocidad promedio', fontsize=10)
        axes[idx].set_title(f'Densidad = {density:.0%}', fontsize=12, fontweight='bold')
        axes[idx].grid(True, alpha=0.3)
        axes[idx].axhline(y=sim.v_max, color='r', linestyle='--', alpha=0.5, label='v_max')
        
        # Identificar régimen
        final_v = np.mean(sim.avg_velocities[-20:])
        if final_v > 0.8 * sim.v_max:
            regime = "FLUJO LIBRE"
            color = 'green'
        elif final_v > 0.4 * sim.v_max:
            regime = "FLUJO SINCRONIZADO"
            color = 'orange'
        else:
            regime = "CONGESTIÓN"
            color = 'red'
        
        axes[idx].text(0.02, 0.95, regime, transform=axes[idx].transAxes,
                      fontsize=11, fontweight='bold', color=color,
                      verticalalignment='top',
                      bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    axes[-1].set_xlabel('Paso de tiempo', fontsize=11)
    
    plt.tight_layout()
    plt.savefig('phase_transition.png', dpi=150, bbox_inches='tight')
    print("\n✓ Transición de fase guardada en 'phase_transition.png'")
    plt.show()


def stochasticity_effect():
    """
    Analiza el efecto de la estocasticidad (p_slow) en la formación de atascos.
    """
    print("\n" + "=" * 60)
    print("EFECTO DE LA ESTOCASTICIDAD EN ATASCOS")
    print("=" * 60)
    
    p_slow_values = [0.0, 0.1, 0.3, 0.5]
    density = 0.25  # Densidad cerca de la transición
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()
    
    for idx, p_slow in enumerate(p_slow_values):
        print(f"\nSimulando con p_slow = {p_slow:.1f}...")
        
        sim = TrafficSimulation(
            graph_file='data/map_reduced.osm',
            cell_length=7.5,
            v_max=5,
            p_slow=p_slow
        )
        
        sim.initialize_vehicles(density=density)
        
        # Simular
        for _ in range(150):
            sim.step()
        
        # Graficar
        axes[idx].plot(sim.avg_velocities, linewidth=2)
        axes[idx].set_xlabel('Paso de tiempo')
        axes[idx].set_ylabel('Velocidad promedio')
        axes[idx].set_title(f'p_slow = {p_slow:.1f}', fontsize=13, fontweight='bold')
        axes[idx].grid(True, alpha=0.3)
        axes[idx].axhline(y=sim.v_max, color='r', linestyle='--', alpha=0.5)
        
        # Calcular varianza
        variance = np.var(sim.avg_velocities[-50:])
        axes[idx].text(0.02, 0.95, f'Varianza: {variance:.3f}',
                      transform=axes[idx].transAxes,
                      fontsize=10, verticalalignment='top',
                      bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))
    
    plt.tight_layout()
    plt.savefig('stochasticity_effect.png', dpi=150, bbox_inches='tight')
    print("\n✓ Efecto de estocasticidad guardado en 'stochasticity_effect.png'")
    plt.show()


def relaxation_time():
    """
    Estudia el tiempo de relajación: cuánto tarda el sistema en alcanzar el estado estacionario.
    """
    print("\n" + "=" * 60)
    print("TIEMPO DE RELAJACIÓN")
    print("=" * 60)
    
    print("\nSimulando desde estado inicial aleatorio...")
    
    sim = TrafficSimulation(
        graph_file='data/map_reduced.osm',
        cell_length=7.5,
        v_max=5,
        p_slow=0.3
    )
    
    # Inicializar con velocidades aleatorias
    sim.initialize_vehicles(density=0.25)
    
    # Dar velocidades aleatorias iniciales
    for vehicle in sim.vehicles.values():
        vehicle.velocity = np.random.randint(0, sim.v_max + 1)
    
    # Simular largo tiempo
    for _ in range(300):
        sim.step()
    
    # Calcular media móvil para identificar estabilización
    window = 20
    moving_avg = np.convolve(sim.avg_velocities, 
                             np.ones(window)/window, 
                             mode='valid')
    
    # Graficar
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))
    
    # Evolución temporal
    axes[0].plot(sim.avg_velocities, alpha=0.5, label='Velocidad instantánea')
    axes[0].plot(range(window-1, len(sim.avg_velocities)), 
                moving_avg, linewidth=2, color='red', 
                label=f'Media móvil (ventana={window})')
    axes[0].set_xlabel('Paso de tiempo')
    axes[0].set_ylabel('Velocidad promedio')
    axes[0].set_title('Relajación al Estado Estacionario', fontsize=14)
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()
    
    # Cambio relativo (derivada)
    diff = np.diff(moving_avg)
    axes[1].plot(diff, linewidth=2, color='blue')
    axes[1].axhline(y=0, color='r', linestyle='--', alpha=0.5)
    axes[1].set_xlabel('Paso de tiempo')
    axes[1].set_ylabel('Cambio en velocidad promedio')
    axes[1].set_title('Tasa de Cambio (indicador de estabilización)', fontsize=14)
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('relaxation_time.png', dpi=150, bbox_inches='tight')
    print("\n✓ Tiempo de relajación guardado en 'relaxation_time.png'")
    plt.show()


def spatial_temporal_diagram():
    """
    Crea un diagrama espacio-temporal mostrando la evolución de los vehículos.
    Similar a los diagramas clásicos de NS.
    """
    print("\n" + "=" * 60)
    print("DIAGRAMA ESPACIO-TEMPORAL")
    print("=" * 60)
    
    print("\nSimulando...")
    
    sim = TrafficSimulation(
        graph_file='data/map_reduced.osm',
        cell_length=7.5,
        v_max=5,
        p_slow=0.3
    )
    
    sim.initialize_vehicles(density=0.3)
    
    # Rastrear posiciones en el tiempo
    num_steps = 100
    history = []
    
    for _ in range(num_steps):
        sim.step()
        
        # Guardar estado actual
        positions = []
        for vehicle in sim.vehicles.values():
            # Codificar posición como un número único basado en edge y position
            edge_hash = hash(vehicle.edge) % 1000
            pos_encoded = edge_hash + vehicle.position / 1000
            positions.append((vehicle.id, pos_encoded, vehicle.velocity))
        
        history.append(positions)
    
    # Crear diagrama (solo para algunos vehículos representativos)
    vehicle_ids = list(sim.vehicles.keys())[:20]  # Primeros 20 vehículos
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    for vid in vehicle_ids:
        trajectory = []
        velocities = []
        
        for t, state in enumerate(history):
            for veh_id, pos, vel in state:
                if veh_id == vid:
                    trajectory.append((t, pos))
                    velocities.append(vel)
                    break
        
        if trajectory:
            times = [t for t, p in trajectory]
            positions = [p for t, p in trajectory]
            
            scatter = ax.scatter(times, positions, c=velocities, 
                               cmap='RdYlGn', s=10, vmin=0, vmax=sim.v_max)
    
    ax.set_xlabel('Tiempo (pasos)', fontsize=12)
    ax.set_ylabel('Posición (codificada)', fontsize=12)
    ax.set_title('Diagrama Espacio-Temporal\n(Trayectorias de vehículos)', fontsize=14)
    
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Velocidad', fontsize=11)
    
    plt.tight_layout()
    plt.savefig('spacetime_diagram.png', dpi=150, bbox_inches='tight')
    print("\n✓ Diagrama espacio-temporal guardado en 'spacetime_diagram.png'")
    plt.show()


def main():
    """Menú principal de ejemplos avanzados."""
    print("=" * 60)
    print("EJEMPLOS AVANZADOS - SIMULACIÓN DE TRÁFICO")
    print("=" * 60)
    print("\nEstos ejemplos realizan análisis científicos del modelo:")
    print()
    print("  1 - Diagrama fundamental del tráfico")
    print("  2 - Transición de fase (flujo libre ↔ congestión)")
    print("  3 - Efecto de la estocasticidad (p_slow)")
    print("  4 - Tiempo de relajación")
    print("  5 - Diagrama espacio-temporal")
    print("  0 - Ejecutar todos los análisis")
    
    choice = input("\nIngresa el número (0-5): ").strip()
    
    examples = {
        '1': fundamental_diagram,
        '2': phase_transition,
        '3': stochasticity_effect,
        '4': relaxation_time,
        '5': spatial_temporal_diagram,
    }
    
    if choice == '0':
        for func in examples.values():
            func()
    elif choice in examples:
        examples[choice]()
    else:
        print("Opción inválida.")
    
    print("\n" + "=" * 60)
    print("ANÁLISIS COMPLETADO")
    print("=" * 60)


if __name__ == '__main__':
    main()
