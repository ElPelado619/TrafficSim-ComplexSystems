# Actualización del Sistema de Semáforos: Direcciones Independientes

## Problema Resuelto

Anteriormente, el sistema de semáforos asignaba un único semáforo por intersección (nodo), lo que significaba que todas las calles que se cruzaban en ese punto compartían el mismo estado (verde o rojo). Esto no reflejaba la realidad del tráfico, donde calles perpendiculares deben tener semáforos con fases opuestas.

## Solución Implementada

El sistema ahora gestiona **semáforos por dirección de llegada** en cada intersección:

### 1. Identificación por Dirección

Cada semáforo se identifica por:
- `node_id`: El nodo de la intersección
- `from_node`: El nodo de origen (dirección de llegada)

Esto permite múltiples semáforos en la misma intersección, uno para cada dirección.

### 2. Coordinación de Fases

El algoritmo genético detecta automáticamente calles perpendiculares y asigna fases opuestas:

- **Grupo 0** (ej. Este-Oeste): `phase_offset = 0` → Empieza en verde
- **Grupo 1** (ej. Norte-Sur): `phase_offset = green_time` → Empieza en rojo

Cuando el Grupo 0 está en verde, el Grupo 1 está en rojo, y viceversa.

### 3. Detección de Direcciones Perpendiculares

El sistema calcula el ángulo de llegada de cada calle usando las coordenadas geográficas:

```python
# Calcula ángulo de llegada
dx = node_x - from_x
dy = node_y - from_y
angle = np.arctan2(dy, dx)

# Clasifica en grupos:
# - Grupo 0: Este-Oeste (ángulos 315-45° o 135-225°)
# - Grupo 1: Norte-Sur (ángulos 45-135° o 225-315°)
```

## Cambios en el Código

### `src/traffic_light.py`

1. **`TrafficLight`**: Añadido parámetro `from_node`
   ```python
   def __init__(self, node_id: int, from_node: int = None, ...)
   ```

2. **`TrafficLightSystem`**: 
   - Clave del diccionario: `(node_id, from_node)` en lugar de solo `node_id`
   - Nuevo método: `get_lights_at_node(node_id)` para obtener todos los semáforos de un nodo
   - Actualizado: `is_red_at_node(node_id, from_node)` para verificar dirección específica

### `src/traffic_simulation.py`

1. **Verificación de semáforos**: Actualizado para pasar `from_node`
   ```python
   # Antes
   if self.traffic_lights.is_red_at_node(current_node):
   
   # Ahora
   from_node = edge[0]
   if self.traffic_lights.is_red_at_node(current_node, from_node):
   ```

2. **Visualización**: Los semáforos se distribuyen alrededor de cada intersección

### `generador_semaforos.py`

1. **`TrafficLightChromosome`**: 
   - Recibe el grafo para analizar geometría
   - Genes identificados por `(node_id, from_node)`
   - Método `_group_perpendicular_edges()` para detectar calles perpendiculares

2. **Coordinación automática**: El algoritmo genético mantiene consistencia en cada intersección

## Resultados

### Ejemplo de Intersección

```
Nodo: 247486278 (3 direcciones)

Dirección 1 (desde 1840278950):
  - green_time: 17, phase_offset: 0
  - Secuencia: 🟢🟢🟢...🔴🔴🔴...

Direcciones 2 y 3 (desde 12161223128, 12161223129):
  - green_time: 17, phase_offset: 17
  - Secuencia: 🔴🔴🔴...🟢🟢🟢...
```

**Coordinación verificada**: 94% del tiempo con estados opuestos

### Estadísticas del Sistema

- **Nodos con semáforos**: 562
- **Total de semáforos**: 1133
- **Promedio**: ~2 semáforos por intersección
- **Nodos con múltiples direcciones**: 480 (85%)

## Uso

### Generar semáforos optimizados

```bash
python generador_semaforos.py \
    --graph data/microcentro.graphml \
    --zones data/O-D-maps/microcentro_zones.json \
    --od data/O-D-maps/microcentro_zones_matrix.json \
    --output data/traffic_lights.json \
    --population 30 \
    --generations 20
```

### Ejecutar simulación

```bash
python examples/run_with_traffic_lights.py \
    --zones data/O-D-maps/microcentro_zones.json \
    --od data/O-D-maps/microcentro_zones_matrix.json \
    --lights-file data/traffic_lights.json \
    --steps 1000 \
    --scale 0.08
```

### Verificar coordinación

```bash
python demo_perpendicular_lights.py
```

## Compatibilidad

El sistema es **retrocompatible**: semáforos sin `from_node` siguen funcionando (se asigna `from_node = -1` internamente).

## Mejoras Futuras

1. **Semáforos vehiculares y peatonales**: Distinguir entre diferentes tipos
2. **Detección de giros**: Semáforos específicos para giros a la izquierda/derecha
3. **Optimización multi-objetivo**: Balance entre flujo vehicular y peatonal
4. **Adaptación dinámica**: Ajustar tiempos según demanda en tiempo real
