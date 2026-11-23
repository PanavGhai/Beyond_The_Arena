# Validation and implementation status

This page separates parsing from later interpretation. A file being parseable does not mean every tag is validated or used.

| Status | Meaning |
|---|---|
| Implemented | A runtime consumer reads or acts on the data. |
| Parsed | A parser converts or stores the value. |
| Validated | A validator or consumer explicitly checks it. |
| Frontend/rendering | Used to build a page or map presentation. |
| Convention | Used consistently in data but not comprehensively enforced. |
| Planned / gap | Placeholder exists or requested feature has no evidence of current implementation. |
| Unknown | Code/data inspected did not establish behavior. |

## Current checks

- Universal parser: UTF-8-sig CSV rows, exactly two fields, nonempty tag; blank lines and leading-`#` comments ignored. Duplicate tags are allowed and preserved.
- Registry manager: parseable definitions are indexed by ID; duplicate definition IDs raise. Registry files need `object.type="registry"`; conflicting duplicate names raise. Missing registry target definitions are not rejected while loading; resolution returns `None`.
- Entity validator: requires nonempty `object.type`, `object.id`, `object.version`, `entity.role`, `entity.name`; object type must be entity. Validates registered roles, species, attributes, skills, personality facets and values. Character-creation validation additionally checks identity limits and allocation budgets.
- Arena renderer: validates dimensions, seed, shapes and region coverage/fallback, usable tile weights, location coordinates and tile references, plus border width/tile. These checks happen when maps are listed/rendered; no separate map-data validator was found.

## Field support guide

| Data | Parsed | Validated | Runtime use |
|---|---|---|---|
| Entity identity and common fields | Yes, entity parser | Required fields subset | Structured Entity; additional use depends on caller. |
| Entity statistic groups | Yes, integer conversion | Registration, whole number, limits | Stored in Entity model. |
| Unknown entity tags | Kept in `extra_tags` | No | No general consumer established. |
| Registry tags | Yes, registry manager | File type and conflicting duplicate keys | Provides short-name to definition-ID lookup. |
| Arena dimensions/seed | Renderer reads and converts | Range limits | Generates deterministic arena grid. |
| Region shape, priority, fallback | Renderer reads | Syntax, bounds, coverage/fallback; overlaps ordered | Selects cells assigned to each region. |
| Region tile weights/spread | Renderer reads | Positive usable weight required; values converted | Chooses/grows terrain patches. |
| Map locations | Renderer reads | Coordinate bounds and registered tile | Adds location presentation on the map. |
| Tile image/color/name/category | Renderer reads | Image path existence gates URL | Builds map display view model. |
| Empty families listed in planned guide | No populated examples | Unknown | No support inferred. |

## Important limits

There is no general schema validator for arbitrary object types. `ObjectDispatcher` currently registers only `entity`; maps are consumed directly by the arena renderer. Several registries are empty and are not supported families in `RegistryManager`. Frontend-visible fields do not prove simulation behavior. See [planned_families.md](planned_families.md) for files needing future data-driven documentation.
