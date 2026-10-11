# Maintenance Hub

Preventive maintenance tracking for Home Assistant: equipment (boiler, heat pump, air conditioning), IT and network (NAS, router, home automation), and vehicles (motorcycles, cars, bicycles).

> **Status: early development.** The repository currently contains the integration skeleton and the first maintenance templates. Sensors, the "done" button and services are not implemented yet.

## Features (planned for the MVP)

- Assets with a category: `equipment`, `it`, `vehicle`.
- Maintenance tasks defined by **templates** in YAML, so anyone can contribute a new asset type without touching code.
- Triggers by **time** (every N days or months), by **distance** (km, for vehicles) and by **hours** of operation.
- Per-task sensors for time or km remaining, and an "overdue" binary sensor.
- A button to mark a task as done, which resets the counter.
- An odometer service for vehicles, so no external sensor is needed.
- English and Spanish interface.

## Installation (HACS)

1. In HACS, go to **⋮ → Custom repositories**.
2. Add `https://github.com/Rodaballoso/ha-maintenance-hub` with category **Integration**.
3. Install **Maintenance Hub** and restart Home Assistant.

## Templates

Templates live in `custom_components/maintenance_hub/templates/`. Each file describes one asset type:

```yaml
asset_type: motorcycle
category: vehicle
name: Motorcycle
name_es: Moto
tasks:
  - id: oil_change
    name: Oil change
    name_es: Cambio de aceite
    trigger: { km: 6000, months: 12 }
```

Templates shipped so far: boiler, NAS and motorcycle.

## Contributing

Templates are the easiest contribution: add a YAML file with the tasks and intervals for your device or vehicle. Open an issue or a pull request.

## License

MIT. See [LICENSE](LICENSE).

---

# Maintenance Hub (español)

Seguimiento de mantenimiento preventivo para Home Assistant: equipamiento (caldera, calentador, aire acondicionado, clima), informática y red (NAS, router, domótica) y vehículos (motos, coches, bicicletas).

> **Estado: en desarrollo temprano.** El repositorio contiene de momento el esqueleto de la integración y las primeras plantillas de mantenimiento. Sensores, botón de "hecho" y servicios aún no están implementados.

## Funcionalidades previstas (MVP)

- Activos con categoría: `equipment`, `it`, `vehicle`.
- Tareas de mantenimiento definidas con **plantillas** en YAML, para que cualquiera pueda aportar un nuevo tipo de activo sin tocar código.
- Disparadores por **tiempo** (cada N días o meses), por **distancia** (km, para vehículos) y por **horas** de funcionamiento.
- Sensores por tarea con el tiempo o los km restantes, y un sensor binario de "vencida".
- Botón para marcar una tarea como hecha, que reinicia el contador.
- Servicio de odómetro para vehículos, sin necesidad de sensores externos.
- Interfaz en inglés y español.

## Instalación (HACS)

1. En HACS, ve a **⋮ → Custom repositories**.
2. Añade `https://github.com/Rodaballoso/ha-maintenance-hub` con categoría **Integration**.
3. Instala **Maintenance Hub** y reinicia Home Assistant.

## Plantillas

Las plantillas están en `custom_components/maintenance_hub/templates/`. Cada fichero describe un tipo de activo (ver el ejemplo de arriba). Plantillas incluidas por ahora: caldera, NAS y moto.

## Contribuir

La forma más fácil de contribuir es añadir una plantilla YAML con las tareas y los intervalos de tu equipo o vehículo. Abre un issue o un pull request.

## Licencia

MIT. Ver [LICENSE](LICENSE).
