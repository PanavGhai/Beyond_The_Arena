# Registries and references

## What a registry does

A registry maps a short lookup name to a definition ID. It is not the definition and does not contain the object's properties. Registry files live under `data/registries/`; definitions live under `data/definitions/`. The current `RegistryManager` indexes definitions recursively by `object.id`, then loads supported families.

Example map registry form:

```text
object.type,"registry"
object.id,"registry.maps.arenas"
object.version,"1"

map.arena.forest_arena_15x15,"definition.map.arena.forest_arena_15x15"
```

The loader ignores `object.*` and `settings.*` tags. For other tags, it uses the final dotted segment as the lookup name and the value as definition ID. Files are recursively loaded under family directories; map registries are selected by filename (`arenas.txt`, `regions.txt`, `locations.txt`, `tiles.txt`).

## Supported families

`RegistryManager` currently initializes and loads `attributes`, `skills`, `facets`, `values`, `arenas`, `regions`, `locations`, `tiles`, `body_parts`, `species`, and `roles`. Personality facets and values share `data/registries/personality/`; map families share `data/registries/maps/`. The save entity-layout registry is read by `GameSaveManager` directly and its targets are resolved through the manager's definition index; it is intentionally not added as a new `RegistryManager` family.

## Resolving references

`RegistryManager` indexes each parseable file under `data/definitions/**/*.txt` by its `object.id`. A duplicate definition ID raises an error. A registry lookup returns its definition ID; `resolve_definition(id)` returns the parsed document or `None` when the ID is not indexed. Registry loading does not verify that each target definition exists, so check both ends when adding an entry.

Common connections:

- Entity statistic name → registry family (`attributes`, `skills`, `facets`, `values`) → definition ID.
- Arena definition → repeated region/location definition IDs.
- Region tile name → tile registry entry → tile definition.
- Map border and special location tile name → tile registry entry.
- Save role → `data/registries/saves/entity_layouts.txt` → role-specific save layout definition.

The current engine does not demonstrate registry connections for empty action, item, event, faction, or other placeholder families; see [planned families](planned_families.md).

## Safe addition checklist

1. Add a definition with unique `object.id` and correct `object.type`.
2. Add a registry tag whose final segment is the intended lookup key and whose value is the exact definition ID.
3. Use the family/file names already loaded by `RegistryManager`.
4. Check for duplicate short names and duplicate definition IDs.
5. Confirm consumer-specific references use the expected short key or full definition ID; map arena region/location fields use definition IDs.
