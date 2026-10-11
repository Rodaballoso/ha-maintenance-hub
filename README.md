# Maintenance Hub

Preventive maintenance tracking for Home Assistant: equipment (boiler, heat pump, air conditioning), IT and network (NAS, router, home automation), and vehicles (motorcycles, cars, bicycles).

> **Status: early development (MVP, not yet tested in a live Home Assistant).** Assets, time and distance triggers, remaining sensors, overdue flags, the "done" button and services are implemented. Hour-based triggers are not implemented yet.

## Features

- Assets with a category: `equipment`, `it`, `vehicle`.
- Maintenance tasks created from **templates** in YAML, so anyone can contribute a new asset type without touching code.
- Triggers by **time** (every N days or months) and by **distance** (km, for vehicles).
- Per task: a sensor with the remaining days (or km), a sensor for "overdue", and a button to mark it as done.
- Services: `add_asset`, `remove_asset`, `mark_done` and `set_odometer`.
- Each asset is a Home Assistant device, so its entities are grouped under it.
- Entity names follow the Home Assistant language (English or Spanish).

## Usage

Create an asset from a template with the `maintenance_hub.add_asset` service. The asset id is written to the Home Assistant log and appears in the attributes of its entities. Use it with `maintenance_hub.mark_done` and `maintenance_hub.set_odometer`.

Setup is done from the UI: **Settings → Devices & services → Add integration → Maintenance Hub**. Only one instance is allowed. Assets are then managed with services.

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

> **Estado: desarrollo temprano (MVP, aún sin probar en un Home Assistant real).** Están implementados los activos, los disparadores por tiempo y por distancia, los sensores de restante, el indicador de vencida, el botón de "hecho" y los servicios. Los disparadores por horas todavía no están implementados.

## Funcionalidades

- Activos con categoría: `equipment`, `it`, `vehicle`.
- Tareas de mantenimiento creadas desde **plantillas** en YAML, para que cualquiera pueda aportar un nuevo tipo de activo sin tocar código.
- Disparadores por **tiempo** (cada N días o meses) y por **distancia** (km, para vehículos).
- Por tarea: un sensor con los días (o km) restantes, un sensor de "vencida" y un botón para marcarla como hecha.
- Servicios: `add_asset`, `remove_asset`, `mark_done` y `set_odometer`.
- Cada activo es un dispositivo de Home Assistant, así que sus entidades aparecen agrupadas bajo él.
- Los nombres de las entidades siguen el idioma de Home Assistant (inglés o español).

## Uso

Crea un activo a partir de una plantilla con el servicio `maintenance_hub.add_asset`. El id del activo se escribe en el registro de Home Assistant y aparece en los atributos de sus entidades. Con ese id usas `maintenance_hub.mark_done` y `maintenance_hub.set_odometer`.

La integración se añade desde la interfaz: **Ajustes → Dispositivos y servicios → Añadir integración → Maintenance Hub**. Solo se permite una instancia. Los activos se gestionan después con servicios.

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
