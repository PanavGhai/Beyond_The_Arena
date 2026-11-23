"""Character creation flow, validation, and tag-file persistence."""

import csv
import io
import re
from pathlib import Path

from engine.character_creation.references import CharacterCreationReferences
from engine.parsing.tag_parser import parse_file
from engine.registries.registry_manager import RegistryManager
from engine.validation.character_creation_validator import CharacterCreationValidator


class CharacterCreationService:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.registries = RegistryManager(self.project_root)
        self.references = CharacterCreationReferences(self.project_root, self.registries).build()
        self.validator = CharacterCreationValidator()

    def validate(self, form):
        return self.validator.validate(form, self.references)

    def save(self, form):
        report = self.validate(form)
        if not report.valid:
            return None, report
        role = form.get("role", "").strip()
        role_data = next(item for item in self.references["roles"] if item["id"] == role)
        folder = role_data["folder"]
        if not re.fullmatch(r"[a-z0-9_]+", folder):
            report.add_error("The registered role folder must use lowercase letters, numbers, and underscores.")
            return None, report
        directory = self.project_root / "data" / "compendium" / "entities" / folder
        directory.mkdir(parents=True, exist_ok=True)
        entity_id, file_path = self._next_identity(folder, directory)

        records = [
            ("object.type", "entity"),
            ("object.id", entity_id),
            ("object.version", "1"),
            ("settings.hardcore", "true" if role == "tributes" and form.get("hardcore", "").strip().lower() in ("true", "on", "1") else "false"),
            ("entity.role", role),
            ("entity.name", form.get("name", "").strip()),
            ("entity.nickname", form.get("nickname", "").strip()),
            ("entity.pronouns", form.get("pronouns", "").strip()),
            ("entity.gender", form.get("gender", "").strip()),
            ("entity.age", str(int(form.get("age", "0")))),
            ("entity.species", form.get("species", "").strip()),
            ("entity.height_cm", self._float_text(form.get("height_cm", ""))),
            ("entity.weight_kg", self._float_text(form.get("weight_kg", ""))),
            ("entity.portrait_url", form.get("portrait_url", "").strip()),
            ("entity.death_portrait_url", form.get("death_portrait_url", "").strip() or "bw"),
            ("entity.description", form.get("description", "").strip()),
        ]
        records.extend((f"entity.attributes.{item['id']}", form.get(f"attribute_{item['id']}", ""))
                       for item in self.references["attributes"])
        records.extend((f"entity.skills.{item['id']}", form.get(f"skill_{item['id']}", ""))
                       for item in self.references["skills"])
        records.extend((f"entity.personality.facets.{item['id']}", form.get(f"facet_{item['id']}", ""))
                       for item in self.references["facets"])
        records.extend((f"entity.personality.values.{item['id']}", form.get(f"value_{item['id']}", ""))
                       for item in self.references["values"])
        contents = self._serialize(records)
        try:
            with file_path.open("x", encoding="utf-8", newline="") as file:
                file.write(contents)
        except FileExistsError:
            return self.save(form)
        return file_path, report

    def sheet_data(self, file_path):
        document = parse_file(file_path)
        references = self.references
        attr_info = {item["id"]: item for item in references["attributes"]}
        skill_info = {item["id"]: item for item in references["skills"]}
        attributes, skills = [], []
        for key, raw in document.get_group("entity.attributes.").items():
            info = attr_info.get(key, {"name": key.replace("_", " ").title(), "default": 6})
            value = int(raw)
            attributes.append({"id": key, "name": info["name"], "value": value,
                               "modifier": (value - info["default"]) // int(references["settings"].get("character_creation.attribute_modifier.interval", "3"))})
        for key, raw in document.get_group("entity.skills.").items():
            info = skill_info.get(key, {"name": key.replace("_", " ").title()})
            value = int(raw)
            skills.append({"id": key, "name": info["name"], "value": value,
                           "modifier": value // int(references["settings"].get("character_creation.skill_modifier.divisor", "4")),
                           "category": info.get("category", "other")})
        role = document.get("entity.role", "")
        species = document.get("entity.species", "")
        return {
            "id": document.get("object.id", file_path.stem),
            "name": document.get("entity.name", ""),
            "nickname": document.get("entity.nickname", ""),
            "pronouns": document.get("entity.pronouns", ""),
            "gender": document.get("entity.gender", ""),
            "age": document.get("entity.age", ""),
            "role": role.replace("_", " ").title(),
            "species": species.rsplit(".", 1)[-1].replace("_", " ").title(),
            "height_cm": document.get("entity.height_cm", ""),
            "weight_kg": document.get("entity.weight_kg", ""),
            "portrait_url": document.get("entity.portrait_url", ""),
            "death_portrait_url": document.get("entity.death_portrait_url", "bw"),
            "description": document.get("entity.description", ""),
            "attributes": sorted(attributes, key=lambda item: item["name"].lower()),
            "skills": sorted(skills, key=lambda item: (item["category"], item["name"].lower())),
            "facets": self._display_values(document.get_group("entity.personality.facets."), references["facets"]),
            "values": self._display_values(document.get_group("entity.personality.values."), references["values"]),
        }

    @staticmethod
    def _display_values(raw_values, definitions):
        by_id = {item["id"]: item for item in definitions}
        return [{"id": key, "name": by_id.get(key, {}).get("name", key.replace("_", " ").title()),
                 "value": int(value)} for key, value in raw_values.items()]

    def _next_identity(self, role, directory):
        used = set()
        for path in directory.glob("*.txt"):
            try:
                used.add(parse_file(path).get("object.id", ""))
            except Exception:
                continue
        number = 1
        while True:
            entity_id = f"entity.{role}.{number:03d}"
            file_path = directory / f"{role}_{number:03d}.txt"
            if entity_id not in used and not file_path.exists():
                return entity_id, file_path
            number += 1

    @staticmethod
    def _float_text(value):
        return format(float(value), ".12g")

    @staticmethod
    def _serialize(records):
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        writer.writerows(records)
        return output.getvalue()
