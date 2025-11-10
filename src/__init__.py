"""
Paquete de simulación de tráfico usando el modelo de Nagel-Schreckenberg.
"""

from .traffic_simulation import TrafficSimulation, Vehicle
from .parallel_simulation import run_simulation_with_params, run_simulations_in_parallel

__version__ = "1.0.0"
__all__ = [
	"TrafficSimulation",
	"Vehicle",
	"run_simulation_with_params",
	"run_simulations_in_parallel",
]
