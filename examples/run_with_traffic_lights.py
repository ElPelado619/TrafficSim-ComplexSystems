#!/usr/bin/env python3
"""
Script completo que ejecuta el flujo:
1. Cargar zonas
2. Cargar matriz O-D
3. Optimizar semáforos con algoritmo genético
4. Ejecutar simulación con semáforos optimizados

Uso:
    python examples/run_with_traffic_lights.py \\
        --zones data/O-D-maps/microcentro_zones.json \\
        --od data/O-D-maps/microcentro_zones_matrix.json \\
        --optimize-lights \\
        --save-lights data/traffic_lights.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import osmnx as ox
from matplotlib import patches
from matplotlib.colors import Normalize

# Añadir la raíz del repositorio para importar módulos locales
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.traffic_simulation import TrafficSimulation
from src.traffic_light import TrafficLightSystem
import generador_od
from generador_semaforos import GeneticOptimizer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simular tráfico con semáforos optimizados mediante algoritmo genético"
    )
    parser.add_argument(
        "--graph",
        type=Path,
        default=Path("data/microcentro.graphml"),
        help="Archivo GraphML con la red vial"
    )
    parser.add_argument(
        "--zones",
        type=Path,
        default=Path("data/O-D-maps/microcentro_zones.json"),
        help="Archivo JSON con la definición de zonas"
    )
    parser.add_argument(
        "--od",
        type=Path,
        default=Path("data/O-D-maps/microcentro_zones_matrix.json"),
        help="Archivo JSON con la matriz O-D"
    )
    parser.add_argument(
        "--optimize-lights",
        action="store_true",
        help="Optimizar semáforos con algoritmo genético"
    )
    parser.add_argument(
        "--lights-file",
        type=Path,
        help="Archivo JSON con configuración de semáforos (si no se optimiza)"
    )
    parser.add_argument(
        "--save-lights",
        type=Path,
        help="Guardar configuración optimizada de semáforos"
    )
    parser.add_argument(
        "--population",
        type=int,
        default=30,
        help="Tamaño de la población para el algoritmo genético"
    )
    parser.add_argument(
        "--generations",
        type=int,
        default=20,
        help="Número de generaciones para el algoritmo genético"
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=0.01,
        help="Factor de escala para la demanda O-D"
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=1000,
        help="Número de pasos de simulación"
    )
    parser.add_argument(
        "--cell-length",
        type=float,
        default=7.5,
        help="Longitud de celda en metros"
    )
    parser.add_argument(
        "--v-max",
        type=int,
        default=5,
        help="Velocidad máxima en celdas por paso"
    )
    parser.add_argument(
        "--p-slow",
        type=float,
        default=0.3,
        help="Probabilidad de desaceleración aleatoria"
    )
    parser.add_argument(
        "--save-prefix",
        type=Path,
        help="Prefijo para guardar archivos de salida"
    )
    parser.add_argument(
        "--animation-gif",
        type=Path,
        help="Guardar animación como GIF"
    )
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="No mostrar gráficos en pantalla"
    )
    
    return parser.parse_args()


def main():
    args = parse_args()
    
    # Verificar archivos de entrada
    if not args.graph.exists():
        print(f"❌ Error: No se encontró el archivo de grafo: {args.graph}")
        return 1
    
    if not args.zones.exists():
        print(f"❌ Error: No se encontró el archivo de zonas: {args.zones}")
        return 1
    
    if not args.od.exists():
        print(f"❌ Error: No se encontró el archivo de matriz O-D: {args.od}")
        return 1
    
    print("=" * 70)
    print("SIMULACIÓN DE TRÁFICO CON SEMÁFOROS OPTIMIZADOS")
    print("=" * 70)
    
    # Paso 1: Cargar zonas y matriz O-D
    print("\n[1/4] Cargando zonas y matriz O-D...")
    zones, _, _, _ = generador_od.load_zone_file(args.zones)
    with open(args.od, 'r', encoding='utf-8') as f:
        od_matrix = json.load(f)
    
    print(f"  ✓ Zonas cargadas: {len(zones)}")
    print(f"  ✓ Pares O-D: {sum(len(dests) for dests in od_matrix.values())}")
    
    # Paso 2: Optimizar o cargar semáforos
    traffic_light_system = None
    
    if args.optimize_lights:
        print("\n[2/4] Optimizando semáforos con algoritmo genético...")
        optimizer = GeneticOptimizer(
            graph_file=args.graph,
            zones_file=args.zones,
            od_matrix_file=args.od,
            population_size=args.population,
            generations=args.generations,
            mutation_rate=0.1,
            elite_size=5,
            simulation_steps=500,
            scale=args.scale,
            min_degree=3
        )
        
        traffic_light_system = optimizer.optimize()
        
        if args.save_lights:
            args.save_lights.parent.mkdir(parents=True, exist_ok=True)
            traffic_light_system.save_to_file(args.save_lights)
            print(f"\n  ✓ Configuración guardada en: {args.save_lights}")
    
    elif args.lights_file:
        print("\n[2/4] Cargando configuración de semáforos...")
        if not args.lights_file.exists():
            print(f"❌ Error: No se encontró el archivo de semáforos: {args.lights_file}")
            return 1
        
        traffic_light_system = TrafficLightSystem.load_from_file(args.lights_file)
        print(f"  ✓ Semáforos cargados: {len(traffic_light_system)}")
    
    else:
        print("\n[2/4] Sin semáforos (usar --optimize-lights o --lights-file)")
    
    # Paso 3: Crear simulación
    print("\n[3/4] Inicializando simulación...")
    sim = TrafficSimulation(
        str(args.graph),
        cell_length=args.cell_length,
        v_max=args.v_max,
        p_slow=args.p_slow
    )
    
    # Instalar semáforos si están disponibles
    if traffic_light_system:
        sim.traffic_lights = traffic_light_system
        print(f"  ✓ Semáforos instalados: {len(sim.traffic_lights)}")
    
    # Generar vehículos desde matriz O-D
    num_vehicles = sim.spawn_from_od_matrix(
        zones,
        od_matrix,
        scale=args.scale,
        random_seed=42
    )
    
    print(f"  ✓ Vehículos generados: {num_vehicles}")
    
    # Paso 4: Ejecutar simulación
    print(f"\n[4/4] Ejecutando simulación ({args.steps} pasos)...")
    
    if args.animation_gif:
        print(f"  Generando animación: {args.animation_gif}")
        args.animation_gif.parent.mkdir(parents=True, exist_ok=True)
        sim.animate(
            steps=args.steps,
            interval=50,
            save_as=str(args.animation_gif),
            show=not args.no_show
        )
    else:
        # Simulación sin animación
        for step in range(args.steps):
            sim.step()
            
            if (step + 1) % 100 == 0:
                avg_v = np.mean([v.velocity for v in sim.vehicles.values()]) if sim.vehicles else 0
                print(f"  Paso {step + 1}/{args.steps} - "
                      f"Vehículos: {len(sim.vehicles)}, "
                      f"Velocidad promedio: {avg_v:.2f}")
    
    # Imprimir reporte detallado de estadísticas
    print("\n" + "=" * 70)
    print("RESULTADOS DETALLADOS")
    print("=" * 70)
    
    sim.print_traffic_report()
    
    # Guardar estadísticas
    output_dir = args.save_prefix.parent if args.save_prefix else Path('results')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📊 Guardando estadísticas en '{output_dir}/'...")
    
    # Guardar gráficos de estadísticas en archivos separados
    saved_files = sim.plot_statistics(output_dir=str(output_dir / 'statistics'), show=not args.no_show)
    
    # Guardar gráfico de estado final
    state_file = output_dir / 'estado_final.png'
    fig, ax = plt.subplots(figsize=(12, 12))
    sim.plot_state(ax=ax, show=False)
    plt.savefig(state_file, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✓ Estado final guardado: {state_file}")
    
    print(f"\n📂 Todos los resultados guardados en: {output_dir}/")
    print(f"   - Gráficos de estadísticas: {len(saved_files)} archivos PNG")
    print(f"   - Estado final: estado_final.png")
    
    print("\n✓ Simulación completada exitosamente")
    return 0


if __name__ == "__main__":
    sys.exit(main())
