# Guía de Inicio Rápido

## 🚀 Comenzar en 5 minutos

### Paso 1: Instalar dependencias

```bash
pip install -r requirements.txt
```

### Paso 2: Verificar instalación

```bash
python tests/test_installation.py
```

Deberías ver:
```
✓ Todas las dependencias están instaladas
✓ Simulación creada correctamente
✓ X vehículos inicializados
✓ PRUEBA EXITOSA
```

### Paso 3: Ejecutar tu primera simulación

```bash
python examples/run_simulation.py
```

Selecciona la opción `1` para ver una simulación básica.

## 📊 Tu Primera Simulación (Código)

Crea un archivo `mi_simulacion.py`:

```python
from src.traffic_simulation import TrafficSimulation

# Crear simulación
sim = TrafficSimulation(
    graph_file='data/map_reduced.osm',
    cell_length=7.5,  # metros por celda
    v_max=5,          # velocidad máxima
    p_slow=0.3        # probabilidad de desaceleración
)

# Añadir vehículos (20% de densidad)
sim.initialize_vehicles(density=0.2)

# Ejecutar 100 pasos
for i in range(100):
    sim.step()
    if (i+1) % 20 == 0:
        print(f"Paso {i+1}: velocidad promedio = {sim.avg_velocities[-1]:.2f}")

# Visualizar resultado
sim.plot_state()
sim.plot_statistics()
```

Ejecuta:
```bash
python mi_simulacion.py
```

## 🎨 Crear una Animación

```python
from src.traffic_simulation import TrafficSimulation

sim = TrafficSimulation('data/map_reduced.osm')
sim.initialize_vehicles(density=0.15)
sim.animate(steps=100, interval=100, save_as='mi_animacion.gif')
```

## 🔬 Análisis Científico Básico

```python
from src.traffic_simulation import TrafficSimulation
import matplotlib.pyplot as plt

densidades = [0.1, 0.2, 0.3, 0.4, 0.5]
velocidades_finales = []

for densidad in densidades:
    sim = TrafficSimulation('data/map_reduced.osm')
    sim.initialize_vehicles(density=densidad)
    
    # Simular hasta estado estacionario
    for _ in range(100):
        sim.step()
    
    velocidades_finales.append(sim.avg_velocities[-1])

# Graficar diagrama velocidad vs densidad
plt.plot(densidades, velocidades_finales, 'o-')
plt.xlabel('Densidad')
plt.ylabel('Velocidad Promedio')
plt.title('Efecto de la Densidad en la Velocidad')
plt.grid(True)
plt.show()
```

## 🎯 Casos de Uso Comunes

### 1. Estudiar un atasco

```python
# Alta densidad para generar congestión
sim = TrafficSimulation('data/map_reduced.osm', v_max=5, p_slow=0.5)
sim.initialize_vehicles(density=0.5)
sim.animate(steps=150)
```

### 2. Tráfico fluido

```python
# Baja densidad para flujo libre
sim = TrafficSimulation('data/map_reduced.osm', v_max=5, p_slow=0.1)
sim.initialize_vehicles(density=0.1)
sim.animate(steps=100)
```

### 3. Comparar escenarios

```python
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Escenario 1: Sin estocasticidad
sim1 = TrafficSimulation('data/map_reduced.osm', p_slow=0.0)
sim1.initialize_vehicles(density=0.25)
for _ in range(100):
    sim1.step()
sim1.plot_state(ax=axes[0])
axes[0].set_title('Sin estocasticidad (p_slow=0)')

# Escenario 2: Con estocasticidad
sim2 = TrafficSimulation('data/map_reduced.osm', p_slow=0.5)
sim2.initialize_vehicles(density=0.25)
for _ in range(100):
    sim2.step()
sim2.plot_state(ax=axes[1])
axes[1].set_title('Con estocasticidad (p_slow=0.5)')

plt.tight_layout()
plt.show()
```

## ⚙️ Parámetros Recomendados

### Tráfico urbano típico
```python
sim = TrafficSimulation(
    'data/map_reduced.osm',
    cell_length=7.5,  # auto + espacio de seguridad
    v_max=5,          # ~135 km/h máx (poco realista en ciudad)
    p_slow=0.3        # bastante estocasticidad
)
sim.initialize_vehicles(density=0.2)
```

### Tráfico en autopista
```python
sim = TrafficSimulation(
    'data/map_reduced.osm',
    cell_length=10.0,  # mayor espacio
    v_max=8,           # mayor velocidad máxima
    p_slow=0.1         # menos variaciones
)
sim.initialize_vehicles(density=0.15)
```

### Tráfico congestionado
```python
sim = TrafficSimulation(
    'data/map_reduced.osm',
    cell_length=5.0,   # más resolución
    v_max=3,           # velocidad baja
    p_slow=0.4         # alta variabilidad
)
sim.initialize_vehicles(density=0.4)
```

## 🐛 Solución de Problemas

### Error: "No module named 'osmnx'"
```bash
pip install osmnx
```

### Error: "No such file or directory: 'map_reduced.osm'"
Asegúrate de estar en el directorio raíz del proyecto:
```bash
cd Traffic
python examples/run_simulation.py
```

### La animación no se guarda
Instala Pillow:
```bash
pip install pillow
```

### La simulación es muy lenta
Reduce el tamaño del mapa o aumenta `cell_length`:
```python
sim = TrafficSimulation('data/map_reduced.osm', cell_length=15.0)
```

## 📚 Próximos Pasos

1. ✅ Ejecuta los ejemplos básicos: `python examples/run_simulation.py`
2. ✅ Prueba los ejemplos avanzados: `python examples/advanced_examples.py`
3. ✅ Lee las notas técnicas: `docs/TECHNICAL_NOTES.md`
4. ✅ Crea tu propia simulación personalizada
5. ✅ Experimenta con diferentes parámetros

## 💡 Ideas para Experimentar

- Variar `v_max` y observar cómo cambia el flujo
- Comparar diferentes valores de `p_slow`
- Estudiar cómo la densidad afecta la formación de atascos
- Analizar el tiempo hasta el estado estacionario
- Medir el flujo en diferentes puntos del mapa
- Crear mapas personalizados con diferentes topologías

## 🤝 Compartir Resultados

Guarda tus resultados:
```python
# Guardar estado
sim.plot_state()
plt.savefig('mi_resultado.png', dpi=300)

# Guardar estadísticas
sim.plot_statistics()
plt.savefig('mis_estadisticas.png', dpi=300)

# Guardar animación
sim.animate(steps=100, save_as='mi_animacion.gif')
```

---

**¿Necesitas ayuda?** Revisa el README.md principal y TECHNICAL_NOTES.md
