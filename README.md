# Simulación de Tráfico - Modelo de Nagel-Schreckenberg

Este proyecto implementa el **autómata celular de Nagel-Schreckenberg** para simular tráfico vehicular sobre un grafo de calles reales obtenido de OpenStreetMap (OSM).

## 📋 Descripción

El modelo de Nagel-Schreckenberg es un autómata celular estocástico que simula el flujo de tráfico en una carretera. En cada paso de tiempo, cada vehículo sigue cuatro reglas simples:

1. **Aceleración**: Si `v < v_max`, aumentar velocidad en 1
2. **Frenado**: Si la distancia al vehículo de adelante es `d`, ajustar `v = min(v, d-1)`
3. **Aleatorización**: Con probabilidad `p`, reducir `v` en 1 (si `v > 0`)
4. **Movimiento**: Avanzar `v` celdas

## 🚗 Características

- ✅ Carga de mapas desde archivos OSM o GraphML
- ✅ Discretización automática de calles en celdas
- ✅ Implementación completa del modelo de Nagel-Schreckenberg
- ✅ Inicialización de vehículos con densidad configurable
- ✅ Visualización estática y animada sobre el mapa
- ✅ Estadísticas de velocidad y flujo de tráfico
- ✅ Soporte para parámetros configurables

## 📦 Requisitos e Instalación

```bash
pip install -r requirements.txt
```

📖 **Para instrucciones detalladas de instalación**, consulta **[INSTALL.md](INSTALL.md)**.

### Dependencias principales:
- `osmnx`: Para cargar y manipular grafos de calles
- `networkx`: Para trabajar con grafos
- `numpy`: Para cálculos numéricos
- `matplotlib`: Para visualización
- `pillow`: Para guardar animaciones (opcional)

## 🚀 Uso Rápido

### Script de ayuda (recomendado):

```bash
python run.py help          # Ver todos los comandos disponibles
python run.py test          # Verificar instalación
python run.py examples      # Ejecutar ejemplos básicos
python run.py advanced      # Ejecutar análisis avanzados
```

### O directamente:

#### Verificar instalación:

```bash
python tests/test_installation.py
```

#### Ejecución del script de ejemplos básicos:

```bash
python examples/run_simulation.py
```

El script te presentará un menú interactivo con 5 ejemplos diferentes:

1. **Simulación básica**: Ejecuta una simulación con densidad media y muestra el estado final
2. **Animación**: Crea una animación GIF de la simulación
3. **Comparación de densidades**: Compara 3 densidades diferentes (10%, 30%, 50%)
4. **Estudio de parámetros**: Analiza el efecto de la probabilidad de desaceleración
5. **Escenario personalizado**: Simulación con parámetros ajustados

### Ejemplos avanzados (análisis científico):

```bash
python examples/advanced_examples.py
```

Incluye análisis avanzados:
- **Diagrama fundamental**: Relación flujo-densidad-velocidad
- **Transición de fase**: Entre flujo libre y congestión
- **Efecto de estocasticidad**: Impacto de p_slow en atascos
- **Tiempo de relajación**: Convergencia al estado estacionario
- **Diagrama espacio-temporal**: Trayectorias de vehículos

### Simulaciones en paralelo

```bash
python examples/run_parallel_simulations.py
```

Lanza un barrido de parámetros en paralelo utilizando ``multiprocessing.Pool``.
Internamente invoca ``src.parallel_simulation.run_simulation_with_params`` y
resume las métricas de cada ejecución.

### Uso programático:

```python
from src.traffic_simulation import TrafficSimulation

# Crear simulación
sim = TrafficSimulation(
    graph_file='data/map_reduced.osm',
    cell_length=7.5,  # metros por celda
    v_max=5,          # velocidad máxima
    p_slow=0.3        # probabilidad de desaceleración
)

# Inicializar vehículos (densidad 20%)
sim.initialize_vehicles(density=0.2)

# Ejecutar simulación
for _ in range(100):
    sim.step()

# Visualizar
sim.plot_state()
sim.plot_statistics()

# Crear animación
sim.animate(steps=100, interval=100, save_as='traffic.gif')
```

