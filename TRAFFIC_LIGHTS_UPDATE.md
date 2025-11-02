# Actualización: Sistema de Semáforos con Optimización Genética

## ✨ Nuevo en esta versión

Se ha implementado un **sistema completo de semáforos** con optimización mediante **algoritmo genético** para mejorar el flujo de tráfico en las simulaciones.

## 🎯 Características Principales

### 1. Semáforos Inteligentes
- Estados ROJO/VERDE con tiempos configurables
- Sincronización mediante phase offset
- Los vehículos detectan y respetan los semáforos automáticamente

### 2. Optimización con Algoritmo Genético
- Identifica intersecciones clave automáticamente
- Optimiza tiempos de verde, rojo y sincronización
- Maximiza velocidad promedio y fluidez del tráfico
- Configuración mediante población, generaciones y mutación

### 3. Visualización Mejorada
- Semáforos visibles en rojo/verde en el mapa
- Animaciones con cambio dinámico de estados
- Estadísticas de performance

## 📦 Archivos Nuevos

```
src/
  traffic_light.py           # Clases para gestión de semáforos
generador_semaforos.py       # Algoritmo genético para optimización
examples/
  run_with_traffic_lights.py # Script integrado completo
docs/
  TRAFFIC_LIGHTS.md          # Documentación detallada
  ZONES_WORKFLOW.md          # Actualizado con flujo de semáforos
```

## 🚀 Inicio Rápido

### Paso 1: Instalar dependencias

```bash
pip install -r requirements.txt
```

### Paso 2: Generar zonas y matriz O-D

```bash
# Crear zonas (interfaz gráfica)
python run.py zones

# Generar matriz O-D
python generador_od.py \
  --zone-file data/O-D-maps/microcentro_zones.json \
  --output data/O-D-maps/microcentro_zones_matrix.json \
  --beta 0.015
```

### Paso 3: Optimizar semáforos

```bash
python generador_semaforos.py \
  --zones data/O-D-maps/microcentro_zones.json \
  --od data/O-D-maps/microcentro_zones_matrix.json \
  --output data/traffic_lights.json \
  --population 30 \
  --generations 20
```

⏱️ **Tiempo estimado**: 5-15 minutos dependiendo del tamaño de la red

### Paso 4: Ejecutar simulación

```bash
python examples/run_with_traffic_lights.py \
  --zones data/O-D-maps/microcentro_zones.json \
  --od data/O-D-maps/microcentro_zones_matrix.json \
  --lights-file data/traffic_lights.json \
  --animation-gif data/runs/microcentro_anim.gif \
  --scale 0.01 \
  --steps 1000
```

## 🎬 Flujo Completo en un Solo Comando

```bash
python examples/run_with_traffic_lights.py \
  --zones data/O-D-maps/microcentro_zones.json \
  --od data/O-D-maps/microcentro_zones_matrix.json \
  --optimize-lights \
  --save-lights data/traffic_lights.json \
  --animation-gif data/runs/microcentro_anim.gif \
  --scale 0.01 \
  --steps 1000 \
  --population 20 \
  --generations 15
```

Esto ejecuta:
1. ✅ Carga de zonas y matriz O-D
2. 🧬 Optimización de semáforos
3. 💾 Guardado de configuración
4. 🚗 Simulación con semáforos
5. 🎥 Generación de animación

## 📊 Ejemplo de Uso Programático

```python
from src.traffic_simulation import TrafficSimulation
from src.traffic_light import TrafficLightSystem
import generador_od

# Cargar datos
zones, _, _, _ = generador_od.load_zone_file("data/O-D-maps/microcentro_zones.json")
with open("data/O-D-maps/microcentro_zones_matrix.json") as f:
    od_matrix = json.load(f)

# Crear simulación
sim = TrafficSimulation("data/microcentro.graphml")

# Cargar semáforos optimizados
traffic_lights = TrafficLightSystem.load_from_file("data/traffic_lights.json")
sim.traffic_lights = traffic_lights

# Generar vehículos
sim.spawn_from_od_matrix(zones, od_matrix, scale=0.01)

# Simular
for step in range(1000):
    sim.step()

# Visualizar
sim.plot_state(show=True)
sim.plot_statistics(show=True)
```

