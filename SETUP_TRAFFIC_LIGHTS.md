# Instalación y Configuración del Sistema de Semáforos

## 🚀 Instalación Rápida

### 1. Instalar dependencias actualizadas

```powershell
pip install -r requirements.txt
```

Esto instalará todas las dependencias necesarias incluyendo:
- `tqdm` (nueva): Barras de progreso para el algoritmo genético
- `osmnx`, `networkx`, `numpy`, `matplotlib`, `pillow` (existentes)

### 2. Verificar instalación

```powershell
python -c "import tqdm; print('tqdm instalado correctamente')"
```

## 📋 Nuevos Archivos del Sistema

### Módulos principales:
- **`src/traffic_light.py`**: Clases TrafficLight y TrafficLightSystem
- **`generador_semaforos.py`**: Optimizador genético

### Scripts de ejemplo:
- **`examples/run_with_traffic_lights.py`**: Script integrado completo

### Documentación:
- **`docs/TRAFFIC_LIGHTS.md`**: Documentación detallada del sistema
- **`docs/ZONES_WORKFLOW.md`**: Actualizado con flujo de semáforos
- **`TRAFFIC_LIGHTS_UPDATE.md`**: Resumen de la actualización

## 🎯 Prueba Rápida (5 minutos)

Si ya tienes zonas y matriz O-D generadas:

```powershell
# Optimizar semáforos (configuración rápida para pruebas)
python generador_semaforos.py `
  --zones data/O-D-maps/microcentro_zones.json `
  --od data/O-D-maps/microcentro_zones_matrix.json `
  --output data/traffic_lights.json `
  --population 10 `
  --generations 5

# Ejecutar simulación
python examples/run_with_traffic_lights.py `
  --zones data/O-D-maps/microcentro_zones.json `
  --od data/O-D-maps/microcentro_zones_matrix.json `
  --lights-file data/traffic_lights.json `
  --steps 500 `
  --scale 0.01
```

## 📝 Flujo Completo desde Cero

### 1. Crear zonas (interfaz gráfica)

```powershell
python run.py zones
```

- Dibuja polígonos sobre el mapa
- Asigna producción y atracción a cada zona
- Guarda en `data/O-D-maps/microcentro_zones.json`

### 2. Generar matriz O-D

```powershell
python generador_od.py `
  --zone-file data/O-D-maps/microcentro_zones.json `
  --output data/O-D-maps/microcentro_zones_matrix.json `
  --beta 0.015
```

### 3. Optimizar semáforos

**Opción A - Rápida (para testing):**
```powershell
python generador_semaforos.py `
  --zones data/O-D-maps/microcentro_zones.json `
  --od data/O-D-maps/microcentro_zones_matrix.json `
  --output data/traffic_lights.json `
  --population 10 `
  --generations 5 `
  --scale 0.01
```
⏱️ ~2-3 minutos

**Opción B - Estándar (recomendada):**
```powershell
python generador_semaforos.py `
  --zones data/O-D-maps/microcentro_zones.json `
  --od data/O-D-maps/microcentro_zones_matrix.json `
  --output data/traffic_lights.json `
  --population 30 `
  --generations 20 `
  --scale 0.01
```
⏱️ ~10-15 minutos

**Opción C - Óptima (mejor resultado):**
```powershell
python generador_semaforos.py `
  --zones data/O-D-maps/microcentro_zones.json `
  --od data/O-D-maps/microcentro_zones_matrix.json `
  --output data/traffic_lights.json `
  --population 50 `
  --generations 40 `
  --scale 0.01
```
⏱️ ~30-40 minutos

### 4. Ejecutar simulación con semáforos

```powershell
python examples/run_with_traffic_lights.py `
  --zones data/O-D-maps/microcentro_zones.json `
  --od data/O-D-maps/microcentro_zones_matrix.json `
  --lights-file data/traffic_lights.json `
  --animation-gif data/runs/microcentro_anim.gif `
  --save-prefix data/runs/microcentro `
  --steps 1000 `
  --scale 0.01 `
  --no-show
