# Editor Interactivo de Semáforos

Este documento describe cómo usar el editor interactivo de semáforos para seleccionar qué nodos del grafo deben tener semáforos antes de ejecutar la optimización genética.

## Descripción

El editor de semáforos permite visualizar todos los nodos candidatos para semáforos en el mapa de la red vial y excluir aquellos donde no se desea colocar semáforos. Esto es útil para:

- Evitar semáforos en ubicaciones específicas por razones de diseño
- Reducir el espacio de búsqueda del algoritmo genético
- Experimentar con diferentes configuraciones de semáforos

## Uso Básico

### Desde el generador de semáforos

La forma más sencilla es usar la flag `--edit` al ejecutar el generador:

```bash
python generador_semaforos.py --edit
```

Esto abrirá el editor interactivo antes de comenzar la optimización genética. Los cambios se guardarán automáticamente y se aplicarán a la optimización.

### Uso independiente

También puedes ejecutar el editor de forma independiente:

```bash
python tools/traffic_light_editor.py --graph data/microcentro.graphml
```

### Opciones de línea de comandos

```bash
python tools/traffic_light_editor.py [opciones]
```

Opciones disponibles:

- `--graph PATH`: Archivo del grafo de la red vial (por defecto: `data/microcentro.graphml`)
- `--exclusions PATH`: Archivo JSON con nodos excluidos para cargar y editar
- `--output PATH`: Archivo de salida para las exclusiones (por defecto: `data/traffic_light_exclusions.json`)
- `--min-degree N`: Grado mínimo de nodo para considerarlo candidato (por defecto: 3)
- `--auto-save`: Guarda automáticamente al salir si hubo cambios

## Controles del Editor

Una vez abierto el editor, verás el mapa de la red vial con los nodos candidatos para semáforos:

- **Nodos verdes**: Nodos incluidos (tendrán semáforos)
- **Nodos rojos**: Nodos excluidos (no tendrán semáforos)

### Controles del ratón

- **Click izquierdo** en un nodo: Alterna su estado (incluido ↔ excluido)

### Atajos de teclado

- **`s`**: Guarda las exclusiones en el archivo JSON
- **`c`**: Limpia todas las exclusiones (excluye todos los candidatos)
- **`r`**: Resetea las exclusiones (incluye todos los candidatos)
- **`q`**: Cierra el editor

## Formato del archivo de exclusiones

El archivo de exclusiones es un JSON con el siguiente formato:

```json
{
  "excluded_nodes": [123, 456, 789],
  "total_candidates": 50,
  "min_degree": 3
}
```

Campos:

- `excluded_nodes`: Lista de IDs de nodos excluidos
- `total_candidates`: Número total de nodos candidatos identificados
- `min_degree`: Grado mínimo usado para identificar candidatos

## Flujo de trabajo completo

### 1. Identificar candidatos y editar

```bash
# Abrir el editor para seleccionar semáforos
python tools/traffic_light_editor.py \
    --graph data/microcentro.graphml \
    --output data/traffic_light_exclusions.json \
    --min-degree 3
```

### 2. Optimizar con exclusiones

```bash
# Ejecutar optimización genética con los nodos seleccionados
python generador_semaforos.py \
    --graph data/microcentro.graphml \
    --zones data/O-D-maps/microcentro_zones.json \
    --od data/O-D-maps/microcentro_zones_matrix.json \
    --exclusions data/traffic_light_exclusions.json \
    --output data/traffic_lights.json \
    --population 50 \
    --generations 30
```

### 3. Flujo integrado (recomendado)

```bash
# Editar y optimizar en un solo comando
python generador_semaforos.py \
    --edit \
    --graph data/microcentro.graphml \
    --zones data/O-D-maps/microcentro_zones.json \
    --od data/O-D-maps/microcentro_zones_matrix.json \
    --output data/traffic_lights.json
```

Este comando:
1. Abre el editor de semáforos
2. Carga exclusiones existentes si hay un archivo
3. Permite editar interactivamente
4. Guarda los cambios
5. Continúa con la optimización genética usando las exclusiones

## Criterios de candidatos

Un nodo se considera candidato para semáforo si cumple:

1. **Grado suficiente**: Tiene al menos `min-degree` (por defecto 3) conexiones entrantes + salientes
2. **No es rotonda**: No forma parte de una rotonda o glorieta
3. **No está excluido**: No está en la lista de exclusiones del usuario

## Ejemplos de uso

### Ejemplo 1: Excluir semáforos en zona residencial

Si identificas visualmente una zona residencial donde no quieres semáforos:

1. Ejecuta: `python tools/traffic_light_editor.py --graph data/microcentro.graphml`
2. Haz click en los nodos de esa zona para excluirlos (se pondrán rojos)
3. Presiona `s` para guardar
4. Presiona `q` para salir
5. Ejecuta la optimización con `--exclusions data/traffic_light_exclusions.json`

### Ejemplo 2: Experimentar con densidad de semáforos

Para probar con menos semáforos:

1. Abre el editor
2. Presiona `c` para excluir todos
3. Haz click solo en las intersecciones principales para incluirlas
4. Guarda y optimiza

### Ejemplo 3: Refinar iterativamente

1. Primera iteración: Optimiza con todos los candidatos
2. Analiza resultados y identifica problemas
3. Abre el editor y excluye nodos problemáticos
4. Vuelve a optimizar
5. Repite hasta obtener buenos resultados

## Integración con el algoritmo genético

El archivo de exclusiones se integra automáticamente en el proceso de optimización:

1. El `GeneticOptimizer` carga las exclusiones al inicializar
2. Los nodos excluidos se filtran de la lista de candidatos
3. El algoritmo genético solo considera los nodos incluidos
4. Los semáforos resultantes solo se colocarán en nodos incluidos

Esto permite un control fino sobre la configuración final de semáforos sin modificar el código del algoritmo genético.

## Notas técnicas

- El editor usa `matplotlib` para la visualización interactiva
- Requiere `tkinter` para los diálogos de confirmación (puede funcionar sin él con confirmación por consola)
- El archivo de exclusiones es independiente de la configuración de semáforos optimizada
- Las exclusiones persisten entre ejecuciones hasta que se modifiquen o eliminen manualmente

## Solución de problemas

### No puedo hacer click en los nodos

- Ajusta el zoom del mapa para ver mejor los nodos
- Los nodos muy pequeños pueden ser difíciles de seleccionar
- Intenta hacer click directamente sobre el marcador verde/rojo

### Los cambios no se guardan

- Asegúrate de presionar `s` antes de cerrar
- Verifica que tengas permisos de escritura en el directorio de salida
- Usa `--auto-save` para guardar automáticamente al salir

### El editor no se abre

- Verifica que tienes `matplotlib` instalado: `pip install matplotlib`
- Si estás en un entorno sin GUI, el editor no funcionará
- Puedes editar el JSON de exclusiones manualmente si es necesario
