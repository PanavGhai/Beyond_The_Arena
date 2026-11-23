# Game saves and setup workflow

This guide covers the Play screen, map selection, Sectors, and per-save entity files in `Beyond_The_Arena/Game`. Save data is written as quoted tag-value `.txt` files and read with the existing tag parser. The browser uses ordinary controls; players never need to type tag syntax. The server translates form fields into tags when saving and parses tags back into the controls when reopening a save.

## Player workflow

1. The Play link opens `/play`, which lists valid save folders.
2. Create a save with an optional name, or open/delete an existing save.
3. A new save opens the combined arena and Sectors screen, initialized from `game_setup.default_arena` in `data/config/game_saves.txt`.
4. Preview the full arena beside its tile inspector. Change the arena or numeric/text seed and refresh the preview without leaving the page. Lock the chosen arena and seed, or unlock it later to keep experimenting.
5. Choose Sectors and assign Tributes with dropdowns and add/remove controls below the map preview.
6. Saving Sectors completes the current setup flow. There is no start-game, NPC-roll, loot-roll, or simulation step in this flow.

The current setup role, limits, labels, defaults, and save capacity are editable in `data/config/game_saves.txt`. The default limits are 1–64 Sectors and 1–64 members per Sector. Each Tribute is unique across the save while `game_setup.members.unique_per_game` is true. The initial number of Sectors is reduced to fit the available roster and configured default member count.

## Save folders

Save folders live under `data/saves/`; they are runtime state, so individual saves are discovered by scanning folders and are not placed in a static content registry.

```text
data/saves/game_001/
  save.txt
  sectors.txt
  entities/
    tributes/
      tribute_001/
        tributes_001.txt
        skills.txt
        personality/
          facets.txt
          values.txt
        effective/
          stats.txt
          bonuses.txt
        traits.txt
        statuses.txt
    npcs/
    mentors/
    sponsors/
    wildlife/
```

The original entity file is copied byte-for-byte into its save folder and is not edited by setup. The companion files hold save-local mutable data. Skills, personality facets, and values are copied into separate tag files. Effective stats, effective bonuses, traits, and statuses begin as valid tag documents with their metadata; later systems can populate their data groups. Empty role folders are created from the registered role layouts for future use.

## Save metadata tags

`save.txt` identifies one save and stores its selected map:

```text
"object.type","game_save"
"object.id","save.game_001"
"object.version","1"
"save.id","game_001"
"save.name","Winter Run"
"save.status","setup_complete"
"save.map.locked","true"
"save.created_at","2026-11-23T10:00:00+00:00"
"save.updated_at","2026-11-23T10:05:00+00:00"
"save.map.id","forest_arena_15x15"
"save.map.seed","4253997220"
```

The map ID refers to an entry in `data/registries/maps/arenas.txt`. The seed is normalized to a 32-bit number by the existing arena seeding helper; re-rendering uses that map ID and seed. `save.map.locked` persists whether the player has confirmed the current map; unlocking allows another preview and updates the same save when locked again. Editing a map definition can therefore change a map in an older save.

## Sector and member tags

The friendly Sectors form submits `sector_count` and fields such as `sector_001_member_001`. Those are UI field names only. The browser saves in place; after a successful save, compact Sector cards show member names and nicknames, and **Edit** reopens the controls. `GameSaveManager` validates the values, then writes them to `sectors.txt`:

```text
"object.type","game_sectors"
"object.id","save.game_001.sectors"
"object.version","1"
"save.sectors.count","2"
"save.sectors.001.name","Sector 1"
"save.sectors.001.members.count","2"
"save.sectors.001.member.001.entity_id","entity.tribute.001"
"save.sectors.001.member.002.entity_id","entity.tribute.002"
"save.sectors.002.name","Sector 2"
"save.sectors.002.members.count","1"
"save.sectors.002.member.001.entity_id","entity.tribute.003"
```

All tag values are text and are serialized with quotes. Sector numbers and member numbers are zero-padded to three digits. The parser reads these tags to restore the roster controls. Invalid ranges, missing members, unknown entity IDs, and duplicate Tribute assignments are rejected before saving.

Successful browser saves return Sector and member display data as JSON so the page can update without navigation or a reload. JSON is only a presentation response; the `.txt` tag files remain authoritative. The map inspector includes an in-page activity panel for setup actions; it is not persisted as game history.

## Editable per-role save layouts

The role-to-layout registry is `data/registries/saves/entity_layouts.txt`. Each role entry points to a definition under `data/definitions/saves/entity_layouts/`. `GameSaveManager` reads this registry directly and resolves the definitions through `RegistryManager`; it does not add a new family to the manager's existing registry dictionary.

Each layout definition includes:

- `save.layout.directory` — the role folder under a save, such as `entities/tributes`.
- `save.layout.entity_directory_pattern` — the per-entity folder name, with placeholders such as `{number}`.
- `save.layout.file.NNN.path` — relative file path; `{source_filename}` copies the exact original filename.
- `save.layout.file.NNN.kind` — `snapshot`, `group`, or `empty`.
- `save.layout.file.NNN.source_prefix` — source tag prefix for a copied group.
- `save.layout.file.NNN.group_name` — group identifier written into companion-file metadata.

`snapshot` copies the source `.txt` file unchanged. `group` creates a tag document containing its metadata and all source tags with the configured prefix. `empty` creates a tag document with metadata ready for future runtime values. Paths are checked to remain under the save folder.

To add a role, register it in `data/registries/entities/roles.txt`, add its layout entry to `entity_layouts.txt`, and create its layout definition. Every registered role must have exactly one valid save layout before saves can be created. Add or remove file entries in the definition to change the role's generated save structure; no Python file layout list needs editing.

## Save manager and safety

`engine/saves/manager.py` handles save discovery, creation, map selection, sector validation, entity snapshots, and deletion. Writes go to a sibling temporary file and replace the previous `.txt` file atomically. The save ID must match the configured folder prefix and numeric ID pattern before a path is accessed. The save count, folder prefix, filenames, and storage directory are read from tag settings.

Deleting a save removes that save folder, including its entity snapshots. No save files are created in `static/`, and the reference GameDev JSON save format is not used by this project.
