"""
Generador de semáforos optimizados mediante algoritmo genético.

Este módulo entrena los tiempos de semáforos para minimizar la congestión 
en la red vial utilizando un algoritmo genético simple.

Uso:
    python generador_semaforos.py \\
        --graph data/microcentro.graphml \\
        --zones data/O-D-maps/microcentro_zones.json \\
        --od data/O-D-maps/microcentro_zones_matrix.json \\
        --output data/traffic_lights.json \\
        --population 50 \\
        --generations 30
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import networkx as nx
import numpy as np
import osmnx as ox
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))

from src.traffic_simulation import TrafficSimulation
from src.traffic_light import TrafficLight, TrafficLightSystem
import generador_od


class TrafficLightChromosome:
    """Representa un cromosoma con configuración de semáforos por dirección."""
    
    def __init__(self, graph: nx.MultiDiGraph, node_ids: List[int], min_time: int = 15, max_time: int = 60):
        """
        Inicializa un cromosoma aleatorio.
        
        Args:
            graph: Grafo de la red vial para identificar direcciones
            node_ids: Lista de IDs de nodos donde colocar semáforos
            min_time: Tiempo mínimo de verde/rojo
            max_time: Tiempo máximo de verde/rojo
        """
        self.graph = graph
        self.node_ids = node_ids
        self.min_time = min_time
        self.max_time = max_time
        
        # Genes: para cada (node_id, from_node), almacenar (green_time, phase_offset)
        # Calles perpendiculares tendrán phase_offset desfasado para coordinación
        self.genes: Dict[Tuple[int, int], Tuple[int, int]] = {}
        
        for node_id in node_ids:
            # Obtener todas las aristas que llegan a este nodo
            in_edges = list(self.graph.in_edges(node_id, keys=True))
            
            if not in_edges:
                continue
            
            # Generar tiempo de ciclo común para este nodo
            green_time = random.randint(min_time, max_time)
            cycle_time = green_time * 2
            
            # Agrupar aristas por dirección (detectar perpendiculares)
            edge_groups = self._group_perpendicular_edges(node_id, in_edges)
            
            # Asignar fases: grupo 0 empieza en verde, grupo 1 empieza en rojo
            for group_idx, edges_in_group in enumerate(edge_groups):
                # Calcular phase_offset: grupo 0 tiene offset 0, grupo 1 tiene offset = green_time
                phase_offset = (group_idx * green_time) % cycle_time
                
                for from_node, _, _ in edges_in_group:
                    key = (node_id, from_node)
                    self.genes[key] = (green_time, phase_offset)
        
        self.fitness = None
    
    def _group_perpendicular_edges(self, node_id: int, in_edges: List[Tuple]) -> List[List[Tuple]]:
        """
        Agrupa aristas que llegan a un nodo según su dirección.
        Detecta calles perpendiculares para coordinar semáforos.
        
        Returns:
            Lista de grupos de aristas (máximo 2 grupos para calles perpendiculares)
        """
        if len(in_edges) <= 1:
            return [in_edges]
        
        # Obtener coordenadas del nodo de intersección
        node_data = self.graph.nodes[node_id]
        node_x, node_y = node_data['x'], node_data['y']
        
        # Calcular ángulo de llegada de cada arista
        angles = []
        for from_node, to_node, key in in_edges:
            from_data = self.graph.nodes[from_node]
            from_x, from_y = from_data['x'], from_data['y']
            
            # Calcular ángulo de la dirección de llegada
            dx = node_x - from_x
            dy = node_y - from_y
            angle = np.arctan2(dy, dx)  # Ángulo en radianes [-π, π]
            angles.append((angle, (from_node, to_node, key)))
        
        # Si solo hay 2 aristas, separarlas en 2 grupos
        if len(angles) == 2:
            return [[angles[0][1]], [angles[1][1]]]
        
        # Para más aristas, agrupar por cuadrantes
        # Normalizar ángulos a [0, 2π)
        normalized_angles = [(a % (2 * np.pi), edge) for a, edge in angles]
        normalized_angles.sort(key=lambda x: x[0])
        
        # Dividir en dos grupos principales: horizontal (E-W) y vertical (N-S)
        # Grupo 0: ángulos alrededor de 0° y 180° (E-W)
        # Grupo 1: ángulos alrededor de 90° y 270° (N-S)
        group_0 = []  # Este-Oeste
        group_1 = []  # Norte-Sur
        
        for angle, edge in normalized_angles:
            # Ángulo en grados para facilitar la lógica
            angle_deg = np.degrees(angle)
            
            # Clasificar según proximidad a ejes cardinales
            # E-W: 315-45° o 135-225°
            # N-S: 45-135° o 225-315°
            if (angle_deg >= 315 or angle_deg < 45) or (135 <= angle_deg < 225):
                group_0.append(edge)
            else:
                group_1.append(edge)
        
        # Si un grupo está vacío, poner todo en un grupo
        if not group_0:
            return [group_1]
        if not group_1:
            return [group_0]
        
        return [group_0, group_1]
    
    def to_traffic_light_system(self) -> TrafficLightSystem:
        """Convierte el cromosoma en un sistema de semáforos."""
        system = TrafficLightSystem()
        for (node_id, from_node), (green_time, phase_offset) in self.genes.items():
            light = TrafficLight(
                node_id=node_id,
                from_node=from_node,
                green_time=green_time,
                red_time=green_time,
                phase_offset=phase_offset
            )
            system.add_light(light)
        return system
    
    def mutate(self, mutation_rate: float = 0.1):
        """Aplica mutación aleatoria a los genes."""
        # Agrupar genes por nodo para mantener consistencia en el ciclo
        nodes_to_mutate = set()
        
        for key in self.genes:
            if random.random() < mutation_rate:
                node_id, from_node = key
                nodes_to_mutate.add(node_id)
        
        # Mutar cada nodo completo (todas sus direcciones)
        for node_id in nodes_to_mutate:
            # Obtener todos los genes de este nodo
            node_genes = {k: v for k, v in self.genes.items() if k[0] == node_id}
            
            if not node_genes:
                continue
            
            # Tomar el green_time actual (debe ser igual para todas las direcciones)
            current_green_time = list(node_genes.values())[0][0]
            
            # Mutar el tiempo de verde
            delta = random.randint(-5, 5)
            new_green_time = max(self.min_time, min(self.max_time, current_green_time + delta))
            new_cycle_time = new_green_time * 2
            
            # Obtener aristas que llegan a este nodo
            in_edges = list(self.graph.in_edges(node_id, keys=True))
            edge_groups = self._group_perpendicular_edges(node_id, in_edges)
            
            # Reasignar phase_offsets manteniendo la estructura de grupos
            for group_idx, edges_in_group in enumerate(edge_groups):
                phase_offset = (group_idx * new_green_time) % new_cycle_time
                
                for from_node, _, _ in edges_in_group:
                    key = (node_id, from_node)
                    if key in self.genes:
                        self.genes[key] = (new_green_time, phase_offset)
    
    @classmethod
    def crossover(cls, parent1: 'TrafficLightChromosome', parent2: 'TrafficLightChromosome') -> 'TrafficLightChromosome':
        """Crea un hijo mediante crossover de dos padres."""
        child = cls.__new__(cls)
        child.graph = parent1.graph
        child.node_ids = parent1.node_ids
        child.min_time = parent1.min_time
        child.max_time = parent1.max_time
        child.genes = {}
        child.fitness = None
        
        # Crossover por nodos completos (mantener consistencia en cada intersección)
        for node_id in parent1.node_ids:
            # Elegir de cuál padre tomar los genes de este nodo
            if random.random() < 0.5:
                source_parent = parent1
            else:
                source_parent = parent2
            
            # Copiar todos los genes de este nodo del padre seleccionado
            for key, value in source_parent.genes.items():
                if key[0] == node_id:
                    child.genes[key] = value
        
        return child


class GeneticOptimizer:
    """Optimizador genético para tiempos de semáforos."""
    
    def __init__(
        self,
        graph_file: Path,
        zones_file: Path,
        od_matrix_file: Path,
        population_size: int = 50,
        generations: int = 30,
        mutation_rate: float = 0.1,
        elite_size: int = 5,
        simulation_steps: int = 500,
        scale: float = 0.01,
        min_degree: int = 3
    ):
        """
        Inicializa el optimizador genético.
        
        Args:
            graph_file: Archivo del grafo de calles
            zones_file: Archivo con definición de zonas
            od_matrix_file: Archivo con matriz O-D
            population_size: Tamaño de la población
            generations: Número de generaciones a evolucionar
            mutation_rate: Tasa de mutación (0-1)
            elite_size: Número de mejores individuos a preservar
            simulation_steps: Pasos de simulación para evaluar fitness
            scale: Factor de escala para la matriz O-D
            min_degree: Grado mínimo para que un nodo tenga semáforo
        """
        self.graph_file = graph_file
        self.zones_file = zones_file
        self.od_matrix_file = od_matrix_file
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.elite_size = elite_size
        self.simulation_steps = simulation_steps
        self.scale = scale
        self.min_degree = min_degree
        
        # Cargar grafo y matriz O-D
        self.graph = self._load_graph()
        self.zones, self.od_matrix = self._load_zones_and_od()
        
        # Identificar nodos candidatos para semáforos (intersecciones importantes)
        self.candidate_nodes = self._identify_intersections()
        
        print(f"Identificados {len(self.candidate_nodes)} nodos candidatos para semáforos")
    
    def _load_graph(self) -> nx.MultiDiGraph:
        """Carga el grafo de la red vial."""
        if self.graph_file.suffix == '.osm':
            graph = ox.graph_from_xml(str(self.graph_file))
        else:
            graph = ox.load_graphml(str(self.graph_file))
        
        if not graph.is_directed():
            graph = graph.to_directed()
        
        return graph
    
    def _load_zones_and_od(self) -> Tuple[Dict, Dict]:
        """Carga las zonas y la matriz O-D."""
        zones, _, _, _ = generador_od.load_zone_file(self.zones_file)
        
        with open(self.od_matrix_file, 'r', encoding='utf-8') as f:
            od_matrix = json.load(f)
        
        return zones, od_matrix
    
    def _identify_intersections(self) -> List[int]:
        """Identifica nodos importantes para colocar semáforos."""
        candidates = []
        
        # Identificar nodos que son parte de rotondas
        roundabout_nodes = set()
        for u, v, key, data in self.graph.edges(keys=True, data=True):
            # Verificar si la arista es parte de una rotonda
            if 'junction' in data:
                junction_type = data['junction']
                if junction_type in ['roundabout', 'circular']:
                    roundabout_nodes.add(u)
                    roundabout_nodes.add(v)
        
        for node_id in self.graph.nodes():
            # Excluir nodos que son parte de rotondas
            if node_id in roundabout_nodes:
                continue
            
            # Contar grado del nodo (entradas + salidas)
            in_degree = self.graph.in_degree(node_id)
            out_degree = self.graph.out_degree(node_id)
            total_degree = in_degree + out_degree
            
            # Considerar nodos con suficiente conectividad
            if total_degree >= self.min_degree:
                candidates.append(node_id)
        
        if roundabout_nodes:
            print(f"  ℹ️  Excluidos {len(roundabout_nodes)} nodos de rotondas")
        
        return candidates
    
    def _evaluate_fitness(self, chromosome: TrafficLightChromosome) -> float:
        """
        Evalúa el fitness de un cromosoma mediante simulación.
        
        Métricas consideradas:
        - Velocidad promedio de los vehículos (mayor es mejor)
        - Tiempo total de viaje (menor es mejor)
        - Fluidez del tráfico (menor varianza en velocidades)
        
        Returns:
            Valor de fitness (mayor es mejor)
        """
        # Crear simulación con semáforos
        sim = TrafficSimulation(
            str(self.graph_file),
            cell_length=7.5,
            v_max=5,
            p_slow=0.3
        )
        
        # Instalar sistema de semáforos
        traffic_light_system = chromosome.to_traffic_light_system()
        sim.traffic_lights = traffic_light_system
        
        # Generar vehículos desde matriz O-D
        num_vehicles = sim.spawn_from_od_matrix(
            self.zones,
            self.od_matrix,
            scale=self.scale,
            random_seed=42
        )
        
        if num_vehicles == 0:
            return 0.0
        
        # Ejecutar simulación
        velocities = []
        
        for _ in range(self.simulation_steps):
            sim.step()
            
            # Recopilar velocidades
            if sim.vehicles:
                avg_velocity = np.mean([v.velocity for v in sim.vehicles.values()])
                velocities.append(avg_velocity)
        
        # Calcular métricas de fitness
        if len(velocities) == 0:
            return 0.0
        
        mean_velocity = np.mean(velocities)
        velocity_std = np.std(velocities)
        
        # Fitness = velocidad promedio alta + baja varianza
        # Normalizar para que esté en un rango razonable
        fitness = mean_velocity - 0.3 * velocity_std
        
        return max(0.0, fitness)
    
    def _create_initial_population(self) -> List[TrafficLightChromosome]:
        """Crea la población inicial aleatoria."""
        population = []
        for _ in range(self.population_size):
            chromosome = TrafficLightChromosome(self.graph, self.candidate_nodes)
            population.append(chromosome)
        return population
    
    def _select_parents(self, population: List[TrafficLightChromosome]) -> Tuple[TrafficLightChromosome, TrafficLightChromosome]:
        """Selecciona dos padres mediante torneo."""
        tournament_size = 3
        
        def tournament():
            contestants = random.sample(population, tournament_size)
            return max(contestants, key=lambda x: x.fitness)
        
        parent1 = tournament()
        parent2 = tournament()
        return parent1, parent2
    
    def optimize(self) -> TrafficLightSystem:
        """
        Ejecuta el algoritmo genético.
        
        Returns:
            Sistema de semáforos optimizado
        """
        print(f"\nIniciando optimización genética:")
        print(f"  Población: {self.population_size}")
        print(f"  Generaciones: {self.generations}")
        print(f"  Tasa de mutación: {self.mutation_rate}")
        print(f"  Elite: {self.elite_size}")
        print(f"  Nodos con semáforos: {len(self.candidate_nodes)}\n")
        
        # Crear población inicial
        population = self._create_initial_population()
        
        best_fitness_history = []
        avg_fitness_history = []
        
        for generation in range(self.generations):
            print(f"\nGeneración {generation + 1}/{self.generations}")
            
            # Evaluar fitness de cada individuo
            for i, chromosome in enumerate(tqdm(population, desc="Evaluando fitness")):
                if chromosome.fitness is None:
                    chromosome.fitness = self._evaluate_fitness(chromosome)
            
            # Ordenar por fitness
            population.sort(key=lambda x: x.fitness, reverse=True)
            
            # Estadísticas
            best_fitness = population[0].fitness
            avg_fitness = np.mean([c.fitness for c in population])
            best_fitness_history.append(best_fitness)
            avg_fitness_history.append(avg_fitness)
            
            print(f"  Mejor fitness: {best_fitness:.4f}")
            print(f"  Fitness promedio: {avg_fitness:.4f}")
            
            # Crear nueva generación
            new_population = []
            
            # Elitismo: preservar los mejores
            new_population.extend(population[:self.elite_size])
            
            # Generar resto mediante crossover y mutación
            while len(new_population) < self.population_size:
                parent1, parent2 = self._select_parents(population)
                child = TrafficLightChromosome.crossover(parent1, parent2)
                child.mutate(self.mutation_rate)
                new_population.append(child)
            
            population = new_population
        
        # Evaluación final
        print("\nEvaluación final...")
        for chromosome in tqdm(population, desc="Evaluando fitness final"):
            if chromosome.fitness is None:
                chromosome.fitness = self._evaluate_fitness(chromosome)
        
        population.sort(key=lambda x: x.fitness, reverse=True)
        
        best_chromosome = population[0]
        print(f"\n✓ Optimización completada")
        print(f"  Mejor fitness final: {best_chromosome.fitness:.4f}")
        
        return best_chromosome.to_traffic_light_system()


def main():
    parser = argparse.ArgumentParser(
        description="Optimiza tiempos de semáforos usando algoritmo genético"
    )
    parser.add_argument(
        "--graph",
        type=Path,
        default=Path("data/microcentro.graphml"),
        help="Archivo del grafo de la red vial"
    )
    parser.add_argument(
        "--zones",
        type=Path,
        default=Path("data/O-D-maps/microcentro_zones.json"),
        help="Archivo JSON con definición de zonas"
    )
    parser.add_argument(
        "--od",
        type=Path,
        default=Path("data/O-D-maps/microcentro_zones_matrix.json"),
        help="Archivo JSON con matriz O-D"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/traffic_lights.json"),
        help="Archivo de salida para la configuración de semáforos"
    )
    parser.add_argument(
        "--population",
        type=int,
        default=50,
        help="Tamaño de la población"
    )
    parser.add_argument(
        "--generations",
        type=int,
        default=30,
        help="Número de generaciones"
    )
    parser.add_argument(
        "--mutation-rate",
        type=float,
        default=0.1,
        help="Tasa de mutación (0-1)"
    )
    parser.add_argument(
        "--elite-size",
        type=int,
        default=5,
        help="Número de individuos elite a preservar"
    )
    parser.add_argument(
        "--simulation-steps",
        type=int,
        default=500,
        help="Pasos de simulación para evaluar fitness"
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=0.01,
        help="Factor de escala para matriz O-D"
    )
    parser.add_argument(
        "--min-degree",
        type=int,
        default=3,
        help="Grado mínimo de nodo para colocar semáforo"
    )
    
    args = parser.parse_args()
    
    # Verificar archivos de entrada
    if not args.graph.exists():
        print(f"Error: No se encontró el archivo de grafo: {args.graph}")
        return 1
    
    if not args.zones.exists():
        print(f"Error: No se encontró el archivo de zonas: {args.zones}")
        return 1
    
    if not args.od.exists():
        print(f"Error: No se encontró el archivo de matriz O-D: {args.od}")
        return 1
    
    # Ejecutar optimización
    optimizer = GeneticOptimizer(
        graph_file=args.graph,
        zones_file=args.zones,
        od_matrix_file=args.od,
        population_size=args.population,
        generations=args.generations,
        mutation_rate=args.mutation_rate,
        elite_size=args.elite_size,
        simulation_steps=args.simulation_steps,
        scale=args.scale,
        min_degree=args.min_degree
    )
    
    best_system = optimizer.optimize()
    
    # Guardar resultado
    args.output.parent.mkdir(parents=True, exist_ok=True)
    best_system.save_to_file(args.output)
    
    print(f"\n✓ Configuración de semáforos guardada en: {args.output}")
    print(f"  Total de semáforos: {len(best_system)}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
