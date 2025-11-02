# Sistema de Semáforos con Optimización Genética

Este módulo implementa un sistema de semáforos inteligentes para la simulación de tráfico, optimizados mediante un algoritmo genético.

## Descripción General

El sistema de semáforos consta de tres componentes principales:

1. **`src/traffic_light.py`**: Clases base para la gestión de semáforos
2. **`generador_semaforos.py`**: Algoritmo genético para optimización
3. **Integración en `TrafficSimulation`**: Los vehículos respetan los semáforos automáticamente

## Componentes

### TrafficLight

Representa un semáforo individual con:
- **Estados**: ROJO o VERDE
- **Tiempos configurables**: duración de luz verde y roja
- **Phase offset**: desfase inicial para sincronización
- **Actualización automática**: cambia de estado según el tiempo transcurrido

### TrafficLightSystem

Sistema que gestiona múltiples semáforos:
- Almacena todos los semáforos de la red
- Actualiza todos los estados simultáneamente
- Consulta rápida por nodo
- Serialización a/desde JSON

### GeneticOptimizer

Algoritmo genético que optimiza los tiempos de semáforos:

**Cromosoma**: Para cada intersección importante:
- `green_time`: duración de luz verde (15-60 pasos)
- `red_time`: duración de luz roja (15-60 pasos)
- `phase_offset`: desfase inicial (0 a ciclo completo)

**Función de fitness**:
```
fitness = velocidad_promedio - 0.3 * desviación_estándar
```
Se maximiza la velocidad promedio mientras se minimiza la varianza (fluidez).

**Operadores genéticos**:
- **Selección**: Torneo (tamaño 3)
- **Crossover**: Uniforme
- **Mutación**: Ajuste de ±5 en tiempos, o cambio aleatorio en offset
- **Elitismo**: Preserva los mejores individuos

## Uso

### 1. Optimización de Semáforos

```bash
python generador_semaforos.py \
  --graph data/microcentro.graphml \
  --zones data/O-D-maps/microcentro_zones.json \
  --od data/O-D-maps/microcentro_zones_matrix.json \
  --output data/traffic_lights.json \
  --population 50 \
  --generations 30 \
  --scale 0.01
```

**Parámetros importantes**:
- `--population`: Mayor = mejor exploración, pero más lento (recomendado: 30-50)
- `--generations`: Mayor = mejor convergencia (recomendado: 20-40)
- `--simulation-steps`: Pasos para evaluar cada individuo (recomendado: 500)
- `--min-degree`: Grado mínimo de nodo para semáforo (default: 3)

### 2. Simulación con Semáforos

#### Opción A: Script integrado

```bash
python examples/run_with_traffic_lights.py \
  --zones data/O-D-maps/microcentro_zones.json \
  --od data/O-D-maps/microcentro_zones_matrix.json \
  --optimize-lights \
  --save-lights data/traffic_lights.json \
  --steps 1000 \
  --scale 0.01
```

#### Opción B: Cargar semáforos pre-optimizados

```bash
python examples/run_with_traffic_lights.py \
  --zones data/O-D-maps/microcentro_zones.json \
  --od data/O-D-maps/microcentro_zones_matrix.json \
  --lights-file data/traffic_lights.json \
  --steps 1000 \
  --scale 0.01
```

#### Opción C: Programático

```python
from src.traffic_simulation import TrafficSimulation
from src.traffic_light import TrafficLightSystem

# Crear simulación
sim = TrafficSimulation("data/microcentro.graphml")

# Cargar semáforos
traffic_lights = TrafficLightSystem.load_from_file("data/traffic_lights.json")
sim.traffic_lights = traffic_lights

# Generar vehículos y simular
sim.spawn_from_od_matrix(zones, od_matrix, scale=0.01)

for _ in range(1000):
    sim.step()
```

## Funcionamiento Interno

### Comportamiento de los Vehículos

Los vehículos respetan los semáforos mediante la función `_get_distance_to_next_vehicle()`:

