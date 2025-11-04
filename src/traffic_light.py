"""
Módulo para la gestión de semáforos en la simulación de tráfico.
"""

from enum import Enum
from typing import Dict, List, Tuple
import json
from pathlib import Path


class LightState(Enum):
    """Estados posibles de un semáforo."""
    RED = "red"
    GREEN = "green"


class TrafficLight:
    """Representa un semáforo en una intersección para una dirección específica."""
    
    def __init__(self, node_id: int, from_node: int = None, green_time: int = 30, red_time: int = 30, initial_state: LightState = LightState.GREEN, phase_offset: int = 0):
        """
        Inicializa un semáforo.
        
        Args:
            node_id: ID del nodo (intersección) donde se ubica el semáforo
            from_node: ID del nodo de origen (dirección de llegada), si se especifica
            green_time: Duración de la luz verde en pasos de tiempo
            red_time: Duración de la luz roja en pasos de tiempo
            initial_state: Estado inicial del semáforo
            phase_offset: Offset de fase inicial (permite sincronizar semáforos)
        """
        self.node_id = node_id
        self.from_node = from_node  # Identifica la dirección de llegada
        self.green_time = green_time
        self.red_time = red_time
        self.state = initial_state
        self.phase_offset = phase_offset
        
        # Contador interno para cambio de estado
        self.timer = phase_offset
        
    @property
    def is_red(self) -> bool:
        """Retorna True si el semáforo está en rojo."""
        return self.state == LightState.RED
    
    @property
    def is_green(self) -> bool:
        """Retorna True si el semáforo está en verde."""
        return self.state == LightState.GREEN
    
    def update(self):
        """Actualiza el estado del semáforo según el tiempo transcurrido."""
        self.timer += 1
        
        if self.state == LightState.GREEN:
            if self.timer >= self.green_time:
                self.state = LightState.RED
                self.timer = 0
        else:  # RED
            if self.timer >= self.red_time:
                self.state = LightState.GREEN
                self.timer = 0
    
    def get_time_to_change(self) -> int:
        """Retorna el tiempo restante hasta el próximo cambio de estado."""
        if self.state == LightState.GREEN:
            return self.green_time - self.timer
        else:
            return self.red_time - self.timer
    
    def to_dict(self) -> dict:
        """Convierte el semáforo a un diccionario serializable."""
        result = {
            'node_id': self.node_id,
            'green_time': self.green_time,
            'red_time': self.red_time,
            'phase_offset': self.phase_offset
        }
        if self.from_node is not None:
            result['from_node'] = self.from_node
        return result
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TrafficLight':
        """Crea un semáforo desde un diccionario."""
        return cls(
            node_id=data['node_id'],
            from_node=data.get('from_node'),
            green_time=data['green_time'],
            red_time=data['red_time'],
            phase_offset=data.get('phase_offset', 0)
        )


class TrafficLightSystem:
    """Sistema que gestiona múltiples semáforos en una red."""
    
    def __init__(self):
        """Inicializa el sistema de semáforos."""
        # Cambio: ahora la clave es (node_id, from_node) para identificar dirección
        # Si from_node es None, se usa solo node_id (compatibilidad con versión anterior)
        self.lights: Dict[Tuple[int, int], TrafficLight] = {}
    
    def add_light(self, traffic_light: TrafficLight):
        """Añade un semáforo al sistema."""
        key = self._get_key(traffic_light.node_id, traffic_light.from_node)
        self.lights[key] = traffic_light
    
    def _get_key(self, node_id: int, from_node: int = None):
        """Genera la clave para el diccionario de semáforos."""
        if from_node is None:
            return (node_id, -1)  # -1 indica sin dirección específica
        return (node_id, from_node)
    
    def remove_light(self, node_id: int, from_node: int = None):
        """Elimina un semáforo del sistema."""
        key = self._get_key(node_id, from_node)
        if key in self.lights:
            del self.lights[key]
    
    def get_light(self, node_id: int, from_node: int = None) -> TrafficLight:
        """Obtiene un semáforo por su node_id y dirección de llegada."""
        key = self._get_key(node_id, from_node)
        return self.lights.get(key)
    
    def update_all(self):
        """Actualiza el estado de todos los semáforos."""
        for light in self.lights.values():
            light.update()
    
    def is_red_at_node(self, node_id: int, from_node: int = None) -> bool:
        """
        Verifica si hay un semáforo en rojo en el nodo dado para una dirección específica.
        
        Args:
            node_id: Nodo donde verificar el semáforo
            from_node: Nodo de origen (dirección de llegada)
        
        Returns:
            True si el semáforo está en rojo, False en caso contrario
        """
        light = self.get_light(node_id, from_node)
        if light is None:
            return False
        return light.is_red
    
    def get_all_node_ids(self) -> List[int]:
        """Retorna lista de todos los nodos únicos con semáforos."""
        unique_nodes = set()
        for (node_id, _) in self.lights.keys():
            unique_nodes.add(node_id)
        return list(unique_nodes)
    
    def get_lights_at_node(self, node_id: int) -> List[TrafficLight]:
        """Retorna todos los semáforos en un nodo dado."""
        return [light for (nid, _), light in self.lights.items() if nid == node_id]
    
    def has_traffic_light_at_node(self, node_id: int) -> bool:
        """Verifica si existe al menos un semáforo en el nodo dado."""
        return any((nid, _) for (nid, _) in self.lights.keys() if nid == node_id)
    
    def save_to_file(self, filepath: Path):
        """Guarda la configuración de semáforos a un archivo JSON."""
        data = {
            'traffic_lights': [light.to_dict() for light in self.lights.values()]
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    @classmethod
    def load_from_file(cls, filepath: Path) -> 'TrafficLightSystem':
        """Carga la configuración de semáforos desde un archivo JSON."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        system = cls()
        for light_data in data.get('traffic_lights', []):
            light = TrafficLight.from_dict(light_data)
            system.add_light(light)
        
        return system
    
    def __len__(self):
        """Retorna el número de semáforos en el sistema."""
        return len(self.lights)
    
    def __repr__(self):
        return f"TrafficLightSystem(lights={len(self.lights)})"
