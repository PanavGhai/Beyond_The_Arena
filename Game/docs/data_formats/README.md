# Data format guides

These guides describe the formats evidenced by the current project files and engine code. The `.txt` data uses CSV-style tag/value lines; the guides distinguish what parses from what validates or renders. Empty registries and files are listed in [planned_families.md](planned_families.md) with a ready-to-reuse prompt. Do not infer their object schemas from their filenames.

## Guides

- [Universal tags and metadata](universal_format.md)
- [Registries and references](registries.md)
- [Entities and tribute sheets](entities.md)
- [Arenas, regions, locations, and tiles](maps.md)
- [Game saves, entity layouts, and Sectors](game_saves.md)
- [Validation and implementation status](validation.md)
- [Families awaiting data](planned_families.md)

Per-family placeholders with a scoped regeneration prompt are in [`planned/`](planned/): actions, anatomy, capabilities, classifications, conditions, effects, events, factions, injuries, items, options, relationships, species, statuses, traits, and arenas.

## Current data inventory

At inspection, `data/` contained 396 `.txt` files: 362 nonempty, parseable files and 34 empty files. All nonempty files parsed with the project's tag parser and had `object.type`, `object.id`, and `object.version`. Populated definition families were attributes (6), skills (10), personality facets (50), personality values (16), map arenas (9), map tiles (66), map regions (87), map locations (60), and entities (6). Counts are an inspection snapshot, not a runtime guarantee.

## Authority

Examples and support statements are based on `engine/parsing/`, `engine/registries/`, `engine/validation/`, `engine/maps/arena_renderer.py`, and the data currently present. The older [`Parsing_System.md`](../Parsing_System.md) overlaps but should be checked against current code where it differs.
