# 📚 Índice de Documentación

Bienvenido al proyecto de **Simulación de Tráfico usando el Modelo de Nagel-Schreckenberg**.

## 🚀 Por Dónde Empezar

Si eres nuevo en el proyecto, sigue esta ruta:

1. **[README.md](README.md)** - Visión general del proyecto
2. **[INSTALL.md](INSTALL.md)** - Instrucciones de instalación detalladas
3. **[docs/QUICKSTART.md](docs/QUICKSTART.md)** - Guía de inicio rápido con ejemplos
4. **[docs/TECHNICAL_NOTES.md](docs/TECHNICAL_NOTES.md)** - Detalles técnicos del modelo

## 📖 Documentación Principal

### Archivos en la Raíz

- **[README.md](README.md)**
  - Descripción general del proyecto
  - Características principales
  - Estructura del proyecto
  - Ejemplos de uso básico
  - Referencias y licencia

- **[INSTALL.md](INSTALL.md)**
  - Instrucciones de instalación paso a paso
  - Requisitos del sistema
  - Configuración de entornos virtuales
  - Solución de problemas comunes
  - Verificación de instalación

### Documentación Técnica (`docs/`)

- **[docs/QUICKSTART.md](docs/QUICKSTART.md)**
  - Guía de inicio rápido
  - Primeros pasos en 5 minutos
  - Ejemplos de código prácticos
  - Casos de uso comunes
  - Parámetros recomendados
  - Tips y trucos

- **[docs/TECHNICAL_NOTES.md](docs/TECHNICAL_NOTES.md)**
  - Implementación detallada del modelo
  - Parámetros y su significado físico
  - Fenómenos observables
  - Métricas de rendimiento
  - Calibración del modelo
  - Validación científica
  - Referencias académicas

## 💻 Código Fuente

### Módulo Principal (`src/`)

- **[src/traffic_simulation.py](src/traffic_simulation.py)**
  - Clase `Vehicle`: Representa vehículos individuales
  - Clase `TrafficSimulation`: Motor de simulación
  - Implementación de las reglas de Nagel-Schreckenberg
  - Sistema de visualización

- **[src/__init__.py](src/__init__.py)**
  - Inicialización del paquete
  - Exports públicos

### Ejemplos (`examples/`)

- **[examples/run_simulation.py](examples/run_simulation.py)**
  - 5 ejemplos básicos interactivos
  - Comparaciones de parámetros
  - Generación de visualizaciones
  - Casos de uso prácticos

- **[examples/advanced_examples.py](examples/advanced_examples.py)**
  - Análisis científicos avanzados
  - Diagrama fundamental del tráfico
  - Transición de fase
  - Estudios de estocasticidad
  - Diagramas espacio-temporales

### Tests (`tests/`)

- **[tests/test_installation.py](tests/test_installation.py)**
  - Verificación de dependencias
  - Tests básicos de funcionamiento
  - Validación de instalación

## 🗂️ Datos

### Mapas (`data/`)

- **data/map_reduced.osm** - Mapa pequeño para pruebas rápidas
- **data/map_reduced.graphml** - Grafo del mapa reducido
- **data/map.osm** - Mapa completo de la región
- **data/map.graphml** - Grafo del mapa completo

## 🛠️ Scripts Utilitarios

### En la Raíz

- **[run.py](run.py)**
  - Script de ayuda para comandos comunes
  - Atajos para ejecutar tests y ejemplos
  - Menú interactivo de ayuda

- **[sim.py](sim.py)**
  - Script original para procesar mapas OSM
  - Conversión de .osm a .graphml

- **[setup.py](setup.py)**
  - Configuración de instalación como paquete
  - Metadatos del proyecto
  - Definición de dependencias

## 📋 Archivos de Configuración

- **[requirements.txt](requirements.txt)**
  - Lista de dependencias de Python
  - Versiones específicas requeridas

- **[.gitignore](.gitignore)**
  - Archivos excluidos del control de versiones
  - Patrones de exclusión