## 🔧 Parámetros del Algoritmo Genético

| Parámetro | Descripción | Recomendado | Rango |
|-----------|-------------|-------------|-------|
| `--population` | Tamaño de la población | 30-50 | 10-100 |
| `--generations` | Número de generaciones | 20-30 | 10-50 |
| `--mutation-rate` | Tasa de mutación | 0.1 | 0.05-0.3 |
| `--elite-size` | Individuos elite | 5 | 2-10 |
| `--simulation-steps` | Pasos de evaluación | 500 | 300-1000 |
| `--min-degree` | Grado mínimo de nodo | 3 | 2-4 |

## 📈 Métricas de Optimización

El algoritmo genético optimiza:
- **Velocidad promedio**: Vehículos más rápidos
- **Fluidez**: Menor varianza en velocidades
- **Throughput**: Máximo flujo de vehículos

Función de fitness:
```
fitness = velocidad_promedio - 0.3 × desviación_estándar
```

## 🎨 Visualización

En las animaciones y gráficos:
- 🟢 **Círculos verdes**: Semáforo en verde (paso libre)
- 🔴 **Círculos rojos**: Semáforo en rojo (stop)
- 🚗 **Vehículos**: Coloreados por velocidad
  - Verde: rápido
  - Amarillo: moderado
  - Rojo: lento/detenido

## 📚 Documentación

- **[ZONES_WORKFLOW.md](docs/ZONES_WORKFLOW.md)**: Flujo completo actualizado
- **[TRAFFIC_LIGHTS.md](docs/TRAFFIC_LIGHTS.md)**: Documentación detallada del sistema de semáforos
- **[TECHNICAL_NOTES.md](docs/TECHNICAL_NOTES.md)**: Notas técnicas del modelo

## 🐛 Solución de Problemas

### El algoritmo genético es muy lento
- Reduce `--population` a 20-30
- Reduce `--generations` a 15-20
- Reduce `--simulation-steps` a 300-400

### No se generan vehículos
- Verifica que la matriz O-D tenga demanda > 0
- Aumenta `--scale` (ej: 0.02 o 0.05)
- Verifica que las zonas tengan nodos válidos

### Los semáforos no se muestran
- Verifica que el archivo JSON tenga el formato correcto
- Asegúrate de cargar los semáforos antes de iniciar la simulación
- Verifica que los node_ids existan en el grafo

## 💡 Tips

1. **Prueba rápida**: Usa población=10, generaciones=5 para testing
2. **Mejor resultado**: Usa población=50, generaciones=40 (más lento)
3. **Balance**: Usa población=30, generaciones=20 (recomendado)
4. **Tráfico ligero**: scale=0.01
5. **Tráfico denso**: scale=0.05

## 🔄 Compatibilidad

El sistema es **totalmente retrocompatible**:
- Scripts antiguos siguen funcionando sin cambios
- Los semáforos son opcionales
- Sin semáforos, la simulación funciona como antes

## 📝 Ejemplo de Archivo de Semáforos

`data/traffic_lights.json`:
```json
{
  "traffic_lights": [
    {
      "node_id": 287040660,
      "green_time": 35,
      "red_time": 28,
      "phase_offset": 12
    },
    {
      "node_id": 287042850,
      "green_time": 42,
      "red_time": 25,
      "phase_offset": 8
    }
  ]
}
```

## 🤝 Contribuir

Para mejorar el sistema de semáforos:
1. Algoritmos de sincronización más sofisticados
2. Semáforos adaptativos en tiempo real
3. Optimización multi-objetivo
4. Paralelización del algoritmo genético

---

**¡Disfruta de las simulaciones con semáforos inteligentes! 🚦🚗**
