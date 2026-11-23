"""Build character-creation choices from data registries and definitions."""

from pathlib import Path

from engine.parsing.tag_parser import parse_file


class CharacterCreationReferences:
    def __init__(self, project_root, registries):
        self.project_root = Path(project_root)
        self.registries = registries
        self.config = parse_file(self.project_root / "data" / "config" / "character_creation.txt")

    def _options(self, filename, prefix):
        path = self.project_root / "data" / "registries" / "options" / filename
        document = parse_file(path)
        groups = {}
        for entry in document.entries:
            parts = entry.tag.split(".")
            if len(parts) != 3 or parts[0] != prefix:
                continue
            groups.setdefault(parts[1], {})[parts[2]] = entry.value
        return [
            {"id": key, "name": fields["value"]}
            for key, fields in groups.items()
            if fields.get("enabled", "true").strip().lower() in ("true", "1", "yes")
            and fields.get("value")
        ]

    def _definition_rows(self, family, name_tag, description_tag, minimum_tag, maximum_tag, default_tag):
        rows = []
        for key, definition_id in self.registries.get_registered_entries(family).items():
            definition = self.registries.resolve_definition(definition_id)
            if definition is None:
                continue
            minimum = int(float(definition.get(minimum_tag, "0")))
            maximum = int(float(definition.get(maximum_tag, "100")))
            default = definition.get(default_tag)
            default = int(float(default)) if default is not None else (minimum + maximum) // 2
            rows.append({
                "id": key,
                "name": definition.get(name_tag, key.replace("_", " ").title()),
                "description": definition.get(description_tag, ""),
                "opposite": definition.get(f"{name_tag.split('.', 1)[0]}.opposite", ""),
                "minimum": minimum,
                "maximum": maximum,
                "default": default,
                "definition": definition,
            })
        return rows

    def build(self):
        attributes = self._definition_rows(
            "attributes", "attribute.name", "attribute.description",
            "attribute.minimum", "attribute.maximum", "attribute.default"
        )
        skills = []
        for row in self._definition_rows(
            "skills", "skill.name", "skill.description",
            "skill.minimum", "skill.maximum", "skill.default"
        ):
            definition = row.pop("definition")
            row["category"] = definition.get("skill.category", "other")
            row["creation_maximum"] = int(float(
                definition.get("skill.creation_maximum", row["maximum"])
            ))
            row["attribute"] = definition.get("skill.attribute", "")
            skills.append(row)
        skills.sort(key=lambda item: (item["category"].lower(), item["name"].lower()))

        facets = self._definition_rows(
            "facets", "facet.name", "facet.description",
            "facet.minimum", "facet.maximum", "facet.default"
        )
        values = self._definition_rows(
            "values", "value.name", "value.description",
            "value.minimum", "value.maximum", "value.default"
        )
        facet_pairs, unpaired_facets = self._group_opposites(facets)
        value_pairs, unpaired_values = self._group_opposites(values)
        species = []
        for key, definition_id in self.registries.get_registered_entries("species").items():
            definition = self.registries.resolve_definition(definition_id)
            if definition:
                species.append({
                    "id": f"species.{key}",
                    "name": definition.get("species.name", key.replace("_", " ").title()),
                })
        roles = [
            {"id": key, "folder": folder,
             "name": "NPCs" if key.lower() == "npcs" else key.replace("_", " ").title()}
            for key, folder in self.registries.get_registered_entries("roles").items()
        ]
        return {
            "attributes": attributes,
            "skills": skills,
            "skill_categories": sorted({item["category"] for item in skills}),
            "facets": facets,
            "facet_pairs": facet_pairs,
            "unpaired_facets": unpaired_facets,
            "values": values,
            "value_pairs": value_pairs,
            "unpaired_values": unpaired_values,
            "species": species,
            "roles": roles,
            "genders": self._options("genders.txt", "gender"),
            "pronouns": self._options("pronouns.txt", "pronouns"),
            "settings": self.config,
        }

    @staticmethod
    def _group_opposites(items):
        by_id = {item["id"]: item for item in items}
        ordered = sorted(items, key=lambda item: item["name"].lower())
        paired = []
        used = set()
        for item in ordered:
            if item["id"] in used or not item["opposite"]:
                continue
            other = by_id.get(item["opposite"])
            if other is None or other.get("opposite") != item["id"]:
                continue
            pair = sorted((item, other), key=lambda entry: entry["name"].lower())
            paired.append(pair)
            used.update((item["id"], other["id"]))
        singles = [item for item in ordered if item["id"] not in used]
        return paired, singles
