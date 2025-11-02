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
    """Representa un semáforo en una intersección."""
    
    def __init__(self, node_id: int, green_time: int = 30, red_time: int = 30, initial_state: LightState = LightState.GREEN, phase_offset: int = 0):
        """
        Inicializa un semáforo.
        
        Args:
            node_id: ID del nodo (intersección) donde se ubica el semáforo
            green_time: Duración de la luz verde en pasos de tiempo
            red_time: Duración de la luz roja en pasos de tiempo
            initial_state: Estado inicial del semáforo
            phase_offset: Offset de fase inicial (permite sincronizar semáforos)
        """
        self.node_id = node_id
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
        return {
            'node_id': self.node_id,
            'green_time': self.green_time,
            'red_time': self.red_time,
            'phase_offset': self.phase_offset
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TrafficLight':
        """Crea un semáforo desde un diccionario."""
        return cls(
            node_id=data['node_id'],
            green_time=data['green_time'],
            red_time=data['red_time'],
            phase_offset=data.get('phase_offset', 0)
        )


class TrafficLightSystem:
    """Sistema que gestiona múltiples semáforos en una red."""
    
    def __init__(self):
        """Inicializa el sistema de semáforos."""
        self.lights: Dict[int, TrafficLight] = {}
    
    def add_light(self, traffic_light: TrafficLight):
        """Añade un semáforo al sistema."""
        self.lights[traffic_light.node_id] = traffic_light
    
    def remove_light(self, node_id: int):
        """Elimina un semáforo del sistema."""
        if node_id in self.lights:
            del self.lights[node_id]
    
    def get_light(self, node_id: int) -> TrafficLight:
        """Obtiene un semáforo por su node_id."""
        return self.lights.get(node_id)
    
    def update_all(self):
        """Actualiza el estado de todos los semáforos."""
        for light in self.lights.values():
            light.update()
    
    def is_red_at_node(self, node_id: int) -> bool:
        """Verifica si hay un semáforo en rojo en el nodo dado."""
        light = self.lights.get(node_id)
        if light is None:
            return False
        return light.is_red
    
    def get_all_node_ids(self) -> List[int]:
        """Retorna lista de todos los nodos con semáforos."""
        return list(self.lights.keys())
    
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
