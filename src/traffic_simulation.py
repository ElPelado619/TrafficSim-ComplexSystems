"""
Simulación de tráfico usando el modelo de Nagel-Schreckenberg
sobre un grafo de calles de OSM.
"""

import osmnx as ox
import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import defaultdict
import random


class Vehicle:
    """Representa un vehículo en la simulación."""
    
    def __init__(self, vehicle_id, edge, position, velocity=0, v_max=5):
        """
        Inicializa un vehículo.
        
        Args:
            vehicle_id: Identificador único del vehículo
            edge: Tupla (u, v, key) representando la arista en la que está el vehículo
            position: Posición en la arista (0 a longitud de la arista en celdas)
            velocity: Velocidad actual (celdas por paso de tiempo)
            v_max: Velocidad máxima permitida
        """
        self.id = vehicle_id
        self.edge = edge  # (u, v, key)
        self.position = position  # Posición en la arista actual
        self.velocity = velocity
        self.v_max = v_max
        self.color = self._generate_color()
    
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
        
        # Estadísticas
        self.time_step = 0
        self.avg_velocities = []
    
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
    
    def add_vehicle(self, edge=None, position=None, velocity=0):
        """
        Añade un vehículo a la simulación.
        
        Args:
            edge: Tupla (u, v, key). Si es None, se elige aleatoriamente.
            position: Posición inicial. Si es None, se elige aleatoriamente.
            velocity: Velocidad inicial.
        
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
        
        vehicle = Vehicle(vehicle_id, edge, position, velocity, self.v_max)
        self.vehicles[vehicle_id] = vehicle
        self.edge_occupation[edge][position] = vehicle_id
        
        return vehicle_id
    
    def initialize_vehicles(self, density=0.2):
        """
        Inicializa vehículos con una densidad dada.
        
        Args:
            density: Densidad de vehículos (0 a 1), fracción de celdas ocupadas.
        """
        # Contar el número total de celdas
        total_cells = sum(
            data['num_cells'] 
            for u, v, key, data in self.graph.edges(keys=True, data=True)
        )
        
        # Número de vehículos a crear
        num_vehicles = int(total_cells * density)
        
        print(f"Inicializando {num_vehicles} vehículos en {total_cells} celdas (densidad: {density:.2%})")
        
        # Añadir vehículos
        added = 0
        attempts = 0
        max_attempts = num_vehicles * 10  # Evitar bucle infinito
        
        while added < num_vehicles and attempts < max_attempts:
            if self.add_vehicle() is not None:
                added += 1
            attempts += 1
        
        print(f"Vehículos añadidos: {added}")
    
    def _get_distance_to_next_vehicle(self, vehicle):
        """
        Calcula la distancia al siguiente vehículo en la misma dirección.
        
        Returns:
            Distancia en celdas al siguiente vehículo.
        """
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
        current_node = edge[1]
        visited = set([edge])
        
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
    
    def _move_vehicle(self, vehicle):
        """
        Mueve un vehículo a su nueva posición.
        
        Returns:
            True si el movimiento fue exitoso, False si hubo colisión.
        """
        old_edge = vehicle.edge
        old_position = vehicle.position
        new_position = old_position + vehicle.velocity
        num_cells = self.graph[old_edge[0]][old_edge[1]][old_edge[2]]['num_cells']
        
        # Verificar si el vehículo permanece en la misma arista
        if new_position < num_cells:
            # Mover dentro de la misma arista
            del self.edge_occupation[old_edge][old_position]
            
            if new_position in self.edge_occupation[old_edge]:
                # Colisión - revertir
                self.edge_occupation[old_edge][old_position] = vehicle.id
                vehicle.velocity = 0
                return False
            
            self.edge_occupation[old_edge][new_position] = vehicle.id
            vehicle.position = new_position
            return True
        
        else:
            # El vehículo sale de la arista actual
            cells_remaining = new_position - num_cells
            
            # Obtener aristas siguientes
            next_edges = list(self.graph.out_edges(old_edge[1], keys=True))
            
            if not next_edges:
                # Sin salida - el vehículo se detiene al final de la arista
                del self.edge_occupation[old_edge][old_position]
                new_position = num_cells - 1
                self.edge_occupation[old_edge][new_position] = vehicle.id
                vehicle.position = new_position
                vehicle.velocity = 0
                return True
            
            # Elegir una arista siguiente aleatoriamente
            next_edge = random.choice(next_edges)
            next_num_cells = self.graph[next_edge[0]][next_edge[1]][next_edge[2]]['num_cells']
            
            if cells_remaining >= next_num_cells:
                # El vehículo atraviesa múltiples aristas (simplificar: detener al final)
                cells_remaining = next_num_cells - 1
            
            if cells_remaining in self.edge_occupation[next_edge]:
                # Colisión - detener al final de la arista actual
                del self.edge_occupation[old_edge][old_position]
                new_position = num_cells - 1
                self.edge_occupation[old_edge][new_position] = vehicle.id
                vehicle.position = new_position
                vehicle.velocity = 0
                return False
            
            # Mover a la nueva arista
            del self.edge_occupation[old_edge][old_position]
            self.edge_occupation[next_edge][cells_remaining] = vehicle.id
            vehicle.edge = next_edge
            vehicle.position = cells_remaining
            return True
    
    def step(self):
        """Ejecuta un paso de tiempo de la simulación."""
        # Aplicar reglas de Nagel-Schreckenberg
        
        # 1. Aceleración
        for vehicle in self.vehicles.values():
            if vehicle.velocity < vehicle.v_max:
                vehicle.velocity += 1
        
        # 2. Frenado (evitar colisiones)
        for vehicle in self.vehicles.values():
            distance = self._get_distance_to_next_vehicle(vehicle)
            if vehicle.velocity >= distance:
                vehicle.velocity = max(0, distance - 1)
        
        # 3. Aleatorización (desaceleración estocástica)
        for vehicle in self.vehicles.values():
            if vehicle.velocity > 0 and random.random() < self.p_slow:
                vehicle.velocity -= 1
        
        # 4. Movimiento
        for vehicle in self.vehicles.values():
            self._move_vehicle(vehicle)
        
        # Actualizar estadísticas
        self.time_step += 1
        if self.vehicles:
            avg_v = np.mean([v.velocity for v in self.vehicles.values()])
            self.avg_velocities.append(avg_v)
    
    def get_vehicle_positions(self):
        """
        Obtiene las posiciones geográficas de todos los vehículos.
        
        Returns:
            Lista de tuplas (lon, lat, color, velocity)
        """
        positions = []
        
        for vehicle in self.vehicles.values():
            edge = vehicle.edge
            position = vehicle.position
            num_cells = self.graph[edge[0]][edge[1]][edge[2]]['num_cells']
            
            # Interpolar la posición en la arista
            u, v = edge[0], edge[1]
            u_data = self.graph.nodes[u]
            v_data = self.graph.nodes[v]
            
            t = position / num_cells  # Parámetro de interpolación (0 a 1)
            lon = u_data['x'] + t * (v_data['x'] - u_data['x'])
            lat = u_data['y'] + t * (v_data['y'] - u_data['y'])
            
            positions.append((lon, lat, vehicle.color, vehicle.velocity))
        
        return positions
    
    def plot_state(self, ax=None, show_velocity=True):
        """
        Visualiza el estado actual de la simulación.
        
        Args:
            ax: Eje de matplotlib. Si es None, se crea uno nuevo.
            show_velocity: Si True, colorea los vehículos según su velocidad.
        """
        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 12))
        
        # Dibujar el grafo
        ox.plot_graph(self.graph, ax=ax, show=False, close=False, 
                      node_size=0, edge_linewidth=0.5, edge_color='gray')
        
        # Dibujar vehículos
        positions = self.get_vehicle_positions()
        
        if positions:
            lons = [p[0] for p in positions]
            lats = [p[1] for p in positions]
            
            if show_velocity:
                velocities = [p[3] for p in positions]
                scatter = ax.scatter(lons, lats, c=velocities, cmap='RdYlGn', 
                                   s=20, zorder=5, vmin=0, vmax=self.v_max,
                                   edgecolors='black', linewidths=0.5)
                plt.colorbar(scatter, ax=ax, label='Velocidad')
            else:
                colors = [p[2] for p in positions]
                ax.scatter(lons, lats, c=colors, s=20, zorder=5,
                          edgecolors='black', linewidths=0.5)
        
        ax.set_title(f'Simulación de Tráfico - Paso {self.time_step}\n'
                    f'Vehículos: {len(self.vehicles)}, '
                    f'Velocidad promedio: {np.mean([v.velocity for v in self.vehicles.values()]):.2f}')
        
        return ax
    
    def animate(self, steps=100, interval=100, save_as=None):
        """
        Crea una animación de la simulación.
        
        Args:
            steps: Número de pasos de tiempo a simular
            interval: Intervalo entre frames en milisegundos
            save_as: Nombre de archivo para guardar la animación (opcional)
        """
        fig, ax = plt.subplots(figsize=(12, 12))
        
        # Dibujar el grafo una vez
        ox.plot_graph(self.graph, ax=ax, show=False, close=False,
                      node_size=0, edge_linewidth=0.5, edge_color='gray')
        
        scatter = ax.scatter([], [], s=20, zorder=5, edgecolors='black', linewidths=0.5)
        title = ax.set_title('')
        
        def init():
            scatter.set_offsets(np.empty((0, 2)))
            return scatter, title
        
        def update(frame):
            # Ejecutar un paso de simulación
            self.step()
            
            # Obtener posiciones
            positions = self.get_vehicle_positions()
            
            if positions:
                lons = [p[0] for p in positions]
                lats = [p[1] for p in positions]
                velocities = [p[3] for p in positions]
                
                offsets = np.column_stack([lons, lats])
                scatter.set_offsets(offsets)
                scatter.set_array(np.array(velocities))
                scatter.set_cmap('RdYlGn')
                scatter.set_clim(0, self.v_max)
            
            avg_v = np.mean([v.velocity for v in self.vehicles.values()]) if self.vehicles else 0
            title.set_text(f'Simulación de Tráfico - Paso {self.time_step}\n'
                          f'Vehículos: {len(self.vehicles)}, '
                          f'Velocidad promedio: {avg_v:.2f}')
            
            return scatter, title
        
        anim = FuncAnimation(fig, update, init_func=init, frames=steps,
                            interval=interval, blit=True, repeat=False)
        
        if save_as:
            anim.save(save_as, writer='pillow', fps=1000//interval)
            print(f"Animación guardada en {save_as}")
        
        plt.colorbar(scatter, ax=ax, label='Velocidad')
        plt.tight_layout()
        plt.show()
        
        return anim
    
    def plot_statistics(self):
        """Visualiza estadísticas de la simulación."""
        fig, axes = plt.subplots(2, 1, figsize=(10, 8))
        
        # Velocidad promedio a lo largo del tiempo
        axes[0].plot(self.avg_velocities)
        axes[0].set_xlabel('Paso de tiempo')
        axes[0].set_ylabel('Velocidad promedio')
        axes[0].set_title('Evolución de la velocidad promedio')
        axes[0].grid(True, alpha=0.3)
        axes[0].axhline(y=self.v_max, color='r', linestyle='--', label='v_max')
        axes[0].legend()
        
        # Distribución de velocidades en el último paso
        velocities = [v.velocity for v in self.vehicles.values()]
        axes[1].hist(velocities, bins=range(self.v_max + 2), edgecolor='black', alpha=0.7)
        axes[1].set_xlabel('Velocidad')
        axes[1].set_ylabel('Número de vehículos')
        axes[1].set_title(f'Distribución de velocidades (paso {self.time_step})')
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