```

### 5. Ver resultados

Los archivos generados estarán en `data/runs/`:
- `microcentro_anim.gif`: Animación de la simulación
- `microcentro_final_state.png`: Estado final
- `microcentro_stats.png`: Gráficos de estadísticas

## 🔄 Flujo Todo-en-Uno

Para ejecutar optimización + simulación en un solo comando:

```powershell
python examples/run_with_traffic_lights.py `
  --zones data/O-D-maps/microcentro_zones.json `
  --od data/O-D-maps/microcentro_zones_matrix.json `
  --optimize-lights `
  --save-lights data/traffic_lights.json `
  --animation-gif data/runs/microcentro_anim.gif `
  --save-prefix data/runs/microcentro `
  --steps 1000 `
  --scale 0.01 `
  --population 20 `
  --generations 15 `
  --no-show
```

## 🎓 Entender los Parámetros

### Algoritmo Genético:
- `--population`: Más individuos = mejor exploración, pero más lento
- `--generations`: Más generaciones = mejor convergencia
- `--mutation-rate`: Tasa de cambios aleatorios (0.1 = 10%)
- `--elite-size`: Mejores individuos que se preservan intactos

### Simulación:
- `--scale`: Multiplica la demanda O-D en número de vehículos
  - 0.001: Muy ligero (debugging)
  - 0.01: Normal (recomendado)
  - 0.05: Denso
  - 0.1: Muy denso (congestión)
- `--steps`: Número de pasos de tiempo a simular
- `--v-max`: Velocidad máxima de vehículos (celdas/paso)
- `--p-slow`: Probabilidad de desaceleración aleatoria

## 🐛 Solución de Problemas

### Error: "Import tqdm could not be resolved"
```powershell
pip install tqdm
```

### Error: "No se encontró el archivo de zonas"
Primero ejecuta:
```powershell
python run.py zones
```
para crear zonas, luego genera la matriz O-D.

### El algoritmo genético es muy lento
Reduce los parámetros:
```powershell
--population 10 --generations 5
```

### No se muestran los semáforos en la visualización
Verifica que:
1. El archivo `traffic_lights.json` existe
2. Se está usando `--lights-file` o `--optimize-lights`
3. El grafo tiene nodos con grado >= 3

### Los vehículos no respetan los semáforos
Asegúrate de que:
1. Los semáforos se cargaron antes de generar vehículos
2. Los `node_id` en el JSON corresponden a nodos reales del grafo

## 📊 Interpretar Resultados

### En consola:
```
Mejor fitness: 3.4521
```
Mayor fitness = mejor configuración de semáforos

### En visualización:
- **Verde/amarillo en vehículos**: Flujo fluido
- **Rojo en vehículos**: Congestión/detenciones
- **Círculos verdes**: Semáforos permitiendo paso
- **Círculos rojos**: Semáforos deteniendo tráfico

### Gráficas de estadísticas:
- **Velocidad promedio alta y constante**: Buena configuración
- **Velocidad con muchas fluctuaciones**: Mala sincronización
- **Velocidad decreciente**: Congestión creciente

## ✅ Verificación de Funcionamiento

Ejecuta este test completo:

```powershell
# 1. Verificar módulos
python -c "from src.traffic_light import TrafficLight; print('✓ traffic_light OK')"
python -c "from src.traffic_simulation import TrafficSimulation; print('✓ traffic_simulation OK')"
python -c "import generador_semaforos; print('✓ generador_semaforos OK')"

# 2. Test con datos de ejemplo (si existen)
python examples/run_with_traffic_lights.py `
  --zones data/O-D-maps/microcentro_zones.json `
  --od data/O-D-maps/microcentro_zones_matrix.json `
  --optimize-lights `
  --steps 100 `
  --scale 0.01 `
  --population 5 `
  --generations 3 `
  --no-show
```

Si todo funciona, verás:
```
✓ Optimización completada
✓ Simulación completada exitosamente
```

## 📚 Documentación Adicional

- **Tutorial completo**: Ver `docs/ZONES_WORKFLOW.md`
- **Detalles técnicos**: Ver `docs/TRAFFIC_LIGHTS.md`
- **Resumen de cambios**: Ver `TRAFFIC_LIGHTS_UPDATE.md`

## 💬 Comandos de Ayuda

```powershell
# Ver opciones del generador de semáforos
python generador_semaforos.py --help

# Ver opciones del script de simulación
python examples/run_with_traffic_lights.py --help

# Ver opciones del generador O-D
python generador_od.py --help
```

---

**¡Listo para optimizar tu tráfico! 🚦✨**
