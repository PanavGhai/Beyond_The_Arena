"""Create, read, and update tag-based game setup saves."""

import csv
import io
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from engine.parsing.tag_parser import TagParserError, parse_file
from engine.registries.registry_manager import RegistryManager


class GameSaveManager:
    def __init__(self, project_root):
        self.project_root = Path(project_root).resolve()
        self.registries = RegistryManager(self.project_root)
        self.config = parse_file(self.project_root / "data" / "config" / "game_saves.txt")
        self.saves_root = self._configured_path("game_saves.storage_directory", "data/saves")
        self.save_filename = self.config.get("game_saves.save_filename", "save.txt")
        self.sectors_filename = self.config.get("game_saves.sectors_filename", "sectors.txt")
        for file_name in (self.save_filename, self.sectors_filename):
            if Path(file_name).name != file_name or not file_name.endswith(".txt"):
                raise ValueError("Save data filenames must be simple .txt filenames.")
        self.folder_prefix = self.config.get("game_saves.folder_prefix", "game_")
        self.id_width = self._integer("game_saves.id_width", 3, 1, 9)
        self.save_limit = self._integer("game_saves.maximum", 5, 1, 1000)
        self.layouts = self._load_layouts()
        self.role_folders = self.registries.get_registered_entries("roles")

    def _integer(self, tag, default, minimum, maximum):
        try:
            value = int(self.config.get(tag, str(default)))
        except (TypeError, ValueError) as error:
            raise ValueError(f"Invalid integer setting: {tag}") from error
        if not minimum <= value <= maximum:
            raise ValueError(f"Setting {tag} must be between {minimum} and {maximum}.")
        return value

    def _configured_path(self, tag, default):
        value = self.config.get(tag, default)
        relative = self._safe_relative(value, tag)
        path = (self.project_root / Path(*relative.parts)).resolve()
        if self.project_root not in path.parents:
            raise ValueError(f"Configured path {tag} must stay inside the project.")
        return path

    @staticmethod
    def _safe_relative(value, label):
        path = PurePosixPath(str(value).replace("\\", "/"))
        if path.is_absolute() or not path.parts or any(part in ("", ".", "..") for part in path.parts):
            raise ValueError(f"Unsafe relative path in {label}.")
        return path

    def _load_layouts(self):
        registry_path = self.project_root / "data" / "registries" / "saves" / "entity_layouts.txt"
        registry = parse_file(registry_path)
        if registry.get("object.type") != "registry":
            raise ValueError(f"Invalid save entity-layout registry: {registry_path}")

        layouts = {}
        for entry in registry.entries:
            if not entry.tag.startswith("save.entity_layout."):
                continue
            role = entry.tag.rsplit(".", 1)[-1]
            definition = self.registries.resolve_definition(entry.value)
            if definition is None or definition.get("object.type") != "save_entity_layout":
                raise ValueError(f"Save layout for {role!r} does not resolve: {entry.value}")
            if definition.get("save.layout.role") != role:
                raise ValueError(f"Save layout role mismatch for {role!r}.")
            directory = definition.get("save.layout.directory", "")
            self._safe_relative(directory, f"save.layout.directory ({role})")
            files = {}
            for item in definition.entries:
                match = re.fullmatch(r"save\.layout\.file\.(\d+)\.(path|kind|source_prefix|group_name)", item.tag)
                if match:
                    index, field = match.groups()
                    files.setdefault(index, {})[field] = item.value
            normalized_files = []
            for index in sorted(files, key=int):
                specification = files[index]
                if not specification.get("path") or specification.get("kind") not in ("snapshot", "group", "empty"):
                    raise ValueError(f"Incomplete file layout {index} for role {role!r}.")
                self._safe_relative(specification["path"].replace("{source_filename}", "snapshot.txt").replace("{source_stem}", "entity"), f"save layout file ({role})")
                normalized_files.append(specification)
            layouts[role] = {
                "role": role,
                "directory": directory,
                "entity_directory_pattern": definition.get("save.layout.entity_directory_pattern", "{source_stem}"),
                "files": normalized_files,
            }

        registered_roles = self.registries.get_registered_entries("roles")
        missing = set(registered_roles) - set(layouts)
        if missing:
            raise ValueError(f"Save layouts are missing roles: {', '.join(sorted(missing))}.")
        return layouts

    def _save_id_pattern(self):
        return re.compile(rf"^{re.escape(self.folder_prefix)}(\d{{{self.id_width},}})$")

    def _save_directory(self, game_id):
        if not self._save_id_pattern().fullmatch(str(game_id or "")):
            return None
        path = (self.saves_root / str(game_id)).resolve()
        if self.saves_root.resolve() not in path.parents:
            return None
        return path

    def _next_save_id(self):
        self.saves_root.mkdir(parents=True, exist_ok=True)
        used = []
        for child in self.saves_root.iterdir():
            match = self._save_id_pattern().fullmatch(child.name)
            if child.is_dir() and match:
                used.append(int(match.group(1)))
        return f"{self.folder_prefix}{max(used, default=0) + 1:0{self.id_width}d}"

    @staticmethod
    def _timestamp():
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _serialize(records):
        output = io.StringIO(newline="")
        writer = csv.writer(output, quoting=csv.QUOTE_ALL, lineterminator="\n")
        writer.writerows((str(tag), str(value)) for tag, value in records)
        return output.getvalue()

    def _write_tags(self, path, records):
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        with temporary.open("w", encoding="utf-8", newline="") as file:
            file.write(self._serialize(records))
        temporary.replace(path)

    def _save_path(self, directory):
        return directory / self.save_filename

    def _sectors_path(self, directory):
        return directory / self.sectors_filename

    def create_save(self, name=""):
        if len(self.list_saves()) >= self.save_limit:
            raise ValueError(f"All {self.save_limit} save slots are used. Delete a save to make room.")
        name = str(name or "").strip()
        name_limit = self._integer("game_saves.name_maximum_length", 60, 1, 1000)
        if len(name) > name_limit:
            raise ValueError(f"Game name cannot exceed {name_limit} characters.")

        game_id = self._next_save_id()
        match = self._save_id_pattern().fullmatch(game_id)
        number = int(match.group(1))
        if not name:
            name = self.config.get("game_saves.default_name", "Game {number}").format(number=number)
        directory = self._save_directory(game_id)
        directory.mkdir(parents=True, exist_ok=False)
        now = self._timestamp()
        try:
            for layout in self.layouts.values():
                relative = self._safe_relative(layout["directory"], "save.layout.directory")
                (directory / Path(*relative.parts)).mkdir(parents=True, exist_ok=True)
            self._write_tags(self._save_path(directory), [
                ("object.type", "game_save"),
                ("object.id", f"save.{game_id}"),
                ("object.version", "1"),
                ("save.id", game_id),
                ("save.name", name),
                ("save.status", "map_selection"),
                ("save.map.locked", "false"),
                ("save.created_at", now),
                ("save.updated_at", now),
            ])
            self._write_tags(self._sectors_path(directory), [
                ("object.type", "game_sectors"),
                ("object.id", f"save.{game_id}.sectors"),
                ("object.version", "1"),
                ("save.sectors.count", "0"),
            ])
        except Exception:
            shutil.rmtree(directory, ignore_errors=True)
            raise
        return self.load_save(game_id)

    def load_save(self, game_id):
        directory = self._save_directory(game_id)
        if not directory or not directory.is_dir():
            return None
        path = self._save_path(directory)
        try:
            document = parse_file(path)
        except (OSError, ValueError, TagParserError):
            return None
        if document.get("object.type") != "game_save" or document.get("save.id") != game_id:
            return None
        map_id = document.get("save.map.id", "")
        map_name = "Map not selected"
        if map_id:
            map_definition = self.registries.get_definition("arenas", map_id)
            if map_definition:
                map_name = map_definition.get("arena.name", map_id.replace("_", " ").title())
            else:
                map_name = map_id
        sectors = self.load_sectors(game_id)
        return {
            "id": game_id,
            "name": document.get("save.name", game_id),
            "status": document.get("save.status", "map_selection"),
            "map_id": map_id,
            "map_seed": document.get("save.map.seed", ""),
            "map_locked": document.get("save.map.locked", "false").strip().lower() in ("true", "1", "yes"),
            "map_name": map_name,
            "sector_count": len(sectors),
            "member_count": sum(len(sector["members"]) for sector in sectors),
            "created_at": document.get("save.created_at", ""),
            "updated_at": document.get("save.updated_at", ""),
        }

    def list_saves(self):
        if not self.saves_root.is_dir():
            return []
        saves = []
        for directory in sorted(self.saves_root.iterdir()):
            if directory.is_dir() and self._save_id_pattern().fullmatch(directory.name):
                save = self.load_save(directory.name)
                if save:
                    saves.append(save)
        return sorted(saves, key=lambda item: item["id"])

    def delete_save(self, game_id):
        directory = self._save_directory(game_id)
        if not directory or not directory.is_dir() or not self.load_save(game_id):
            return False
        shutil.rmtree(directory)
        return True

    def _replace_save_tags(self, game_id, updates):
        directory = self._save_directory(game_id)
        save = self.load_save(game_id)
        if not directory or not save:
            raise ValueError("That save could not be found.")
        old = parse_file(self._save_path(directory))
        replaced = set(updates)
        records = [(entry.tag, entry.value) for entry in old.entries if entry.tag not in replaced]
        records.extend(updates.items())
        self._write_tags(self._save_path(directory), records)

    def choose_map(self, game_id, map_id, seed, locked=False):
        if not self.load_save(game_id):
            raise ValueError("That save could not be found.")
        if not self.registries.get_definition("arenas", map_id):
            raise ValueError("Choose a registered arena.")
        self._replace_save_tags(game_id, {
            "save.map.id": map_id,
            "save.map.seed": str(seed),
            "save.map.locked": "true" if locked else "false",
            "save.status": "sector_setup",
            "save.updated_at": self._timestamp(),
        })

    def _load_sectors_document(self, game_id):
        directory = self._save_directory(game_id)
        if not directory or not self.load_save(game_id):
            raise ValueError("That save could not be found.")
        path = self._sectors_path(directory)
        if not path.is_file():
            raise ValueError("The sector data for this save is missing.")
        try:
            document = parse_file(path)
        except TagParserError as error:
            raise ValueError("The sector data file is not valid tag data.") from error
        if document.get("object.type") != "game_sectors":
            raise ValueError("The sector data file has an invalid object type.")
        return document

    def load_sectors(self, game_id):
        directory = self._save_directory(game_id)
        if not directory or not self._sectors_path(directory).is_file():
            return []
        try:
            document = parse_file(self._sectors_path(directory))
        except TagParserError:
            return []
        if document.get("object.type") != "game_sectors":
            return []
        try:
            count = int(document.get("save.sectors.count", "0"))
        except ValueError:
            return []
        sectors = []
        for sector_number in range(1, count + 1):
            prefix = f"save.sectors.{sector_number:03d}"
            try:
                member_count = int(document.get(f"{prefix}.members.count", "0"))
            except ValueError:
                member_count = 0
            members = [
                document.get(f"{prefix}.member.{member_number:03d}.entity_id", "")
                for member_number in range(1, member_count + 1)
            ]
            sectors.append({
                "number": sector_number,
                "name": document.get(f"{prefix}.name", f"Sector {sector_number}"),
                "members": members,
            })
        return sectors

    def setup_limits(self):
        limits = {
            "sector_minimum": self._integer("game_setup.sectors.minimum", 1, 1, 1000),
            "sector_maximum": self._integer("game_setup.sectors.maximum", 64, 1, 1000),
            "sector_default": self._integer("game_setup.sectors.default", 12, 1, 1000),
            "member_minimum": self._integer("game_setup.members.minimum", 1, 1, 1000),
            "member_maximum": self._integer("game_setup.members.maximum", 64, 1, 1000),
            "member_default": self._integer("game_setup.members.default", 2, 1, 1000),
            "unique_members": self.config.get("game_setup.members.unique_per_game", "true").lower() in ("true", "1", "yes"),
            "sector_label": self.config.get("game_setup.sector_label", "Sector"),
            "role": self.config.get("game_setup.selectable_role", "tributes"),
        }
        if limits["sector_minimum"] > limits["sector_maximum"] or limits["member_minimum"] > limits["member_maximum"]:
            raise ValueError("Sector or member minimum exceeds its configured maximum.")
        return limits

    def available_tributes(self, game_id):
        limits = self.setup_limits()
        role = limits["role"]
        source_folder = self.role_folders.get(role)
        if not source_folder:
            return []
        source_root = self.project_root / "data" / "compendium" / "entities" / source_folder
        entities = {}
        if source_root.is_dir():
            for path in sorted(source_root.glob("*.txt")):
                try:
                    document = parse_file(path)
                except (OSError, ValueError, TagParserError):
                    continue
                if document.get("object.type") != "entity" or document.get("entity.role") != role:
                    continue
                entity_id = document.get("object.id", "")
                if entity_id:
                    entities[entity_id] = self._entity_view(document, entity_id, path)

        save_directory = self._save_directory(game_id)
        layout = self.layouts.get(role)
        if save_directory and layout:
            role_path = self._role_save_path(save_directory, layout)
            if role_path.is_dir():
                for path in sorted(role_path.glob("*/*.txt")):
                    try:
                        document = parse_file(path)
                    except (OSError, ValueError, TagParserError):
                        continue
                    if document.get("object.type") != "entity" or document.get("entity.role") != role:
                        continue
                    entity_id = document.get("object.id", "")
                    if entity_id:
                        entities[entity_id] = self._entity_view(document, entity_id, path, saved=True)
        return sorted(entities.values(), key=lambda item: item["name"].casefold())

    @staticmethod
    def _entity_view(document, entity_id, path, saved=False):
        return {
            "id": entity_id,
            "role": document.get("entity.role", ""),
            "name": document.get("entity.name", entity_id),
            "nickname": document.get("entity.nickname", ""),
            "species": document.get("entity.species", ""),
            "portrait_url": document.get("entity.portrait_url", ""),
            "path": path,
            "saved": saved,
        }

    def _role_save_path(self, save_directory, layout):
        relative = self._safe_relative(layout["directory"], "save.layout.directory")
        path = (save_directory / Path(*relative.parts)).resolve()
        if save_directory.resolve() not in path.parents:
            raise ValueError("Entity layout escaped its game save folder.")
        return path

    def _entity_folder(self, save_directory, layout, source_path, entity_id):
        relative_root = self._safe_relative(layout["directory"], "save.layout.directory")
        number_match = re.search(r"(\d+)$", source_path.stem)
        folder_name = layout["entity_directory_pattern"].format(
            source_stem=source_path.stem,
            entity_id=re.sub(r"[^A-Za-z0-9_-]", "_", entity_id),
            number=number_match.group(1) if number_match else re.sub(r"[^A-Za-z0-9_-]", "_", entity_id),
        )
        relative_folder = self._safe_relative(folder_name, "save.layout.entity_directory_pattern")
        folder = (save_directory / Path(*relative_root.parts) / Path(*relative_folder.parts)).resolve()
        if save_directory.resolve() not in folder.parents:
            raise ValueError("Entity layout escaped its game save folder.")
        return folder

    def _snapshot_entity(self, game_id, entity):
        save_directory = self._save_directory(game_id)
        if not save_directory or not self.load_save(game_id):
            raise ValueError("That save could not be found.")
        source_path = Path(entity["path"]).resolve()
        if save_directory.resolve() in source_path.parents:
            return
        role = entity.get("role") or self.setup_limits()["role"]
        layout = self.layouts.get(role)
        if not layout:
            raise ValueError(f"No save layout is registered for role {role!r}.")
        destination_folder = self._entity_folder(save_directory, layout, source_path, entity["id"])
        source_document = parse_file(source_path)
        number_match = re.search(r"(\d+)$", source_path.stem)
        entity_number = number_match.group(1) if number_match else re.sub(r"[^A-Za-z0-9_-]", "_", entity["id"])
        for specification in layout["files"]:
            output_relative = specification["path"].format(
                source_filename=source_path.name,
                source_stem=source_path.stem,
                entity_id=re.sub(r"[^A-Za-z0-9_-]", "_", entity["id"]),
                number=entity_number,
            )
            safe_relative = self._safe_relative(output_relative, "save.layout.file.path")
            destination = (destination_folder / Path(*safe_relative.parts)).resolve()
            if destination_folder.resolve() not in destination.parents:
                raise ValueError("An entity file path escaped its entity folder.")
            kind = specification["kind"]
            if kind == "snapshot":
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, destination)
            else:
                group_name = specification.get("group_name", "state")
                records = [
                    ("object.type", "saved_entity_data"),
                    ("object.id", f"save.{game_id}.{entity['id']}.{group_name}"),
                    ("object.version", "1"),
                    ("save.entity.source_id", entity["id"]),
                    ("save.entity.role", role),
                    ("save.entity.data_group", group_name),
                ]
                if kind == "group":
                    source_prefix = specification.get("source_prefix", "")
                    if not source_prefix:
                        raise ValueError(f"A source prefix is required for save layout group {group_name!r}.")
                    records.extend(
                        (entry.tag, entry.value)
                        for entry in source_document.entries
                        if entry.tag.startswith(source_prefix)
                    )
                elif kind != "empty":
                    raise ValueError(f"Unknown save layout file kind: {kind}")
                self._write_tags(destination, records)

    def save_sectors(self, game_id, sectors):
        save = self.load_save(game_id)
        if not save:
            raise ValueError("That save could not be found.")
        if not save["map_id"]:
            raise ValueError("Choose an arena before saving sectors.")
        limits = self.setup_limits()
        count = len(sectors)
        if not limits["sector_minimum"] <= count <= limits["sector_maximum"]:
            raise ValueError(f"Choose between {limits['sector_minimum']} and {limits['sector_maximum']} sectors.")
        available = {item["id"]: item for item in self.available_tributes(game_id)}
        seen_members = set()
        for index, sector in enumerate(sectors, start=1):
            members = sector.get("members", [])
            if not limits["member_minimum"] <= len(members) <= limits["member_maximum"]:
                raise ValueError(f"{limits['sector_label']} {index} needs between {limits['member_minimum']} and {limits['member_maximum']} members.")
            for entity_id in members:
                if entity_id not in available:
                    raise ValueError(f"A selected tribute is no longer available: {entity_id}")
                if limits["unique_members"] and entity_id in seen_members:
                    raise ValueError("A tribute can only be assigned once in this save.")
                seen_members.add(entity_id)

        for entity_id in seen_members:
            self._snapshot_entity(game_id, available[entity_id])

        records = [
            ("object.type", "game_sectors"),
            ("object.id", f"save.{game_id}.sectors"),
            ("object.version", "1"),
            ("save.sectors.count", str(count)),
        ]
        for sector_number, sector in enumerate(sectors, start=1):
            prefix = f"save.sectors.{sector_number:03d}"
            records.extend([
                (f"{prefix}.name", sector.get("name") or f"{limits['sector_label']} {sector_number}"),
                (f"{prefix}.members.count", str(len(sector["members"]))),
            ])
            for member_number, entity_id in enumerate(sector["members"], start=1):
                records.append((f"{prefix}.member.{member_number:03d}.entity_id", entity_id))

        directory = self._save_directory(game_id)
        self._write_tags(self._sectors_path(directory), records)
        self._replace_save_tags(game_id, {
            "save.status": "setup_complete",
            "save.updated_at": self._timestamp(),
        })
        return self.load_save(game_id)

    def sectors_from_form(self, form):
        limits = self.setup_limits()
        raw_count = form.get("sector_count", "")
        try:
            count = int(raw_count)
        except (TypeError, ValueError) as error:
            raise ValueError("Enter a valid number of sectors.") from error
        if not limits["sector_minimum"] <= count <= limits["sector_maximum"]:
            raise ValueError(f"Choose between {limits['sector_minimum']} and {limits['sector_maximum']} sectors.")
        sectors = []
        for sector_number in range(1, count + 1):
            pattern = re.compile(rf"^sector_{sector_number:03d}_member_(\d+)$")
            indexed_members = []
            for key in form.keys():
                match = pattern.fullmatch(key)
                if match:
                    indexed_members.append((int(match.group(1)), form.get(key, "").strip()))
            members = [value for _, value in sorted(indexed_members)]
            sectors.append({"name": f"{limits['sector_label']} {sector_number}", "members": members})
        return sectors

    def initial_sectors(self, game_id, available_count):
        existing = self.load_sectors(game_id)
        if existing:
            return existing
        limits = self.setup_limits()
        if available_count < limits["member_minimum"]:
            return []
        member_default = min(max(limits["member_minimum"], limits["member_default"]), limits["member_maximum"], available_count)
        sector_default = min(limits["sector_default"], limits["sector_maximum"], max(limits["sector_minimum"], available_count // member_default))
        return [
            {"number": index, "name": f"{limits['sector_label']} {index}", "members": [""] * member_default}
            for index in range(1, sector_default + 1)
        ]