Para estudios masivos de parámetros puedes utilizar las utilidades paralelas:

```python
from src.parallel_simulation import run_simulation_with_params, run_simulations_in_parallel

scenarios = [
    {"label": "d0.15_p0.2", "graph_file": "data/map_reduced.osm", "density": 0.15, "p_slow": 0.2, "steps": 80},
    {"label": "d0.30_p0.4", "graph_file": "data/map_reduced.osm", "density": 0.30, "p_slow": 0.4, "steps": 80},
]

results = run_simulations_in_parallel(scenarios)
for result in results:
    print(result["label"], result["metrics"]["final_avg_velocity"])
```

### Optimización de semáforos con editor interactivo:

```bash
# 1. Editar y optimizar en un solo comando
python generador_semaforos.py --edit \
    --graph data/microcentro.graphml \
    --zones data/O-D-maps/microcentro_zones.json \
    --od data/O-D-maps/microcentro_zones_matrix.json

# El comando anterior:
# - Abre un editor visual donde puedes hacer click en nodos para incluir/excluir semáforos
# - Al cerrar el editor, automáticamente optimiza los tiempos de semáforo
# - Guarda la configuración optimizada en data/traffic_lights.json

# 2. O ejecutar el editor por separado
python tools/traffic_light_editor.py --graph data/microcentro.graphml

# Controles del editor:
# - Click izquierdo: Toggle incluir/excluir nodo
# - [s]: Guardar cambios
# - [r]: Reset (incluir todos)
# - [q]: Salir
```

📖 **Ver guía completa**: [Editor de Semáforos](docs/TRAFFIC_LIGHT_EDITOR.md)

## 🔧 Parámetros del Modelo

### `TrafficSimulation`

- **`graph_file`**: Ruta al archivo .osm o .graphml con el mapa
- **`cell_length`**: Longitud de cada celda en metros (default: 7.5m ≈ longitud de un auto)
- **`v_max`**: Velocidad máxima en celdas por paso de tiempo (default: 5)
- **`p_slow`**: Probabilidad de desaceleración aleatoria, entre 0 y 1 (default: 0.3)

### `initialize_vehicles`

- **`density`**: Fracción de celdas ocupadas por vehículos, entre 0 y 1 (default: 0.2)

### `animate`

- **`steps`**: Número de pasos de tiempo a simular (default: 100)
- **`interval`**: Intervalo entre frames en milisegundos (default: 100)
- **`save_as`**: Nombre de archivo para guardar la animación (opcional)

## 📊 Resultados

La simulación genera varias visualizaciones:

### Estado de la simulación
Muestra el mapa con los vehículos coloreados según su velocidad:
- 🟢 Verde: Velocidad alta
- 🟡 Amarillo: Velocidad media
- 🔴 Rojo: Velocidad baja/detenido

### Estadísticas
- **Velocidad promedio vs tiempo**: Evolución temporal del flujo de tráfico
- **Distribución de velocidades**: Histograma de velocidades en un instante

### Animación
Animación GIF que muestra la evolución de la simulación en el tiempo.

## 🧪 Ejemplos de Estudio

### Efecto de la densidad
Al aumentar la densidad de vehículos:
- ⬆️ **Densidad baja (10%)**: Flujo libre, velocidades cercanas a v_max
- ⬆️ **Densidad media (30%)**: Aparecen atascos locales
- ⬆️ **Densidad alta (50%)**: Congestión generalizada, velocidades bajas

### Efecto de p_slow
El parámetro `p_slow` modela incertidumbre (cambios de carril, distracciones, etc.):
- **p_slow = 0.0**: Flujo determinista, sin fluctuaciones
- **p_slow = 0.3**: Flujo realista con variaciones naturales
- **p_slow = 0.8**: Alta incertidumbre, flujo muy irregular

