"""
Simulación de tráfico usando el modelo de Nagel-Schreckenberg
sobre un grafo de calles de OSM.
Versión mejorada con lógica de destinos, enrutamiento inteligente y respawn.
"""

import osmnx as ox
import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Circle
from collections import defaultdict
import random
from pathlib import Path

# Importar el sistema de semáforos
from .traffic_light import TrafficLightSystem


class Vehicle:
    """Representa un vehículo en la simulación."""
    
    def __init__(self, vehicle_id, edge, position, velocity=0, v_max=5, destination_zone=None):
        """
        Inicializa un vehículo.
        
        Args:
            vehicle_id: Identificador único del vehículo
            edge: Tupla (u, v, key) representando la arista en la que está el vehículo
            position: Posición en la arista (0 a longitud de la arista en celdas)
            velocity: Velocidad actual (celdas por paso de tiempo)
            v_max: Velocidad máxima permitida
            destination_zone: Nombre de la zona destino, si aplica
        """
        self.id = vehicle_id
        self.edge = edge  # (u, v, key)
        self.position = position  # Posición en la arista actual
        self.velocity = velocity
        self.v_max = v_max
        self.destination_zone = destination_zone
        self.previous_edge = None  # Arista anterior para evitar retroceso
        self.node_history = []     # Historial de nodos visitados (últimos 3-5 nodos)
        self.color = self._generate_color()
        
        # Estadísticas del vehículo
        self.stopped_time = 0      # Tiempo total parado (velocidad = 0)
        self.total_time = 0        # Tiempo total en la simulación
        self.velocity_history = [] # Historial de velocidades
        self.distance_traveled = 0 # Distancia total recorrida
        
        # Estado de navegación
        self.has_arrived = False   # Flag para indicar si llegó a destino
        self.consecutive_stopped_time = 0  # Tiempo consecutivo parado
    
    def _generate_color(self):
        """Genera un color aleatorio para el vehículo."""
        return (random.random(), random.random(), random.random())


