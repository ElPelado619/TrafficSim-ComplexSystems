# Zona a Simulación: Guía Rápida

Sigue estos pasos para definir zonas sobre el microcentro, generar la matriz O-D, optimizar semáforos y ejecutar una simulación que use esa demanda.

## 1. Abrir el editor de zonas

```bash
python run.py zones
```

Acciones dentro del editor:
- Dibuja un polígono con clic izquierdo (doble clic para cerrar).
- Completa los diálogos para nombre, producción (P) y atracción (A).
- Cada zona se guarda en `data/O-D-maps/microcentro_zones.json`.
- Atajos: `s` (guardar), `u` (deshacer), `d` (borrar por nombre), `c` (limpiar todo), `q` (salir).

## 2. Generar la matriz O-D

```bash
python generador_od.py \
  --zone-file data/O-D-maps/microcentro_zones.json \
  --output data/O-D-maps/microcentro_zones_matrix.json \
  --beta 0.015
```

Ajusta `--beta` (o usa `--gamma --friction power`) según necesites. El resultado es un JSON con la demanda entre zonas.

## 3. Optimizar semáforos (NUEVO)

Este paso es **opcional** pero recomendado. Utiliza un algoritmo genético para optimizar los tiempos de los semáforos basándose en el flujo de tráfico de la matriz O-D.

```bash
python generador_semaforos.py \
  --zones data/O-D-maps/microcentro_zones.json \
  --od data/O-D-maps/microcentro_zones_matrix.json \
  --output data/traffic_lights.json \
  --population 30 \
  --generations 20 \
  --scale 0.01
```

Parámetros del algoritmo genético:
- `--population`: Tamaño de la población (default: 50)
- `--generations`: Número de generaciones a evolucionar (default: 30)
- `--mutation-rate`: Tasa de mutación 0-1 (default: 0.1)
- `--elite-size`: Individuos elite a preservar (default: 5)
- `--simulation-steps`: Pasos de simulación para evaluar fitness (default: 500)
- `--scale`: Factor de escala para la demanda O-D (default: 0.01)
- `--min-degree`: Grado mínimo de nodo para colocar semáforo (default: 3)

El algoritmo:
1. Identifica intersecciones importantes (nodos con alto grado de conectividad)
2. Genera poblaciones con diferentes configuraciones de tiempos de semáforo
3. Evalúa cada configuración ejecutando una simulación corta
4. Selecciona las mejores configuraciones usando torneo
5. Aplica crossover y mutación para crear nuevas generaciones
6. Repite hasta converger a una solución óptima

## 4. Ejecutar la simulación con semáforos

### Opción A: Script integrado (recomendado)

```bash
python examples/run_with_traffic_lights.py \
  --zones data/O-D-maps/microcentro_zones.json \
  --od data/O-D-maps/microcentro_zones_matrix.json \
  --optimize-lights \
  --save-lights data/traffic_lights.json \
  --save-prefix data/runs/microcentro \
  --animation-gif data/runs/microcentro_anim.gif \
  --scale 0.01 \
  --steps 1000 \
  --no-show
```

Este script ejecuta todo el flujo:
1. Carga zonas y matriz O-D
2. Optimiza semáforos (si se usa `--optimize-lights`) o carga configuración existente (`--lights-file`)
3. Ejecuta la simulación con los semáforos
4. Genera visualizaciones y animaciones

### Opción B: Usar semáforos pre-optimizados

Si ya optimizaste los semáforos en el paso 3:

```bash
python examples/run_with_traffic_lights.py \
  --zones data/O-D-maps/microcentro_zones.json \
  --od data/O-D-maps/microcentro_zones_matrix.json \
  --lights-file data/traffic_lights.json \
  --save-prefix data/runs/microcentro \
  --animation-gif data/runs/microcentro_anim.gif \
  --scale 0.01 \
  --steps 1000 \
  --no-show
```

### Opción C: Actualizar script existente

Para usar semáforos en `examples/run_microcentro_od.py`, modifica el script:

```python
from src.traffic_light import TrafficLightSystem

# Después de crear la simulación
sim = TrafficSimulation(...)

# Cargar semáforos
traffic_lights = TrafficLightSystem.load_from_file("data/traffic_lights.json")
sim.traffic_lights = traffic_lights
```

Parámetros útiles:
- `--scale`: convierte demanda en número de vehículos (ej. `0.01`).
- `--steps`: pasos de simulación.
- `--cell-length`, `--v-max`, `--p-slow`: parámetros del modelo Nagel-Schreckenberg.
- `--population`, `--generations`: parámetros del algoritmo genético (solo para optimización).

## 5. Funcionamiento de los semáforos

Los semáforos implementados:
- Se colocan en intersecciones importantes (nodos con ≥3 conexiones)
- Alternan entre estados ROJO y VERDE con tiempos configurables
- Los vehículos detectan semáforos en rojo y frenan automáticamente
- El algoritmo genético optimiza:
  - `green_time`: duración de luz verde
  - `red_time`: duración de luz roja
  - `phase_offset`: desfase para sincronización entre semáforos

En la visualización:
- **Círculos verdes**: semáforos en verde (vehículos pueden pasar)
- **Círculos rojos**: semáforos en rojo (vehículos deben detenerse)
- Los vehículos se colorean según su velocidad (verde=rápido, amarillo=medio, rojo=lento)

## 6. Integrar nuevas zonas en otros scripts
- Usa `generador_od.load_zone_file(...)` para cargar zonas y factores.
- La matriz O-D es un dict anidado (`origen -> destino -> demanda`).
- `TrafficSimulation.spawn_from_od_matrix(...)` crea vehículos basados en la matriz.
- `TrafficSimulation.load_traffic_lights(...)` carga semáforos desde archivo JSON.
- `TrafficLightSystem.load_from_file(...)` carga configuración de semáforos.

## 7. Consejos rápidos
- Producción = viajes que salen de la zona (orígenes).
- Atracción = viajes que llegan a la zona (destinos).
- Las zonas pueden editarse en cualquier momento desde el mismo editor; cada cambio se guarda automáticamente.
- Para versiones alternativas, guarda archivos con otros nombres dentro de `data/O-D-maps/` y referencia esos paths en los comandos anteriores.
- La optimización de semáforos puede tardar varios minutos dependiendo del tamaño de la población y generaciones.
- Usa valores más bajos de `--population` y `--generations` para pruebas rápidas.
- El parámetro `--scale` controla cuántos vehículos se generan; valores muy altos pueden causar congestión extrema.
- Los semáforos optimizados mejoran el flujo general del tráfico al reducir congestión en intersecciones clave.
