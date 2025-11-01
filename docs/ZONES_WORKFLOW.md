# Zona a Simulación: Guía Rápida

Sigue estos pasos para definir zonas sobre el microcentro, generar la matriz O-D y ejecutar una simulación que use esa demanda.

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

## 3. Ejecutar la simulación

```bash
python examples/run_microcentro_od.py \
  --zones data/O-D-maps/microcentro_zones.json \
  --od data/O-D-maps/microcentro_zones_matrix.json \
  --save-prefix data/runs/microcentro \
  --animation-gif data/runs/microcentro_anim.gif \
  --attraction-map data/runs/microcentro_attraction.png \
  --no-show
```

Parámetros útiles:
- `--scale`: convierte demanda en número de vehículos (ej. `0.01`).
- `--steps`: pasos de simulación.
- `--cell-length`, `--v-max`, `--p-slow`: parámetros del modelo Nagel-Schreckenberg.

## 4. Integrar nuevas zonas en otros scripts
- Usa `generador_od.load_zone_file(...)` para cargar zonas y factores.
- La matriz O-D es un dict anidado (`origen -> destino -> demanda`).
- `TrafficSimulation.spawn_from_od_matrix(...)` crea vehículos basados en la matriz.

## 5. Consejos rápidos
- Producción = viajes que salen de la zona (orígenes).
- Atracción = viajes que llegan a la zona (destinos).
- Las zonas pueden editarse en cualquier momento desde el mismo editor; cada cambio se guarda automáticamente.
- Para versiones alternativas, guarda archivos con otros nombres dentro de `data/O-D-maps/` y referencia esos paths en los comandos anteriores.