class TrafficSimulation:
    """Simulación de tráfico usando el modelo de Nagel-Schreckenberg."""
    
    def __init__(self, graph_file, cell_length=7.5, v_max=5, p_slow=0.3):
        """
        Inicializa la simulación.
        
        Args:
            graph_file: Archivo .osm o .graphml con el grafo de calles
            cell_length: Longitud de cada celda en metros (default: 7.5m ≈ longitud de un auto)
            v_max: Velocidad máxima en celdas por paso de tiempo
            p_slow: Probabilidad de desaceleración aleatoria (0 a 1)
        """
        # Cargar el grafo
        if graph_file.endswith('.osm'):
            self.graph = ox.graph_from_xml(graph_file)
        else:
            self.graph = ox.load_graphml(graph_file)
        
        # Asegurar que el grafo sea dirigido
        if not self.graph.is_directed():
            self.graph = self.graph.to_directed()
        
        # Parámetros del modelo
        self.cell_length = cell_length
        self.v_max = v_max
        self.p_slow = p_slow
        
        # Discretizar las aristas
        self._discretize_edges()
        
        # Almacenar vehículos
        self.vehicles = {}  # {vehicle_id: Vehicle}
        self.vehicle_counter = 0
        
        # Mapa de ocupación: {edge: {position: vehicle_id}}
        self.edge_occupation = defaultdict(dict)
        
        # Sistema de semáforos
        self.traffic_lights = TrafficLightSystem()
        
        # Datos de navegación y zonas
        self.zone_centroids = {} # {zone_name: (x, y)}
        self.zone_nodes = {}     # {zone_name: set(node_ids)}
        self.od_matrix_cache = None # Para respawnear vehículos
        self.respawn_queue = [] # Almacenará los "pasos de tiempo" en los que un vehículo debe reaparecer
        
        # Estadísticas
        self.time_step = 0
        self.avg_velocities = []
        self.stopped_vehicles_count = []  # Número de vehículos parados por paso
        self.edge_densities = []           # Densidad promedio por arista
        self.congestion_points = []        # Puntos con alta densidad de vehículos
        self.vehicle_stopped_ratio = []    # Porcentaje de vehículos parados
        self.traffic_light_states = []     # Estados de semáforos por paso de tiempo
        self.arrived_vehicles_count = 0    # Contador de vehículos que llegaron a destino
    
    def _discretize_edges(self):
        """Discretiza las aristas del grafo en celdas."""
        for u, v, key, data in self.graph.edges(keys=True, data=True):
            # Obtener longitud de la arista
            if 'length' in data:
                length = data['length']
            else:
                # Calcular longitud usando coordenadas
                u_data = self.graph.nodes[u]
                v_data = self.graph.nodes[v]
                length = ox.distance.great_circle_vec(
                    u_data['y'], u_data['x'],
                    v_data['y'], v_data['x']
                )
            
            # Número de celdas en esta arista
            num_cells = max(1, int(np.ceil(length / self.cell_length)))
            self.graph[u][v][key]['length'] = length
            self.graph[u][v][key]['num_cells'] = num_cells
            
    def set_zones(self, zones_dict):
        """
        Configura las zonas y precalcula centroides para navegación eficiente.
        Args:
            zones_dict: Diccionario {zone_name: [node_id1, node_id2, ...]}
        """
        self.zone_nodes = {k: set(v) for k, v in zones_dict.items()}
        self.zone_centroids = {}
        
        for zone, nodes in zones_dict.items():
            xs = []
            ys = []
            for node in nodes:
                if node in self.graph.nodes:
                    xs.append(self.graph.nodes[node]['x'])
                    ys.append(self.graph.nodes[node]['y'])
            if xs:
                self.zone_centroids[zone] = (np.mean(xs), np.mean(ys))
    
    def add_vehicle(self, edge=None, position=None, velocity=0, destination=None):
        """
        Añade un vehículo a la simulación.
        
        Returns:
            vehicle_id si se añadió exitosamente, None si la posición está ocupada.
        """
        if edge is None:
            # Elegir una arista aleatoria
            edges = list(self.graph.edges(keys=True))
            edge = random.choice(edges)
        
        num_cells = self.graph[edge[0]][edge[1]][edge[2]]['num_cells']
        
        if position is None:
            # Elegir una posición aleatoria
            position = random.randint(0, num_cells - 1)
        
        # Verificar que la posición no esté ocupada
        if position in self.edge_occupation[edge]:
            return None
        
        # Crear vehículo
        vehicle_id = self.vehicle_counter
        self.vehicle_counter += 1

        vehicle = Vehicle(vehicle_id, edge, position, velocity, self.v_max, destination_zone=destination)
        self.vehicles[vehicle_id] = vehicle
        self.edge_occupation[edge][position] = vehicle_id

        return vehicle_id
    
    def initialize_vehicles(self, density=0.2):
        """Inicializa vehículos con una densidad dada de forma aleatoria."""
        total_cells = sum(
            data['num_cells'] 
            for u, v, key, data in self.graph.edges(keys=True, data=True)
        )
        
        # Número de vehículos a crear
        num_vehicles = int(total_cells * density)
        print(f"Inicializando {num_vehicles} vehículos en {total_cells} celdas (densidad: {density:.2%})")
        
        added = 0
        attempts = 0
        max_attempts = num_vehicles * 10
        
        while added < num_vehicles and attempts < max_attempts:
            if self.add_vehicle() is not None:
                added += 1
            attempts += 1
        
        print(f"Vehículos añadidos: {added}")

    def spawn_from_od_matrix(self, zones, od_matrix, scale=1.0, random_seed=None, max_attempts=5):
        """Genera vehículos según una matriz O-D y guarda configuración para respawn."""
        # Guardar configuración para reusar al llegar a destino
        self.set_zones(zones)
        self.od_matrix_cache = {
            'od_matrix': od_matrix,
            'zones': zones,
            'origins': list(od_matrix.keys()) # Lista rápida de orígenes
        }

        if random_seed is not None:
            random.seed(random_seed)

        if scale <= 0:
            raise ValueError("scale must be positive")

        zones_with_edges = {}
        for zone_name, node_ids in zones.items():
            edges = []
            for node_id in node_ids:
                edges.extend(list(self.graph.out_edges(node_id, keys=True)))
            if edges:
                zones_with_edges[zone_name] = edges

        total_added = 0
        for origin_zone, destinations in od_matrix.items():
            origin_edges = zones_with_edges.get(origin_zone)
            if not origin_edges:
                continue
            for destination_zone, demand in destinations.items():
                if demand <= 0:
                    continue
                if destination_zone == origin_zone:
                    continue
                vehicle_count = int(round(demand * scale))
                if vehicle_count <= 0:
                    continue
                for _ in range(vehicle_count):
                    attempts = 0
                    added_id = None
                    while attempts < max_attempts and added_id is None:
                        selected_edge = random.choice(origin_edges)
                        initial_velocity = random.randint(0, self.v_max)
                        added_id = self.add_vehicle(
                            edge=selected_edge,
                            position=0,
                            velocity=initial_velocity,
                            destination=destination_zone,
                        )
                        if added_id is None:
                            added_id = self.add_vehicle(
                                edge=selected_edge,
                                position=None,
                                velocity=initial_velocity,
                                destination=destination_zone,
                            )
                        attempts += 1
                    if added_id is not None:
                        total_added += 1
        return total_added
    
    def load_traffic_lights(self, traffic_lights_file: Path):
        """Carga la configuración de semáforos desde un archivo JSON."""
        self.traffic_lights = TrafficLightSystem.load_from_file(traffic_lights_file)
        print(f"✓ Cargados {len(self.traffic_lights)} semáforos desde {traffic_lights_file}")
    
    def _get_distance_to_next_vehicle(self, vehicle):
        """Calcula la distancia al siguiente vehículo en la misma dirección."""
        edge = vehicle.edge
        position = vehicle.position
        num_cells = self.graph[edge[0]][edge[1]][edge[2]]['num_cells']
        
        # Buscar en la arista actual
        for dist in range(1, num_cells):
            next_pos = position + dist
            if next_pos >= num_cells:
                break
            if next_pos in self.edge_occupation[edge]:
                return dist
        
        # Si no hay vehículo en la arista actual, buscar en aristas siguientes
        distance = num_cells - position
        
        # Buscar nodos siguientes
        current_node = edge[1]  # Nodo al final de la arista actual
        from_node = edge[0]     # Nodo de origen (para verificar semáforo)
        visited = set([edge])
        
        # Verificar si hay semáforo en rojo en el nodo siguiente
        if self.traffic_lights.is_red_at_node(current_node, from_node):
            return distance
        
        # BFS limitado para encontrar el siguiente vehículo
        max_search_distance = self.v_max * 2
        
        for next_edge in self.graph.out_edges(current_node, keys=True):
            if next_edge in visited:
                continue
            
            next_num_cells = self.graph[next_edge[0]][next_edge[1]][next_edge[2]]['num_cells']
            
            for pos in range(next_num_cells):
                if pos in self.edge_occupation[next_edge]:
                    return distance + pos
                if distance + pos >= max_search_distance:
                    return max_search_distance
        
        return max_search_distance

    def _get_greedy_next_edge(self, vehicle, available_edges):
        """
        Selecciona la siguiente arista basándose en una heurística Greedy:
        Minimizar (Distancia a destino + Penalización por Congestión).
        """
        # Si no hay destino o no tenemos datos de zonas, comportamiento aleatorio
        if not vehicle.destination_zone or vehicle.destination_zone not in self.zone_centroids:
            return random.choice(available_edges)
        
        target_x, target_y = self.zone_centroids[vehicle.destination_zone]
        best_edge = None
        min_score = float('inf')
        
        # Factor de penalización por congestión
        # Un valor alto (e.g., 5.0) hace que los autos eviten tráfico activamente
        congestion_penalty = 5.0 
        
        for edge in available_edges:
            u, v, key = edge
            
            # 1. Calcular congestión en la arista candidata
            num_cells = self.graph[u][v][key]['num_cells']
            current_load = len(self.edge_occupation[edge])
            density = current_load / num_cells if num_cells > 0 else 0
            
            # Si la arista está muy llena (>90%), penalización extrema
            if density >= 0.9:
                score_density = 100.0
            else:
                score_density = density * congestion_penalty
            
            # 2. Calcular distancia euclidiana al cuadrado (más rápido que raíz cuadrada)
            # desde el nodo final de la arista candidata hasta el centroide del destino
            v_data = self.graph.nodes[v]
            dist_sq = (v_data['x'] - target_x)**2 + (v_data['y'] - target_y)**2
            
            # 3. Score final (buscamos el mínimo)
            # Score = Distancia * (1 + Factor de Congestión)
            score = dist_sq * (1 + score_density)
            
            if score < min_score:
                min_score = score
                best_edge = edge
        
        return best_edge if best_edge else random.choice(available_edges)
    
    def _move_vehicle(self, vehicle):
        """
        Mueve un vehículo a su nueva posición.
        Maneja llegada a destino y enrutamiento inteligente.
        
        Returns:
            True si el movimiento fue exitoso, False si hubo colisión.
        """
        # --- 1. Verificación de LLEGADA A DESTINO ---
        # Si el vehículo está en un nodo que pertenece a su zona de destino
        if vehicle.destination_zone and vehicle.destination_zone in self.zone_nodes:
            # Verificar si el nodo final de la arista actual está en la zona destino
            current_dest_node = vehicle.edge[1]
            if current_dest_node in self.zone_nodes[vehicle.destination_zone]:
                # Marcar para eliminar al final del step
                vehicle.has_arrived = True
                return True

        # --- 2. Movimiento Normal ---
        old_edge = vehicle.edge
        old_position = vehicle.position
        edge_cells = self.edge_occupation[old_edge]
        observed_vehicle = edge_cells.get(old_position)
        if observed_vehicle != vehicle.id:
            # Re-sincronizar el mapa de ocupación si se perdió la referencia
            edge_cells[old_position] = vehicle.id
        new_position = old_position + vehicle.velocity
        num_cells = self.graph[old_edge[0]][old_edge[1]][old_edge[2]]['num_cells']
        
        # Caso A: Mover dentro de la misma arista
        if new_position < num_cells:
            # Mover dentro de la misma arista
            edge_cells.pop(old_position, None)
            
            if new_position in self.edge_occupation[old_edge]:
                # Colisión - revertir
                self.edge_occupation[old_edge][old_position] = vehicle.id
                vehicle.velocity = 0
                return False
            
            self.edge_occupation[old_edge][new_position] = vehicle.id
            vehicle.position = new_position
            return True
        
        # Caso B: El vehículo sale de la arista actual
        else:
            cells_remaining = new_position - num_cells
            
            # Obtener aristas siguientes
            next_edges = list(self.graph.out_edges(old_edge[1], keys=True))
            
            if not next_edges:
                # Buscar CUALQUIER arista de retorno, no asumir la misma key
                reverse_edge = None
                u, v = old_edge[1], old_edge[0] # Invertir nodos
                
                if self.graph.has_edge(u, v):
                    # Obtener la primera clave válida disponible
                    possible_keys = list(self.graph[u][v].keys())
                    if possible_keys:
                        # Construir la arista de retorno con una clave REAL existente
                        reverse_edge = (u, v, possible_keys[0])
                
                if reverse_edge:
                    next_edges = [reverse_edge]
                else:
                    # Lo marcamos como 'llegado' para que el limpiador lo borre y respawnee
                    vehicle.has_arrived = True 
                    return True

            # Aplicar regla de no retroceso (si hay opciones)
            available_edges = self._filter_available_edges(vehicle, next_edges)
            
            if not available_edges:
                # No hay aristas disponibles - detenerse al final
                edge_cells.pop(old_position, None)
                fallback_position = num_cells - 1
                self.edge_occupation[old_edge][fallback_position] = vehicle.id
                vehicle.position = fallback_position
                vehicle.velocity = 0
                return True
            
            # USAR ENRUTAMIENTO GREEDY 
            next_edge = self._get_greedy_next_edge(vehicle, available_edges)
            
            next_num_cells = self.graph[next_edge[0]][next_edge[1]][next_edge[2]]['num_cells']
            
            if cells_remaining >= next_num_cells:
                # Detener al final si intenta cruzar múltiples aristas en un tick
                cells_remaining = next_num_cells - 1
            
            target_edge_cells = self.edge_occupation[next_edge]

            if cells_remaining in target_edge_cells:
                # Colisión en la siguiente arista
                edge_cells.pop(old_position, None)
                fallback_position = num_cells - 1
                self.edge_occupation[old_edge][fallback_position] = vehicle.id
                vehicle.position = fallback_position
                vehicle.velocity = 0
                return False
            
            # Mover a la nueva arista
            edge_cells.pop(old_position, None)
            target_edge_cells[cells_remaining] = vehicle.id
            
            # Actualizar el historial del vehículo
            previous_edge = vehicle.edge
            vehicle.previous_edge = previous_edge
            vehicle.edge = next_edge
            vehicle.position = cells_remaining
            
            # Actualizar historial de nodos visitados
            if not hasattr(vehicle, 'node_history'):
                vehicle.node_history = []
            
            # Agregar el nodo de origen de la arista anterior al historial
            previous_node = previous_edge[0]
            vehicle.node_history.append(previous_node)
            
            # Mantener solo los últimos 3 nodos en el historial
            if len(vehicle.node_history) > 3:
                vehicle.node_history = vehicle.node_history[-3:]
            
            return True

    def _respawn_vehicle(self):
        """Genera un nuevo vehículo para reemplazar uno que llegó, manteniendo la demanda."""
        if self.od_matrix_cache:
            # Intentar mantener la distribución de la matriz OD
            # Elegir un origen aleatorio de la lista de orígenes válidos
            origin_zone = random.choice(self.od_matrix_cache['origins'])
            
            # Obtener destinos posibles desde este origen
            destinations = self.od_matrix_cache['od_matrix'][origin_zone]
            
            if not destinations: 
                return
            
            # Selección aleatoria de destino (ponderada si se quisiera mejorar)
            dest_zone = random.choice(list(destinations.keys()))
            
            # Encontrar arista de origen válida
            if origin_zone in self.zone_nodes:
                nodes = list(self.zone_nodes[origin_zone])
                if not nodes: return
                
                # Intentar encontrar un nodo de inicio con salida
                for _ in range(5): # 5 intentos
                    start_node = random.choice(nodes)
                    edges = list(self.graph.out_edges(start_node, keys=True))
                    if edges:
                        edge = random.choice(edges)
                        # Añadir vehículo con velocidad inicial baja para evitar colisiones inmediatas
                        self.add_vehicle(edge=edge, position=0, velocity=1, destination=dest_zone)
                        return
        else:
            # Fallback: spawn totalmente aleatorio si no hay matriz OD
            self._spawn_new_vehicle()
    
    def step(self):
        """Ejecuta un paso de tiempo de la simulación."""

        # Antes de mover nada, vemos si debemos re-introducir vehículos
        # que fueron eliminados por atasco.
        
        # Usamos list comprehension para reconstruir la cola, 
        # quitando los que ya deben reaparecer.
        remaining_in_queue = []
        respawn_count = 0

        for respawn_time_step in self.respawn_queue:
            if self.time_step >= respawn_time_step:
                # ¡Tiempo cumplido! Reaparece el vehículo.
                # Usamos la misma lógica que al llegar a destino.
                self._respawn_vehicle()
                respawn_count += 1
            else:
                # Aún no es tiempo, mantener en la cola.
                remaining_in_queue.append(respawn_time_step)
        
        self.respawn_queue = remaining_in_queue

        # Actualizar semáforos
        self.traffic_lights.update_all()        
        
        # Aplicar reglas de Nagel-Schreckenberg
        
        # 1. Aceleración
        for vehicle in list(self.vehicles.values()):
            if vehicle.velocity < vehicle.v_max:
                vehicle.velocity += 1
        
        # 2. Frenado (evitar colisiones y respetar semáforos)
        for vehicle in list(self.vehicles.values()):
            distance = self._get_distance_to_next_vehicle(vehicle)
            if vehicle.velocity >= distance:
                vehicle.velocity = max(0, distance - 1)
        
        # 3. Aleatorización (desaceleración estocástica)
        for vehicle in list(self.vehicles.values()):
            if vehicle.velocity > 0 and random.random() < self.p_slow:
                vehicle.velocity -= 1
        
        # 4. Movimiento y Gestión de Llegadas
        # Parámetros de "paciencia"
        MAX_WAIT_TIME = 50      # Pasos máximos parado antes de eliminarse
        DELAY_RESPAWN_TIME = 10 # Pasos a esperar antes de reaparecer
        
        arrived_ids = []
        stuck_ids = [] # Lista para vehículos atascados

        # 4a. Movimiento y chequeo de estado
        for vid, vehicle in list(self.vehicles.items()):
            self._move_vehicle(vehicle)
            
            if vehicle.has_arrived:
                arrived_ids.append(vid)
                continue # Si llegó, no puede estar atascado

            # Chequeo de bloqueo (Deadlock)
            if vehicle.velocity == 0:
                vehicle.consecutive_stopped_time += 1 # Incrementar paciencia
                
                if vehicle.consecutive_stopped_time > MAX_WAIT_TIME:
                    stuck_ids.append(vid)
            else:
                vehicle.consecutive_stopped_time = 0 # Se movió, resetea paciencia

        # 4b. Procesar vehículos llegados (Respawn inmediato)
        for vid in arrived_ids:
            if vid not in self.vehicles: continue # Pudo ser eliminado por atasco justo antes
            
            veh = self.vehicles[vid]
            # Liberar espacio en el mapa de ocupación si aún está ahí
            if veh.position in self.edge_occupation[veh.edge]:
                if self.edge_occupation[veh.edge][veh.position] == vid:
                    del self.edge_occupation[veh.edge][veh.position]
            
            del self.vehicles[vid]
            self.arrived_vehicles_count += 1
            
            # El respawn por LLEGADA sigue siendo inmediato
            self._respawn_vehicle() 
        
        # 4c. Procesar vehículos atascados (Respawn retardado)
        for vid in stuck_ids:
            if vid in self.vehicles: # Verificar que no fue procesado en "llegados"
                veh = self.vehicles[vid]
                
                # Liberar la celda que está bloqueando
                if veh.position in self.edge_occupation[veh.edge]:
                    del self.edge_occupation[veh.edge][veh.position]
                
                del self.vehicles[vid]
                
                # Añadir a la cola para reaparecer 10 pasos en el futuro
                respawn_at = self.time_step + DELAY_RESPAWN_TIME
                self.respawn_queue.append(respawn_at)
        
        # Actualizar estadísticas de vehículos
        for vehicle in self.vehicles.values():
            vehicle.total_time += 1
            vehicle.velocity_history.append(vehicle.velocity)
            vehicle.distance_traveled += vehicle.velocity
            if vehicle.velocity == 0:
                vehicle.stopped_time += 1
        
        # Actualizar estadísticas globales
        self.time_step += 1
        if self.vehicles:
            avg_v = np.mean([v.velocity for v in self.vehicles.values()])
            self.avg_velocities.append(avg_v)
            
            # Estadísticas de vehículos parados
            stopped_stats = self.get_stopped_vehicles_stats()
            self.stopped_vehicles_count.append(stopped_stats['stopped_vehicles'])
            self.vehicle_stopped_ratio.append(stopped_stats['stopped_ratio'])
            
            # Densidad promedio de aristas
            avg_density = self.get_avg_edge_density()
            self.edge_densities.append(avg_density)
            
            # Puntos de congestión
            congestion = self.get_congestion_points(density_threshold=0.5)
            self.congestion_points.append(len(congestion))
        
        # Guardar estados de semáforos
        traffic_light_state = {
            'time_step': self.time_step,
            'states': {node_id: {'is_red': light.is_red, 'timer': light.timer} 
                       for node_id, light in self.traffic_lights.lights.items()}
        }
        self.traffic_light_states.append(traffic_light_state)
    
    def _filter_available_edges(self, vehicle, next_edges):
        """
        Filtra las aristas disponibles para evitar que el vehículo se dé la vuelta.
        """
        if not next_edges:
            return next_edges
        
        # Construir conjunto de nodos a evitar
        nodes_to_avoid = set()
        
        # 1. Evitar el nodo inmediatamente anterior (U-turn directo)
        if vehicle.previous_edge is not None:
            previous_origin_node = vehicle.previous_edge[0]
            nodes_to_avoid.add(previous_origin_node)
        
        # 2. Evitar nodos del historial reciente (loops cortos)
        if hasattr(vehicle, 'node_history') and vehicle.node_history:
            recent_nodes = vehicle.node_history[-3:]
            nodes_to_avoid.update(recent_nodes)
        
        # 3. Evitar también el nodo de origen de la arista actual
        current_origin = vehicle.edge[0]
        nodes_to_avoid.add(current_origin)
        
        # Filtrar aristas
        available_edges = []
        
        for edge in next_edges:
            destination_node = edge[1]
            if destination_node not in nodes_to_avoid:
                available_edges.append(edge)
        
        # Si después de filtrar no quedan opciones, permitir cualquier opción
        # (Excepción para evitar bloqueos totales en calles sin salida)
        if not available_edges:
            return next_edges
        
        return available_edges
    
    def _spawn_new_vehicle(self):
        """Genera un nuevo vehículo en una ubicación aleatoria del mapa."""
        all_edges = list(self.graph.edges(keys=True))
        
        for attempt in range(20):
            edge = random.choice(all_edges)
            edge_data = self.graph[edge[0]][edge[1]][edge[2]]
            max_position = min(edge_data['num_cells'] // 3, 5)
            position = random.randint(0, max(0, max_position))
            velocity = random.randint(0, min(self.v_max, 3))
            
            new_vehicle_id = self.add_vehicle(edge=edge, position=position, velocity=velocity)
            
            if new_vehicle_id is not None:
                return new_vehicle_id
        return None
    
    def get_edge_density(self, edge):
        """Calcula la densidad de vehículos en una arista específica."""
        num_cells = self.graph[edge[0]][edge[1]][edge[2]]['num_cells']
        num_vehicles = len(self.edge_occupation[edge])
        return num_vehicles / num_cells if num_cells > 0 else 0
    
    def get_congestion_points(self, density_threshold=0.5):
        """Identifica aristas con alta densidad de vehículos (congestión)."""
        congested = []
        for edge in self.graph.edges(keys=True):
            density = self.get_edge_density(edge)
            if density >= density_threshold:
                num_vehicles = len(self.edge_occupation[edge])
                congested.append((edge, density, num_vehicles))
        congested.sort(key=lambda x: x[1], reverse=True)
        return congested
    
    def get_avg_edge_density(self):
        """Calcula la densidad promedio de todas las aristas con vehículos."""
        densities = []
        for edge in self.edge_occupation.keys():
            if self.edge_occupation[edge]:
                densities.append(self.get_edge_density(edge))
        return np.mean(densities) if densities else 0.0
    
    def get_stopped_vehicles_stats(self):
        """Obtiene estadísticas sobre vehículos parados."""
        total = len(self.vehicles)
        stopped = sum(1 for v in self.vehicles.values() if v.velocity == 0)
        return {
            'total_vehicles': total,
            'stopped_vehicles': stopped,
            'stopped_ratio': stopped / total if total > 0 else 0,
            'moving_vehicles': total - stopped
        }

    def get_vehicle_positions(self):
        """Obtiene las posiciones geográficas de todos los vehículos."""
        positions = []
        for vehicle in self.vehicles.values():
            edge = vehicle.edge
            position = vehicle.position
            num_cells = self.graph[edge[0]][edge[1]][edge[2]]['num_cells']
            
            u, v = edge[0], edge[1]
            u_data = self.graph.nodes[u]
            v_data = self.graph.nodes[v]
            
            t = position / num_cells
            lon = u_data['x'] + t * (v_data['x'] - u_data['x'])
            lat = u_data['y'] + t * (v_data['y'] - u_data['y'])
            
            positions.append((lon, lat, vehicle.color, vehicle.velocity))
        return positions
    
    def plot_state(self, ax=None, show_velocity=True, show=True):
        """Visualiza el estado actual de la simulación."""
        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 12))
        
        ox.plot_graph(self.graph, ax=ax, show=False, close=False, 
                      node_size=0, edge_linewidth=0.5, edge_color='gray')
        
        # Dibujar semáforos
        for node_id in self.traffic_lights.get_all_node_ids():
            node_data = self.graph.nodes[node_id]
            x, y = node_data['x'], node_data['y']
            lights = self.traffic_lights.get_lights_at_node(node_id)
            num_lights = len(lights)
            for i, light in enumerate(lights):
                angle = (2 * np.pi * i) / num_lights if num_lights > 0 else 0
                x_offset = 0.00003 * np.cos(angle)
                y_offset = 0.00003 * np.sin(angle)
                color = 'red' if light.is_red else 'green'
                circle = Circle((x + x_offset, y + y_offset), radius=0.00002, 
                              color=color, zorder=4, 
                              edgecolor='black', linewidth=1.0, alpha=0.9)
                ax.add_patch(circle)
        
        # Dibujar vehículos
        positions = self.get_vehicle_positions()
        if positions:
            lons = [p[0] for p in positions]
            lats = [p[1] for p in positions]
            
            if show_velocity:
                velocities = [p[3] for p in positions]
                scatter = ax.scatter(lons, lats, c=velocities, cmap='gist_rainbow_r', 
                                   s=15, zorder=5, vmin=0, vmax=self.v_max,
                                   edgecolors='black', linewidths=0.5, marker='^')
                plt.colorbar(scatter, ax=ax, label='Velocidad')
            else:
                colors = [p[2] for p in positions]
                ax.scatter(lons, lats, c=colors, s=15, zorder=5,
                          edgecolors='black', linewidths=0.5, marker='^')
        
        ax.set_title(f'Simulación - Paso {self.time_step} | Vehículos: {len(self.vehicles)}\n'
                    f'Llegadas a destino: {self.arrived_vehicles_count}')
        
        if show and ax.figure:
            plt.show()
        return ax
    
    def animate(self, steps=100, interval=100, save_as=None, show=True):
        """Crea una animación de la simulación."""
        fig, ax = plt.subplots(figsize=(12, 12))
        
        ox.plot_graph(self.graph, ax=ax, show=False, close=False,
                      node_size=0, edge_linewidth=0.5, edge_color='gray')
        
        scatter = ax.scatter([], [], s=15, zorder=5, edgecolors='black', linewidths=0.5, marker='^')
        title = ax.set_title('')
        
        # Preparar círculos para semáforos
        traffic_light_circles = {}
        for node_id in self.traffic_lights.get_all_node_ids():
            node_data = self.graph.nodes[node_id]
            x, y = node_data['x'], node_data['y']
            lights = self.traffic_lights.get_lights_at_node(node_id)
            num_lights = len(lights)
            for i, light in enumerate(lights):
                angle = (2 * np.pi * i) / num_lights if num_lights > 0 else 0
                x_offset = 0.00003 * np.cos(angle)
                y_offset = 0.00003 * np.sin(angle)
                circle = Circle((x + x_offset, y + y_offset), radius=0.00002, 
                              color='green', zorder=4,
                              edgecolor='black', linewidth=1.0, alpha=0.9)
                ax.add_patch(circle)
                traffic_light_circles[(node_id, light.from_node)] = circle
        
        def init():
            scatter.set_offsets(np.empty((0, 2)))
            return scatter, title
        
        def update(frame):
            self.step()
            
            # Actualizar semáforos
            for key, circle in traffic_light_circles.items():
                node_id, from_node = key
                light = self.traffic_lights.get_light(node_id, from_node)
                if light:
                    circle.set_color('red' if light.is_red else 'green')
            
            # Obtener posiciones
            positions = self.get_vehicle_positions()
            if positions:
                lons = [p[0] for p in positions]
                lats = [p[1] for p in positions]
                velocities = [p[3] for p in positions]
                
                offsets = np.column_stack([lons, lats])
                scatter.set_offsets(offsets)
                scatter.set_array(np.array(velocities))
                scatter.set_cmap('gist_rainbow_r')
                scatter.set_clim(0, self.v_max)
            else:
                scatter.set_offsets(np.empty((0, 2)))
            
            avg_v = np.mean([v.velocity for v in self.vehicles.values()]) if self.vehicles else 0
            title.set_text(f'Simulación - Paso {self.time_step} | '
                          f'Vehículos: {len(self.vehicles)} | Llegadas: {self.arrived_vehicles_count}')
            return scatter, title
        
        anim = FuncAnimation(fig, update, init_func=init, frames=steps,
                            interval=interval, blit=False, repeat=False)
        
        plt.colorbar(scatter, ax=ax, label='Velocidad')
        plt.tight_layout()

        if save_as:
            fps = max(1, int(1000 / interval)) if interval else 10
            anim.save(save_as, writer='pillow', fps=fps)
            print(f"Animación guardada en {save_as}")
        
        if show:
            plt.show()
        else:
            plt.close(fig)
        return anim
    
    def plot_statistics(self, output_dir='statistics', show=False):
        """Visualiza y guarda estadísticas de la simulación."""
        from pathlib import Path
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        saved_files = []
        
        # 1. Velocidad promedio
        if self.avg_velocities:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(self.avg_velocities, color='blue', linewidth=1.5)
            ax.set_xlabel('Paso de tiempo')
            ax.set_ylabel('Velocidad promedio')
            ax.set_title('Evolución de la velocidad promedio')
            ax.grid(True, alpha=0.3)
            filepath = output_path / '01_velocidad_promedio.png'
            fig.savefig(filepath)
            saved_files.append(filepath)
            if not show: plt.close(fig)

        # 2. Distribución velocidades (último paso)
        if self.vehicles:
            fig, ax = plt.subplots(figsize=(10, 6))
            velocities = [v.velocity for v in self.vehicles.values()]
            ax.hist(velocities, bins=range(self.v_max + 2), edgecolor='black', color='green')
            ax.set_title(f'Distribución de velocidades (paso {self.time_step})')
            filepath = output_path / '02_distribucion_velocidades.png'
            fig.savefig(filepath)
            saved_files.append(filepath)
            if not show: plt.close(fig)
            
        # 3. Vehículos parados
        if self.stopped_vehicles_count:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(self.stopped_vehicles_count, color='red')
            ax.set_title('Número de vehículos parados')
            filepath = output_path / '03_vehiculos_parados.png'
            fig.savefig(filepath)
            saved_files.append(filepath)
            if not show: plt.close(fig)

        return saved_files
    
    def print_traffic_report(self):
        """Imprime un reporte detallado de las estadísticas de tráfico."""
        print("\n" + "="*60)
        print("REPORTE DE ESTADÍSTICAS DE TRÁFICO")
        print("="*60)
        print(f"\n📊 INFORMACIÓN GENERAL")
        print(f"   Paso de tiempo actual: {self.time_step}")
        print(f"   Total de vehículos activos: {len(self.vehicles)}")
        print(f"   Vehículos que han completado viaje: {self.arrived_vehicles_count}")
        
        if not self.vehicles:
            return
            
        velocities = [v.velocity for v in self.vehicles.values()]
        avg_current_velocity = np.mean(velocities)
        print(f"\n🚗 VELOCIDAD")
        print(f"   Velocidad actual promedio: {avg_current_velocity:.2f} celdas/paso")
        
        stopped_stats = self.get_stopped_vehicles_stats()
        print(f"\n🛑 VEHÍCULOS PARADOS")
        print(f"   Vehículos parados actualmente: {stopped_stats['stopped_vehicles']} "
              f"({stopped_stats['stopped_ratio']*100:.1f}%)")
        
        avg_density = self.get_avg_edge_density()
        print(f"\n🚦 CONGESTIÓN")
        print(f"   Densidad promedio de aristas: {avg_density:.2%}")
        print("\n" + "="*60 + "\n")