## 🎯 Flujos de Trabajo Recomendados

### Para Usuarios Nuevos

```
1. README.md → 2. INSTALL.md → 3. run.py test → 4. docs/QUICKSTART.md
```

### Para Desarrollo

```
1. docs/TECHNICAL_NOTES.md → 2. src/traffic_simulation.py → 3. examples/
```

### Para Análisis Científico

```
1. docs/TECHNICAL_NOTES.md → 2. examples/advanced_examples.py → 3. Personalizar
```

## 🔍 Búsqueda Rápida

¿Buscas algo específico?

| Tema | Archivo |
|------|---------|
| **Instalación** | [INSTALL.md](INSTALL.md) |
| **Primeros pasos** | [docs/QUICKSTART.md](docs/QUICKSTART.md) |
| **API del código** | [src/traffic_simulation.py](src/traffic_simulation.py) |
| **Ejemplos básicos** | [examples/run_simulation.py](examples/run_simulation.py) |
| **Análisis científico** | [examples/advanced_examples.py](examples/advanced_examples.py) |
| **Teoría del modelo** | [docs/TECHNICAL_NOTES.md](docs/TECHNICAL_NOTES.md) |
| **Parámetros** | [docs/TECHNICAL_NOTES.md](docs/TECHNICAL_NOTES.md#-parámetros-y-su-significado) |
| **Calibración** | [docs/TECHNICAL_NOTES.md](docs/TECHNICAL_NOTES.md#-calibración-del-modelo) |
| **Problemas comunes** | [INSTALL.md](INSTALL.md#-solución-de-problemas-comunes) |
| **Tests** | [tests/test_installation.py](tests/test_installation.py) |

## 📊 Estructura Visual

```
┌─────────────────────────────────────────────────────────────┐
│                      Traffic Project                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  📄 Documentación Principal                                 │
│  ├── README.md ..................... Visión general         │
│  ├── INSTALL.md .................... Instalación           │
│  └── INDEX.md (este archivo) ....... Índice                │
│                                                              │
│  📁 src/ ........................... Código fuente          │
│  │   ├── __init__.py                                        │
│  │   └── traffic_simulation.py                             │
│                                                              │
│  📁 examples/ ...................... Scripts de ejemplo     │
│  │   ├── run_simulation.py                                  │
│  │   └── advanced_examples.py                              │
│                                                              │
│  📁 tests/ ......................... Tests                  │
│  │   └── test_installation.py                              │
│                                                              │
│  📁 data/ .......................... Mapas OSM              │
│  │   ├── map_reduced.osm                                    │
│  │   ├── map_reduced.graphml                               │
│  │   ├── map.osm                                            │
│  │   └── map.graphml                                        │
│                                                              │
│  📁 docs/ .......................... Documentación técnica  │
│  │   ├── QUICKSTART.md                                      │
│  │   └── TECHNICAL_NOTES.md                                │
│                                                              │
│  🛠️ Utilidades                                              │
│  ├── run.py ........................ Helper script          │
│  ├── sim.py ........................ Procesador OSM         │
│  ├── setup.py ...................... Configuración          │
│  ├── requirements.txt .............. Dependencias          │
│  └── .gitignore .................... Git config            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 🆘 Soporte

Si tienes dudas:
1. Consulta este índice para encontrar el documento adecuado
2. Revisa la sección de "Solución de Problemas" en [INSTALL.md](INSTALL.md)
3. Lee las FAQs en [docs/QUICKSTART.md](docs/QUICKSTART.md)

## 📝 Contribuir

Para contribuir al proyecto:
1. Lee [docs/TECHNICAL_NOTES.md](docs/TECHNICAL_NOTES.md) para entender el modelo
2. Revisa el código en [src/traffic_simulation.py](src/traffic_simulation.py)
3. Añade tus ejemplos en la carpeta `examples/`
4. Documenta tus cambios

---

**Última actualización**: 25 de octubre de 2025
