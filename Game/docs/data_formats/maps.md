# Maps

Arena data is split among an arena definition, region definitions, location definitions, tile definitions, and map registry files. The renderer is `engine/maps/arena_renderer.py`; `RegistryManager` supplies the registered definitions. Keep region-specific tile generation values inside each region definition.

## Arena definition

Definitions are under `data/definitions/maps/arenas/`; registry entries are in the arenas registry. The arena definition references region and location definitions by full definition ID. Repeated `arena.region` and `arena.location` tags are expected.

```text
object.type,"map_arena"
object.id,"definition.map.arena.example"
object.version,"1"
arena.name,"Example Arena (15x15)"
arena.description,"A sample map."
arena.dimensions.width,"15"
arena.dimensions.height,"15"
arena.generation.seed,"1234"
arena.generation.enabled,"true"
arena.fallback_region,"definition.map.region.example_outer"
arena.region,"definition.map.region.example_clearing"
arena.location,"definition.map.location.example_cache"
arena.border.width,"1"
arena.border.type,"forest"
arena.border.name,"Arena Perimeter"
arena.border.tile,"arena_edge"
```

The renderer accepts dimensions 1–100, seed 0–4294967295, and border width 0–20. It reads dimensions from `arena.dimensions.height/width`, falling back to `arena.generation.rows/columns`, then 15. `arena.generation.enabled` controls whether the map appears in the list. Region entries and locations are read with repeated-value access. Border fields are optional; a border tile must be registered if width is positive.

## Regions and dynamic shapes

Region definitions are under `data/definitions/maps/regions/`. A region uses `object.type,"map_region"` and tags such as `region.name`, `region.type`, `region.priority`, `region.enabled`, `region.fallback`, and `region.shape`.

The shape language is a semicolon-separated list of inclusive rectangles in `row,column-row,column` form:

```text
region.shape,"2,1-2,2;3,1-3,3"
```

Coordinates are 1-based and must fit the arena dimensions. Reversed ranges and malformed segments fail when rendered. Overlap is resolved by lower numeric priority first, then region ID. Fallback fills uncovered playable cells. The selected fallback must be enabled and marked `region.fallback`.

Tile-generation profiles stay in the region file:

```text
region.tile.pine_floor.weight,"5"
region.tile.pine_floor.spread_chance,"0.75"
region.tile.pine_floor.spread_decay,"0.82"
region.tile.open_water.weight,"2"
region.tile.open_water.spread_chance,"0.60"
region.tile.open_water.spread_decay,"0.70"
```

Weights are relative and need not sum to a target. A tile is selected by weighted choice without replacement; each tile type seeds at most one patch for that region. For a patch, the renderer's spread chance at generation `n` is clamped base chance multiplied by clamped decay raised to `n`. Spread values are intentionally modest so patches stay small and leave varied ground between them. If the region exhausts its tile choices while cells remain, those cells use the arena's climate-specific wilds palette; any final gaps in the wilds fill use its last selected wild tile. The same seeded random generator controls tile choices and equal-priority region overlaps, so a seed remains repeatable. Every region needs at least one usable positive weight pointing to a registered tile.

## Special locations

Location definitions are under `data/definitions/maps/locations/` and use `object.type,"map_location"`. Relevant tags are `location.enabled`, `location.name`, `location.type`, `location.position.row`, `location.position.column`, `location.tile`, `location.symbol`, and `location.description`.

Locations are referenced by the arena definition. Coordinates are 1-based and must be within the playable dimensions. Location tiles resolve through the tile registry. Disabled locations are skipped. The renderer builds a location dictionary keyed by coordinate; multiple enabled locations at the same coordinate overwrite earlier entries. No independent location validator was found.

## Tiles and images

Tile definitions live under `data/definitions/maps/tiles/`; registrations are in the map tiles registry. Observed fields include `tile.name`, `tile.category`, `tile.terrain_type`, `tile.color`, `tile.elevation`, `tile.movement_difficulty`, `tile.image`, and `tile.default_overlays`. Elevation is an integer relative tier with 0 near sea level, negative values below sea level, and larger positive values for higher ground. Movement difficulty uses 1 (easy) through 10 (extremely difficult); 0 on object tiles means the overlay itself does not define a terrain movement cost. The renderer uses name/category/terrain type/color/image/overlays for its view model. A location tile with category `object` is rendered as an object overlay; terrain-category location tiles replace displayed terrain.

Images are explicitly assigned with `tile.image` and resolved under `data/assets/`. For example, `maps/tiles/open_water.svg` resolves to `data/assets/maps/tiles/open_water.svg`. The renderer does not search or auto-discover textures. Paths must be relative and may not contain `..`; the file must exist to produce an image URL. A missing image leaves the tile without an image URL and the color remains available as fallback. SVG is present in project data, but the implementation does not establish a complete supported-format or dimension contract.

No movement, visibility, or noise modifiers were found in the tile renderer's consumed fields; do not add such tags expecting current map rendering to use them.
