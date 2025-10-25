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

## 💡 Posibles Extensiones

- [ ] Implementar semáforos en las intersecciones
- [ ] Añadir diferentes tipos de vehículos (autos, buses, motos)
- [ ] Implementar cambios de carril en calles multi-carril
- [ ] Calcular métricas de rendimiento (throughput, tiempo de viaje)
- [ ] Optimización de fases de semáforos
- [ ] Simulación de accidentes y bloqueos temporales
- [ ] Exportar datos para análisis estadístico detallado

## 📄 Licencia

Este proyecto es de uso educativo y de investigación.

## ✍️ Autor

Proyecto de simulación de sistemas complejos.
