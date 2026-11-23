"""Load registered arena definitions and build view models for the web UI."""

from collections import deque
from pathlib import Path
import random
import re

from engine.maps.seeding import normalize_seed
from engine.registries.registry_manager import RegistryManager


class ArenaRenderer:
    """Resolve map tags into the grid and card data consumed by the HTML pages."""

    def __init__(self, project_root, asset_url=None):
        self.project_root = Path(project_root)
        self.registries = RegistryManager(self.project_root)
        self.asset_url = asset_url or (lambda name: "/" + name.lstrip("/"))
        self.tile_catalog = {}
        self._load_tiles()

    @staticmethod
    def _enabled(value, default=True):
        if value is None:
            return default
        return value.strip().lower() in {"true", "1", "yes", "on"}

    @staticmethod
    def _tile_id(reference):
        return (reference or "").rsplit(".", 1)[-1]

    @staticmethod
    def _nice_name(value):
        return (value or "").replace("_", " ").title()

    def _load_tiles(self):
        for tile_id, definition_id in self.registries.get_registered_entries("tiles").items():
            document = self.registries.resolve_definition(definition_id)
            if document is None or document.get("object.type") != "map_tile":
                continue
            image = document.get("tile.image", "")
            image_url = None
            image_path = Path(image.replace("\\", "/")) if image else None
            if image_path and not image_path.is_absolute() and ".." not in image_path.parts:
                image_file = self.project_root / "data" / "assets" / image_path
                if image_file.is_file():
                    image_url = self.asset_url(image_path.as_posix())
            overlays = [part.strip() for part in (document.get("tile.default_overlays") or "").split(";") if part.strip()]
            self.tile_catalog[tile_id] = {
                "id": tile_id,
                "name": document.get("tile.name", self._nice_name(tile_id)),
                "category": document.get("tile.category", "terrain"),
                "terrain_type": document.get("tile.terrain_type", ""),
                "color": document.get("tile.color", "#45634a"),
                "elevation": int(document.get("tile.elevation", "0")),
                "movement_difficulty": int(document.get("tile.movement_difficulty", "0")),
                "image_url": image_url,
                "overlays": overlays,
            }

    def list_arenas(self):
        maps = []
        for map_id, definition_id in self.registries.get_registered_entries("arenas").items():
            document = self.registries.resolve_definition(definition_id)
            if document is None or document.get("object.type") != "map_arena":
                continue
            if not self._enabled(document.get("arena.generation.enabled"), True):
                continue
            maps.append({
                "id": map_id,
                "name": document.get("arena.name", self._nice_name(map_id)),
                "description": document.get("arena.description", ""),
                "rows": int(document.get("arena.dimensions.height", document.get("arena.generation.rows", "15"))),
                "columns": int(document.get("arena.dimensions.width", document.get("arena.generation.columns", "15"))),
                "border_width": int(document.get("arena.border.width", "0")),
                "border_type": document.get("arena.border.type", ""),
                "definition_id": definition_id,
            })
        return sorted(maps, key=lambda item: (item["name"].casefold(), item["id"]))

    def _region(self, definition_id, order):
        document = self.registries.resolve_definition(definition_id)
        if document is None or document.get("object.type") != "map_region":
            raise ValueError(f"Map references an unavailable region: {definition_id}")
        object_id = document.get("object.id", definition_id)
        tile_weights = {}
        for entry in document.entries:
            match = re.fullmatch(r"region\.tile\.([^.]+)\.(weight|spread_chance|spread_decay)", entry.tag)
            if match:
                tile_id, field = match.groups()
                tile_weights.setdefault(tile_id, {})[field] = float(entry.value)
        weights = [
            {
                "tile_id": tile_id,
                "weight": values.get("weight", 0),
                "spread_chance": values.get("spread_chance", 0.7),
                "spread_decay": values.get("spread_decay", 0.8),
            }
            for tile_id, values in tile_weights.items()
            if values.get("weight", 0) > 0 and tile_id in self.tile_catalog
        ]
        if not weights:
            raise ValueError(f"Region has no usable registered tile weights: {definition_id}")
        return {
            "id": object_id.rsplit(".", 1)[-1],
            "name": document.get("region.name", self._nice_name(object_id.rsplit(".", 1)[-1])),
            "type": document.get("region.type", ""),
            "priority": int(document.get("region.priority", "999")),
            "enabled": self._enabled(document.get("region.enabled"), True),
            "fallback": self._enabled(document.get("region.fallback"), False),
            "shape": document.get("region.shape", ""),
            "weights": weights,
            "order": order,
        }

    @staticmethod
    def _shape_cells(shape, rows, columns):
        cells = set()
        for segment in filter(None, (part.strip() for part in shape.split(";"))):
            match = re.fullmatch(r"(\d+)\s*,\s*(\d+)\s*-\s*(\d+)\s*,\s*(\d+)", segment)
            if not match:
                raise ValueError(f"Invalid region shape: {segment}")
            row1, column1, row2, column2 = map(int, match.groups())
            if row2 < row1 or column2 < column1:
                raise ValueError(f"Invalid region range: {segment}")
            if row1 < 1 or column1 < 1 or row2 > rows or column2 > columns:
                raise ValueError(f"Region shape is outside map dimensions: {segment}")
            cells.update((row, column) for row in range(row1, row2 + 1) for column in range(column1, column2 + 1))
        return cells

    @staticmethod
    def _weighted_choice(rng, weights):
        return rng.choices(weights, weights=[item["weight"] for item in weights], k=1)[0]

    def _grow_region(self, rng, cells, weights, fallback_weights=None):
        """Pick relative tile weights without replacement, then grow each patch."""
        unassigned = set(cells)
        assigned = {}
        available = list(weights)
        neighbours = ((-1, 0), (1, 0), (0, -1), (0, 1))
        last_tile_id = None

        while unassigned and available:
            # Weights determine a weighted order. Once picked, a tile type is
            # removed from this region's pool and cannot seed another patch.
            chosen = self._weighted_choice(rng, available)
            available.remove(chosen)
            last_tile_id = chosen["tile_id"]
            seed = rng.choice(tuple(unassigned))
            unassigned.remove(seed)
            assigned[seed] = last_tile_id
            frontier = deque([(seed, 0)])

            while frontier:
                (row, column), generation = frontier.popleft()
                chance = max(0.0, min(1.0, chosen["spread_chance"])) * (max(0.0, chosen["spread_decay"]) ** generation)
                candidates = [
                    (row + dr, column + dc)
                    for dr, dc in neighbours
                    if (row + dr, column + dc) in unassigned
                ]
                rng.shuffle(candidates)
                for cell in candidates:
                    if cell in unassigned and rng.random() <= chance:
                        unassigned.remove(cell)
                        assigned[cell] = last_tile_id
                        frontier.append((cell, generation + 1))

        # Exhausted biome patches hand unclaimed cells to this arena's
        # climate-specific wilds palette. Wilds themselves finish with their
        # final seeded tile if their own patches leave any gaps.
        if unassigned and fallback_weights:
            assigned.update(self._grow_region(rng, unassigned, fallback_weights))
        elif last_tile_id is not None:
            for cell in unassigned:
                assigned[cell] = last_tile_id
        return assigned
    def render_map(self, map_id, seed_override=None):
        map_entry = self.registries.get_definition("arenas", map_id)
        if map_entry is None or map_entry.get("object.type") != "map_arena":
            raise KeyError(map_id)

        rows = int(map_entry.get("arena.dimensions.height", map_entry.get("arena.generation.rows", "15")))
        columns = int(map_entry.get("arena.dimensions.width", map_entry.get("arena.generation.columns", "15")))
        if not 1 <= rows <= 100 or not 1 <= columns <= 100:
            raise ValueError(f"Map dimensions are outside the supported range: {rows}x{columns}")
        raw_seed = seed_override if seed_override is not None else map_entry.get("arena.generation.seed", "0")
        seed = normalize_seed(raw_seed)
        rng = random.Random(seed)

        regions = [
            self._region(definition_id, order)
            for order, definition_id in enumerate(map_entry.get_all("arena.region"))
        ]
        regions = [region for region in regions if region["enabled"] and not region["fallback"]]
        # Lower numeric priorities are placed first. Regions at the same
        # priority use the arena seed to choose winners for overlapping cells.
        ordered_regions = []
        for priority in sorted({region["priority"] for region in regions}):
            same_priority = [region for region in regions if region["priority"] == priority]
            rng.shuffle(same_priority)
            ordered_regions.extend(same_priority)
        regions = ordered_regions
        region_by_cell = {}
        for region in regions:
            region["cells"] = self._shape_cells(region["shape"], rows, columns)
            for cell in region["cells"]:
                region_by_cell.setdefault(cell, region)

        fallback_ref = map_entry.get("arena.fallback_region")
        fallback = self._region(fallback_ref, len(regions)) if fallback_ref else None
        if fallback and (not fallback["enabled"] or not fallback["fallback"]):
            raise ValueError("The referenced fallback region is not enabled as a fallback")
        for row in range(1, rows + 1):
            for column in range(1, columns + 1):
                region_by_cell.setdefault((row, column), fallback)
        if any(region is None for region in region_by_cell.values()):
            raise ValueError("Map regions do not cover the playable area and no fallback is defined")

        generated_tiles = {}
        wilds_weights = fallback["weights"] if fallback else None
        for region in regions:
            cells = {cell for cell, owner in region_by_cell.items() if owner["id"] == region["id"]}
            generated_tiles.update(self._grow_region(rng, cells, region["weights"], wilds_weights))
        if fallback:
            wilds_cells = {cell for cell, owner in region_by_cell.items() if owner["id"] == fallback["id"]}
            generated_tiles.update(self._grow_region(rng, wilds_cells, fallback["weights"]))

        locations = {}
        for order, definition_id in enumerate(map_entry.get_all("arena.location")):
            document = self.registries.resolve_definition(definition_id)
            if document is None or document.get("object.type") != "map_location":
                raise ValueError(f"Map references an unavailable location: {definition_id}")
            if not self._enabled(document.get("location.enabled"), True):
                continue
            row = int(document.get("location.position.row", "0"))
            column = int(document.get("location.position.column", "0"))
            if not (1 <= row <= rows and 1 <= column <= columns):
                raise ValueError(f"Location is outside map dimensions: {definition_id}")
            tile_id = self._tile_id(document.get("location.tile"))
            if tile_id not in self.tile_catalog:
                raise ValueError(f"Location references an unavailable tile: {tile_id}")
            locations[(row, column)] = {
                "id": document.get("object.id", definition_id).rsplit(".", 1)[-1],
                "name": document.get("location.name", self._nice_name(tile_id)),
                "type": document.get("location.type", "special_location"),
                "row": row,
                "column": column,
                "tile_id": tile_id,
                "symbol": document.get("location.symbol", "◆"),
                "description": document.get("location.description", ""),
            }

        border_width = int(map_entry.get("arena.border.width", "0"))
        if border_width < 0 or border_width > 20:
            raise ValueError(f"Border width is outside the supported range: {border_width}")
        border_tile_id = self._tile_id(map_entry.get("arena.border.tile"))
        if border_width and border_tile_id not in self.tile_catalog:
            raise ValueError(f"Border references an unavailable tile: {border_tile_id}")
        border_tile = self.tile_catalog.get(border_tile_id, {"id": border_tile_id, "name": "Border", "color": "#45634a", "elevation": 0, "movement_difficulty": 10})
        border_region = {
            "id": "border",
            "name": map_entry.get("arena.border.name", "Map Perimeter"),
            "type": map_entry.get("arena.border.type", ""),
        }

        display_rows = rows + border_width * 2
        display_columns = columns + border_width * 2
        grid = []
        for grid_row in range(1, display_rows + 1):
            row_cells = []
            for grid_column in range(1, display_columns + 1):
                row = grid_row - border_width
                column = grid_column - border_width
                playable = 1 <= row <= rows and 1 <= column <= columns
                if playable:
                    region = region_by_cell[(row, column)]
                    biome_id = generated_tiles[(row, column)]
                    special = locations.get((row, column))
                    display_id = special["tile_id"] if special else biome_id
                    display_tile = self.tile_catalog[display_id]
                    if special and display_tile["category"] == "terrain":
                        terrain_id = display_id
                    else:
                        terrain_id = biome_id
                    terrain_tile = self.tile_catalog[terrain_id]
                    objects = []
                    if special and display_tile["category"] == "object":
                        objects.append({
                            "id": special["id"],
                            "name": special["name"],
                            "tile_color": display_tile["color"],
                            "image_url": display_tile["image_url"],
                            "symbol": special["symbol"],
                        })
                    location_name = special["name"] if special else "Unmarked terrain"
                    coordinate = f"({row}, {column})"
                    region_id, region_name = region["id"], region["name"]
                else:
                    region, special = border_region, None
                    biome_id = terrain_id = display_id = border_tile_id
                    display_tile = terrain_tile = border_tile
                    objects = []
                    location_name = border_region["name"]
                    coordinate = f"Perimeter ({grid_row}, {grid_column})"
                    region_id, region_name = border_region["id"], border_region["name"]

                row_cells.append({
                    "row": row if playable else "",
                    "column": column if playable else "",
                    "grid_row": grid_row,
                    "grid_column": grid_column,
                    "coordinate": coordinate,
                    "playable": playable,
                    "tile_id": display_id,
                    "terrain_tile_id": terrain_id,
                    "terrain_name": terrain_tile["name"],
                    "terrain_color": terrain_tile["color"],
                    "elevation": terrain_tile["elevation"],
                    "movement_difficulty": terrain_tile["movement_difficulty"],
                    "terrain_image_url": terrain_tile["image_url"],
                    "biome_name": self.tile_catalog[biome_id]["name"],
                    "objects": objects,
                    "overlays": [],
                    "conditions": [],
                    "region_id": region_id,
                    "region_name": region_name,
                    "location_name": location_name,
                    "special": special,
                })
            grid.append(row_cells)

        return {
            "id": map_id,
            "name": map_entry.get("arena.name", self._nice_name(map_id)),
            "description": map_entry.get("arena.description", ""),
            "rows": rows,
            "columns": columns,
            "seed": seed,
            "grid_rows": display_rows,
            "grid_columns": display_columns,
            "border_width": border_width,
            "edge_width": border_width,
            "edge_region": border_region if border_width else None,
            "grid": grid,
            "regions": regions,
            "special_locations": list(locations.values()),
        }
