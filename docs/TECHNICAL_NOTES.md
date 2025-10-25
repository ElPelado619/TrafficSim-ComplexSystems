# Notas Técnicas - Modelo de Nagel-Schreckenberg

## 🎯 Implementación del Modelo

### Discretización del Espacio

El grafo de calles continuo se discretiza en celdas de tamaño configurable:

```
Longitud de calle (metros) / Longitud de celda (metros) = Número de celdas
```

Por defecto, usamos `cell_length = 7.5m`, que aproximadamente corresponde a:
- Longitud promedio de un auto (4.5m)
- Distancia de seguridad mínima (3m)

### Adaptación a Grafos 2D

El modelo original de NS es unidimensional (una carretera). Esta implementación lo extiende a un grafo 2D:

1. **Cada arista del grafo** se trata como una carretera 1D independiente
2. **En las intersecciones**, los vehículos eligen aleatoriamente una salida disponible
3. **Las reglas de NS** se aplican dentro de cada arista

### Reglas del Modelo

Para cada vehículo en cada paso de tiempo:

#### 1. Aceleración
```python
if v < v_max:
    v = v + 1
```

#### 2. Frenado
```python
d = distance_to_next_vehicle()
if v >= d:
    v = d - 1
```

#### 3. Aleatorización
```python
if v > 0 and random() < p_slow:
    v = v - 1
```

#### 4. Movimiento
```python
position = position + v
```

## 📊 Parámetros y su Significado

### `cell_length` (metros)
- **Valor típico**: 5-10 metros
- **Efecto**: 
  - Menor → Mayor resolución espacial, más tiempo de cómputo
  - Mayor → Menor resolución, simulación más rápida
  
### `v_max` (celdas/paso)
- **Valor típico**: 5
- **Conversión a velocidad real**:
  ```
  v_real (km/h) = (v_max × cell_length × 3600) / (1000 × tiempo_paso_real)
  ```
  Con `cell_length=7.5m` y `v_max=5`:
  - Si 1 paso = 1 segundo → v_max ≈ 135 km/h
  - Si 1 paso = 2 segundos → v_max ≈ 67.5 km/h

### `p_slow` (probabilidad)
- **Valor típico**: 0.2-0.4
- **Interpretación física**:
  - Modelo de incertidumbre del conductor
  - Cambios de carril
  - Distracciones momentáneas
  - Condiciones de la vía
  
### `density` (fracción)
- **Valor típico**: 0.1-0.5
- **Regímenes de tráfico**:
  - `< 0.15`: Flujo libre
  - `0.15-0.30`: Flujo sincronizado
  - `> 0.30`: Congestión

## 🔬 Fenómenos Observables

### 1. Diagrama Fundamental del Tráfico

La relación entre densidad (ρ), flujo (J) y velocidad (v):

```
J = ρ × v
```

En el modelo NS, se observa:
- **Flujo máximo** en densidad crítica ρ_c ≈ 0.25
- **Transición de fase** entre flujo libre y congestionado

### 2. Formación de Atascos

Atascos "fantasma" que aparecen espontáneamente debido a:
- Desaceleración estocástica (`p_slow`)
- Efecto cascada hacia atrás
- No requieren obstáculos externos

### 3. Ondas de Choque

Perturbaciones que se propagan en dirección contraria al flujo:
- Velocidad de propagación: `-v_wave`
- Frente de onda: transición abrupta de velocidades

### 4. Metaestabilidad

Estados temporalmente estables que eventualmente colapsan:
- Flujo libre metaestable → colapso en congestión
- Tiempo de vida depende de `p_slow`

## 🧮 Métricas de Rendimiento

### Velocidad Promedio
```python
v_avg = (1/N) × Σ v_i
```
donde N es el número de vehículos.

### Flujo (Throughput)
Número de vehículos que pasan por un punto por unidad de tiempo:
```python
J = número_de_vehículos_que_pasan / tiempo
```

### Tiempo de Viaje
Tiempo que tarda un vehículo en atravesar el sistema:
```python
T = distancia_total / velocidad_promedio
```

## 🎨 Visualización

### Código de Colores por Velocidad

La visualización usa un mapa de colores que indica la velocidad:
- 🔴 Rojo (v=0): Detenido
- 🟠 Naranja (v=1-2): Muy lento
- 🟡 Amarillo (v=3): Lento
- 🟢 Verde claro (v=4): Moderado
- 🟢 Verde (v=v_max): Velocidad máxima

### Interpretación de Patrones

- **Puntos rojos agrupados**: Atasco
- **Transición gradual de colores**: Onda de densidad
- **Verde uniforme**: Flujo libre
- **Patrón oscilante**: Inestabilidad

## 🔧 Consideraciones Técnicas

### Manejo de Intersecciones

Cuando un vehículo llega al final de una arista:
1. Se obtienen todas las aristas salientes del nodo destino
2. Se elige una aleatoriamente (distribución uniforme)
3. Si no hay aristas salientes, el vehículo se detiene

Mejoras futuras:
- [ ] Probabilidades no uniformes (basadas en distancias)
- [ ] Semáforos en intersecciones
- [ ] Prioridad de paso

### Detección de Colisiones

El sistema previene colisiones mediante:
1. Regla de frenado en el paso 2 del algoritmo
2. Verificación antes del movimiento
3. Mapa de ocupación: `{edge: {position: vehicle_id}}`

### Condiciones de Frontera

En calles sin salida:
- Los vehículos se detienen al final
- No se crean ni destruyen vehículos
- Número total de vehículos es constante

## 📈 Calibración del Modelo

Para calibrar el modelo con datos reales:

1. **Medir velocidad promedio real**: v_real (km/h)
2. **Definir escala temporal**: Δt (segundos por paso)
3. **Calcular v_max**:
   ```
   v_max = (v_real × 1000 × Δt) / (3600 × cell_length)
   ```
4. **Ajustar p_slow** para reproducir varianza observada
5. **Validar** comparando distribuciones de velocidad

## 🚀 Optimizaciones Posibles

### Rendimiento Computacional

Actualmente: O(N) por paso, donde N = número de vehículos

Optimizaciones:
- [ ] Usar estructuras de datos espaciales (quadtree)
- [ ] Paralelizar actualización de vehículos
- [ ] Compilar con Numba/Cython
- [ ] GPU computing (CUDA)

### Escalabilidad

Para mapas grandes:
- [ ] Simulación por regiones
- [ ] Nivel de detalle variable
- [ ] Actualización selectiva (solo regiones activas)

## 📚 Validación Científica

El modelo NS reproduce correctamente:
- ✅ Diagrama fundamental del tráfico
- ✅ Transición de fase flujo libre ↔ congestión
- ✅ Formación de atascos espontáneos
- ✅ Propagación de ondas de densidad

Limitaciones:
- ❌ No modela cambios de carril explícitamente
- ❌ Todos los vehículos son idénticos
- ❌ No considera semáforos nativamente
- ❌ Elección de ruta es aleatoria

## 🔗 Referencias Adicionales

### Artículos Fundamentales
1. Nagel & Schreckenberg (1992) - Artículo original
2. Chowdhury et al. (2000) - Review comprehensivo
3. Maerivoet & De Moor (2005) - Modelos celulares

### Extensiones del Modelo
- VDR (Velocity Dependent Randomization)
- TASEP (Totally Asymmetric Simple Exclusion Process)
- Multi-lane NS model
- NS con anticipación

### Software Relacionado
- SUMO (Simulation of Urban MObility)
- MATSim (Multi-Agent Transport Simulation)
- VISSIM (Microscopic traffic simulation)