## 📁 Estructura del Proyecto

```
Traffic/
├── src/                          # Código fuente principal
│   ├── __init__.py              # Inicialización del paquete
│   └── traffic_simulation.py   # Implementación del modelo NS
│
├── examples/                     # Scripts de ejemplo
│   ├── run_simulation.py        # Ejemplos básicos interactivos
│   └── advanced_examples.py     # Análisis científicos avanzados
│
├── tests/                        # Tests y validación
│   └── test_installation.py     # Script de prueba de instalación
│
├── data/                         # Datos de mapas OSM
│   ├── map_reduced.osm          # Mapa reducido de ejemplo
│   ├── map_reduced.graphml      # Grafo reducido
│   ├── map.osm                  # Mapa completo
│   └── map.graphml              # Grafo completo
│
├── docs/                         # Documentación
│   ├── QUICKSTART.md            # Guía de inicio rápido
│   └── TECHNICAL_NOTES.md       # Notas técnicas detalladas
│
├── sim.py                        # Script original para cargar mapas OSM
├── run.py                        # Script de ayuda para comandos comunes
├── setup.py                      # Configuración de instalación del paquete
├── requirements.txt              # Dependencias del proyecto
├── .gitignore                    # Archivos ignorados por git
└── README.md                     # Este archivo
```

## 🔬 Fundamentos Teóricos

El modelo de Nagel-Schreckenberg (1992) es uno de los modelos más simples y estudiados de tráfico vehicular. A pesar de su simplicidad, captura fenómenos complejos como:

- **Formación espontánea de atascos**: Incluso sin obstáculos externos
- **Ondas de choque**: Propagación de perturbaciones hacia atrás
- **Transición de fase**: Entre flujo libre y flujo congestionado
- **Diagrama fundamental**: Relación entre densidad, flujo y velocidad

### Adaptación a grafos 2D

Esta implementación extiende el modelo 1D original a una red 2D de calles:
- Las calles se discretizan en celdas
- Los vehículos pueden cambiar de calle en las intersecciones
- Se mantienen las reglas fundamentales del modelo

## 📚 Referencias

- K. Nagel and M. Schreckenberg, "A cellular automaton model for freeway traffic", *Journal de Physique I*, 1992
- Documentación de OSMnx: https://osmnx.readthedocs.io/

## 💡 Extensiones y Características Avanzadas

### Implementadas

- [x] **Semáforos en intersecciones**: Sistema completo de semáforos con fases configurables
- [x] **Optimización genética de semáforos**: Algoritmo genético para optimizar tiempos
- [x] **Editor interactivo de semáforos**: Herramienta visual para seleccionar ubicaciones
- [x] **Sistema de zonas O-D**: Generación de vehículos basada en matrices origen-destino
- [x] **Editor de zonas**: Interfaz gráfica para definir zonas de tráfico

### Pendientes

- [ ] Añadir diferentes tipos de vehículos (autos, buses, motos)
- [ ] Implementar cambios de carril en calles multi-carril
- [ ] Calcular métricas de rendimiento adicionales (throughput, tiempo de viaje)
- [ ] Simulación de accidentes y bloqueos temporales
- [ ] Exportar datos para análisis estadístico detallado

### Documentación adicional

- 📖 [Editor de Semáforos](docs/TRAFFIC_LIGHT_EDITOR.md): Guía del editor interactivo
- 📖 [Semáforos](docs/TRAFFIC_LIGHTS.md): Documentación del sistema de semáforos
- 📖 [Zonas O-D](docs/ZONES_WORKFLOW.md): Flujo de trabajo con zonas origen-destino

## 📄 Licencia

Este proyecto es de uso educativo y de investigación.

## ✍️ Autor

Proyecto de simulación de sistemas complejos.
