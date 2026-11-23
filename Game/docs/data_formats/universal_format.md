# Universal tag format

All observed game `.txt` data files are line-oriented tag/value data parsed by `engine/parsing/tag_parser.py`.

```text
object.type,"map_tile"
object.id,"definition.map.tile.open_water"
object.version,"1"

tile.name,"Open Water"
tile.category,"terrain"
tile.terrain_type,"water"
tile.color,"#315b78"
tile.image,"maps/tiles/open_water.svg"
```

## Syntax

| Rule | Actual behavior |
|---|---|
| Entry | Exactly two CSV fields per nonblank, noncomment line: tag and value. |
| Quoting | Project convention is `tag,"value"`. CSV syntax is used; parser does not require quotes around values. |
| Commas | A comma inside a quoted value is preserved. Escape a quote by doubling it (`""`). |
| Whitespace | Tag is stripped; value is kept as CSV-decoded, including surrounding spaces inside quotes. |
| Blank lines | Ignored. |
| Comments | A line whose trimmed beginning is `#` is ignored. Inline comments are not special. |
| Encoding | UTF-8, with an optional UTF-8 BOM. |
| Ordering | Entries retain order. No general order requirement is imposed by the parser. |
| Repeated tags | Preserved. `get(tag)` and `to_dict()` use the last value; `get_all(tag)` returns all. |

Tags are dotted namespaces by convention, such as `arena.dimensions.width` or `region.tile.moss.weight`. This parser treats a tag as an opaque string; it does not enforce a namespace schema.

## Universal metadata

Definitions and registries commonly begin with:

```text
object.type,"..."
object.id,"..."
object.version,"1"
```

`object.type` selects an object format where a specialized consumer exists. IDs are strings and references use those IDs as values. `object.version` is stored as text; no general version migration or semantic version validation was found. Do not change an existing ID casually: registries and arena references point to it.

## Conversion

The universal parser returns strings. Consumers convert values themselves. The entity parser converts selected numeric tags to integers and the legacy `settings.persistent` tag to a boolean (`true/1/yes`, `false/0/no`, case-insensitive). `settings.hardcore` is currently stored as an untyped string in `extra_tags` for later implementation. The arena renderer converts dimensions, coordinates, seeds, border width, weights and spread settings where used. Invalid conversions can raise errors at consumption time. Empty or absent optional values are often handled by consumer-specific defaults; there is no universal null syntax.

## Duplicate behavior and repeated relationships

Repeated tags are appropriate where the consumer calls `get_all`, including `arena.region` and `arena.location` references. For scalar tags, duplicates can silently resolve to the last value in `get`. Avoid duplicate scalar tags because parser acceptance does not mean the format intends them.
