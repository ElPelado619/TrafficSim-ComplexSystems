# Instrucciones de Instalación

## 📦 Instalación Básica

### Opción 1: Instalación simple (recomendada)

```bash
# 1. Clonar o descargar el repositorio
cd Traffic

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Verificar instalación
python run.py test
```

### Opción 2: Instalación como paquete

Si quieres instalar el proyecto como un paquete de Python:

```bash
# Instalación en modo desarrollo (recomendado para desarrollo)
pip install -e .

# O instalación normal
pip install .
```

Esto instalará el paquete `src` y permitirá importarlo desde cualquier lugar:

```python
from src.traffic_simulation import TrafficSimulation
```

## 🔧 Requisitos del Sistema

- **Python**: 3.8 o superior
- **Sistema Operativo**: Windows, macOS, Linux
- **Memoria RAM**: Mínimo 4GB (recomendado 8GB para simulaciones grandes)
- **Espacio en disco**: ~500MB (incluyendo dependencias)

## 📚 Dependencias Principales

Las dependencias se instalarán automáticamente con `pip install -r requirements.txt`:

- **osmnx** (>=1.9.0): Procesamiento de mapas de OpenStreetMap
- **networkx** (>=3.0): Manejo de grafos
- **numpy** (>=1.24.0): Cálculos numéricos
- **matplotlib** (>=3.7.0): Visualización
- **pillow** (>=10.0.0): Generación de GIFs

## 🐍 Entornos Virtuales

### Usando venv (recomendado)

```bash
# Crear entorno virtual
python -m venv .venv

# Activar entorno virtual
# En Windows:
.venv\Scripts\activate
# En Linux/macOS:
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### Usando conda

```bash
# Crear entorno
conda create -n traffic python=3.11

# Activar entorno
conda activate traffic

# Instalar dependencias
pip install -r requirements.txt
```

## ✅ Verificación de Instalación

Después de instalar las dependencias, verifica que todo funcione:

```bash
python run.py test
```

Deberías ver:
```
✓ Todas las dependencias están instaladas
✓ Simulación creada correctamente
✓ X vehículos inicializados
✓ PRUEBA EXITOSA
```

## 🔍 Solución de Problemas Comunes

### Error: "No module named 'osmnx'"

```bash
pip install osmnx
```

### Error: "Microsoft Visual C++ 14.0 is required"

En Windows, instala las Build Tools de Microsoft Visual C++:
- Descarga desde: https://visualstudio.microsoft.com/visual-cpp-build-tools/

### Error con Shapely o GeoPandas

```bash
# En Windows, intenta:
conda install -c conda-forge geopandas

# O usa pip con wheels precompilados:
pip install --upgrade shapely geopandas
```

### Error: "ImportError: cannot import name 'TrafficSimulation'"

Asegúrate de estar en el directorio raíz del proyecto:
```bash
cd Traffic
python run.py test
```

### Problemas con matplotlib en sistemas sin GUI

Si estás ejecutando en un servidor sin interfaz gráfica:

```python
import matplotlib
matplotlib.use('Agg')  # Backend sin GUI
import matplotlib.pyplot as plt
```

## 🚀 Primeros Pasos Después de la Instalación

1. **Ejecuta el test de instalación**:
   ```bash
   python run.py test
   ```

2. **Prueba un ejemplo básico**:
   ```bash
   python run.py examples
   ```
   Selecciona la opción 1.

3. **Lee la guía rápida**:
   ```bash
   # Abre en tu editor favorito
   code docs/QUICKSTART.md
   ```

4. **Crea tu primera simulación personalizada**:
   ```python
   from src.traffic_simulation import TrafficSimulation
   
   sim = TrafficSimulation('data/map_reduced.osm')
   sim.initialize_vehicles(density=0.2)
   
   for _ in range(100):
       sim.step()
   
   sim.plot_state()
   ```

## 📊 Datos de Mapas

El proyecto incluye mapas de ejemplo en `data/`:
- `map_reduced.osm`: Mapa pequeño para pruebas rápidas
- `map.osm`: Mapa completo de la región

Para usar tus propios mapas:
1. Descarga un área de OpenStreetMap (formato .osm)
2. Colócalo en la carpeta `data/`
3. Úsalo en tu simulación:
   ```python
   sim = TrafficSimulation('data/tu_mapa.osm')
   ```

## 🔄 Actualización

Para actualizar las dependencias:

```bash
pip install --upgrade -r requirements.txt
```

## 📝 Notas Adicionales

- **Rendimiento**: Para simulaciones grandes, considera aumentar `cell_length` o reducir el área del mapa
- **Memoria**: El uso de memoria crece con el número de celdas (calles más largas / `cell_length` más pequeño)
- **Gráficos**: Las animaciones pueden consumir mucha memoria; usa `save_as` para guardarlas en disco

## 🆘 Soporte

Si tienes problemas:
1. Revisa esta guía de instalación
2. Consulta `docs/QUICKSTART.md`
3. Lee `docs/TECHNICAL_NOTES.md`
4. Revisa los issues en GitHub (si aplica)

## 📜 Licencia

Este proyecto es para uso educativo y de investigación.
