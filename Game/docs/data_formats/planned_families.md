# Data families awaiting populated examples

These files are currently zero bytes. Their intended families can be read from their directories or filenames, but there is not enough data or engine support to specify a complete format. Keep them listed until examples and consumer behavior exist; do not copy schemas from similarly named concepts.

## Empty paths found

- `data/registries/actions/combat.txt`, `crafting.txt`, `general.txt`, `survival.txt`, `tools.txt`
- `data/registries/capabilities/combat.txt`, `crafting.txt`, `general.txt`, `survival.txt`, `tools.txt`
- `data/registries/classifications/combat.txt`, `general.txt`, `items.txt`
- `data/registries/conditions/conditions.txt`
- `data/registries/effects/capabilities.txt`, `restrictions.txt`, `special.txt`, `stat_modifiers.txt`
- `data/registries/events/arena.txt`, `encounters.txt`, `sponsor.txt`, `weather.txt`
- `data/registries/factions/factions.txt`
- `data/registries/injuries/injuries.txt`
- `data/registries/items/consumables.txt`, `equipment.txt`, `materials.txt`, `resources.txt`, `tools.txt`, `weapons.txt`
- `data/registries/options/other.txt`
- `data/registries/relationships/relationships.txt`
- `data/registries/species/species.txt`
- `data/registries/statuses/statuses.txt`
- `data/registries/traits/traits.txt`

Map arena definitions are now documented in [maps.md](maps.md) and stored under `data/definitions/maps/arenas/`. The map arena registry is `data/registries/maps/arenas.txt`.

The empty `data/registries/options/districts.txt` was removed. Sectors are generated per game save and stored in `sectors.txt`; they are not a character identity option registry.

## Follow-up prompt

When these data files are populated, provide this guide together with the updated project and ask:

> Reinspect the listed data family files, the current parser, registry manager, validators, and runtime consumers. Rewrite this Markdown guide from actual populated examples and implementation. Document the exact paths, IDs, tags, value formats, references, validation, and runtime use. Keep unsupported behavior marked as planned or unknown. Preserve the universal tag-value conventions and do not invent data or alter engine architecture. Confirm all paths reviewed and list remaining empty files.

For one family, replace “listed data family files” with the exact folder and filenames above so the guide stays scoped.