```python
# Si el semáforo está en rojo en el nodo siguiente
if self.traffic_lights.is_red_at_node(current_node):
    # La distancia efectiva es hasta el final de la arista
    return distance
```

Los vehículos:
1. **Detectan** semáforos en rojo al aproximarse a intersecciones
2. **Frenan** gradualmente según la distancia al semáforo
3. **Se detienen** al final de la arista si el semáforo está en rojo
4. **Reanudan** cuando el semáforo cambia a verde

### Algoritmo Genético - Detalles

**Inicialización**:
```python
# Identificar intersecciones (nodos con grado >= min_degree)
candidate_nodes = [n for n in graph.nodes() 
                   if graph.degree(n) >= min_degree]

# Crear población inicial aleatoria
population = [TrafficLightChromosome(candidate_nodes) 
              for _ in range(population_size)]
```

**Evaluación**:
```python
# Crear simulación con el cromosoma
sim = TrafficSimulation(...)
sim.traffic_lights = chromosome.to_traffic_light_system()

# Generar tráfico y simular
sim.spawn_from_od_matrix(zones, od_matrix, scale)
for _ in range(simulation_steps):
    sim.step()

# Calcular fitness
fitness = mean_velocity - 0.3 * std_velocity
```

**Evolución**:
```python
# Preservar elite
new_population = population[:elite_size]

# Generar resto
while len(new_population) < population_size:
    parent1, parent2 = tournament_selection(population)
    child = crossover(parent1, parent2)
    mutate(child, mutation_rate)
    new_population.append(child)
```

## Visualización

Los semáforos se muestran en la simulación como:
- **Círculos verdes**: luz verde (paso permitido)
- **Círculos rojos**: luz roja (stop)

Las animaciones muestran:
- Cambio dinámico de estados de semáforos
- Vehículos deteniéndose y arrancando
- Colores de vehículos según velocidad

## Formato de Archivo JSON

```json
{
  "traffic_lights": [
    {
      "node_id": 287040660,
      "green_time": 35,
      "red_time": 28,
      "phase_offset": 12
    },
    ...
  ]
}
```

## Métricas de Performance

El algoritmo genético optimiza para:

1. **Velocidad promedio alta**: Los vehículos se mueven rápido en general
2. **Baja varianza**: Flujo uniforme sin paradas/arranques bruscos
3. **Throughput**: Máximo número de vehículos procesados

## Tips de Optimización

### Para redes pequeñas (< 50 nodos):
```bash
--population 20 --generations 15 --simulation-steps 300
```

### Para redes medianas (50-200 nodos):
```bash
--population 30 --generations 25 --simulation-steps 500
```

### Para redes grandes (> 200 nodos):
```bash
--population 50 --generations 40 --simulation-steps 500
```

### Ajuste del scale:
- **scale=0.001**: Tráfico muy ligero (debugging)
- **scale=0.01**: Tráfico moderado (recomendado)
- **scale=0.05**: Tráfico denso
- **scale=0.1**: Tráfico muy denso (congestión)

## Limitaciones Conocidas

1. **Tiempo de optimización**: Puede tardar 10-30 minutos para redes grandes
2. **Memoria**: Cada evaluación crea una simulación completa
3. **Convergencia**: No garantiza el óptimo global
4. **Sincronización**: Los semáforos no coordinan "olas verdes" explícitamente

## Mejoras Futuras

- [ ] Algoritmos de sincronización (olas verdes)
- [ ] Semáforos adaptativos según demanda en tiempo real
- [ ] Optimización multi-objetivo (velocidad + emisiones + equidad)
- [ ] Paralelización del algoritmo genético
- [ ] Semáforos con fase amarilla
- [ ] Prioridad para vehículos de emergencia

## Referencias

- Modelo Nagel-Schreckenberg: https://en.wikipedia.org/wiki/Nagel–Schreckenberg_model
- Algoritmos genéticos: Holland, J. H. (1992). "Adaptation in Natural and Artificial Systems"
- Traffic signal optimization: Gao, K. et al. (2019). "A survey on traffic signal control methods"
