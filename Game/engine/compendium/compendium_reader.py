
# engine/compendium/compendium_reader.py

from pathlib import Path
import logging

from engine.parsing.tag_parser import parse_file
from engine.registries.registry_manager import RegistryManager


logger = logging.getLogger(__name__)


class CompendiumReader:

    def __init__(self, project_root, registries=None):

        self.project_root = Path(project_root)

        self.entity_root = (
            self.project_root
            / "data"
            / "compendium"
            / "entities"
        )

        self.entity_registry_path = (
            self.project_root
            / "data"
            / "registries"
            / "entities"
            / "roles.txt"
        )

        self.registries = (
            registries
            if registries is not None
            else RegistryManager(self.project_root)
        )

        self.definition_cache = {}

    # ==========================================
    # 1. LOAD ENTITY CATEGORIES
    # ==========================================

    def load_categories(self):

        if not self.entity_registry_path.is_file():
            raise FileNotFoundError(
                f"Entity registry not found: "
                f"{self.entity_registry_path}"
            )

        document = parse_file(self.entity_registry_path)

        categories = []

        for entry in document.entries:

            if entry.tag.startswith("object."):
                continue

            if entry.tag.startswith("settings."):
                continue

            folder_name = entry.value.strip()

            if not folder_name:
                continue

            folder_path = self.entity_root / folder_name

            categories.append({
                "id": folder_name,
                "name": folder_name.replace("_", " ").title(),
                "path": folder_path,
                "count": 0,
            })

        return categories

    # ==========================================
    # 2. RESOLVE DEFINITION LABELS
    # ==========================================

    def get_definition(self, family, name):
        cache_key = (family, name)

        if cache_key not in self.definition_cache:
            self.definition_cache[cache_key] = (
                self.registries.get_definition(family, name)
            )

        return self.definition_cache[cache_key]

    def resolve_name(self, family, key):
        registry = self.registries.registries.get(family, {})
        definition_id = registry.get(key)

        if not definition_id:
            return key.replace("_", " ").title()

        definition = self.get_definition(family, key)

        if definition is None:
            return key.replace("_", " ").title()

        name_tags = {
            "attributes": "attribute.name",
            "skills": "skill.name",
            "facets": "personality.facet.name",
            "values": "personality.value.name",
        }

        name_tag = name_tags.get(family)

        if name_tag:
            name = definition.get(name_tag)

            if name:
                return name

        return key.replace("_", " ").title()

    # ==========================================
    # 3. READ ENTITY GROUPS
    # ==========================================

    def load_group(
        self,
        document,
        prefix,
        family,
        maximum
    ):

        raw_group = document.get_group(prefix)

        items = []

        for key, raw_value in raw_group.items():

            try:
                value = int(raw_value)
            except (TypeError, ValueError):
                logger.warning(
                    "Invalid numeric value for %s%s: %s",
                    prefix,
                    key,
                    raw_value
                )
                continue

            percent = max(
                0,
                min(100, (value / maximum) * 100)
            )

            items.append({
                "id": key,
                "name": self.resolve_name(family, key),
                "value": value,
                "percent": round(percent),
            })

        return items

    # ==========================================
    # 4. BUILD PROFILE FIELDS
    # ==========================================

    def build_profile_fields(self, data):

        field_definitions = [
            ("Age", "entity.age"),
            ("Species", "entity.species"),
            ("Gender", "entity.gender"),
            ("Pronouns", "entity.pronouns"),
            ("Role", "entity.role"),
        ]

        fields = []

        for label, tag in field_definitions:

            value = data.get(tag)

            if value:
                fields.append({
                    "label": label,
                    "value": value,
                })

        return fields

    # ==========================================
    # 5. LOAD INDIVIDUAL ENTITY
    # ==========================================

    def load_entity(self, file_path, category):

        document = parse_file(file_path)

        if document.get("object.type") != "entity":
            return None

        name = document.get("entity.name")

        if not name:
            logger.warning(
                "Entity has no name: %s",
                file_path
            )
            return None

        data = document.to_dict()

        attributes = self.load_group(
            document,
            "entity.attributes.",
            "attributes",
            20
        )

        skills = self.load_group(
            document,
            "entity.skills.",
            "skills",
            20
        )

        personality_facets = self.load_group(
            document,
            "entity.personality.facets.",
            "facets",
            100
        )

        personality_values = self.load_group(
            document,
            "entity.personality.values.",
            "values",
            100
        )

        top_skills = sorted(
            skills,
            key=lambda item: item["value"],
            reverse=True
        )[:3]

        role = data.get("entity.role", "")
        species = data.get("entity.species", "")
        # Species values are namespaced identifiers (for example
        # ``species.human``), while the Compendium presents display labels.
        species = species.rsplit(".", 1)[-1].replace("_", " ").title()
        data["entity.species"] = species

        return {
            "id": data.get("object.id", file_path.stem),
            "name": name,
            "nickname": data.get("entity.nickname", ""),
            "description": data.get("entity.description", ""),
            "portrait_url": data.get("entity.portrait_url", ""),
            "category_id": category["id"],
            "category_name": category["name"],
            "role": role,
            "species": species,
            "age": data.get("entity.age", ""),
            "profile_fields": self.build_profile_fields(data),
            "attributes": attributes,
            "skills": skills,
            "top_skills": top_skills,
            "personality_facets": personality_facets,
            "personality_values": personality_values,
            "source_file": str(file_path),
            "file_name": file_path.stem,
        }

    # ==========================================
    # 6. LOAD ALL ENTITIES
    # ==========================================

    def load_all(self):

        categories = self.load_categories()

        entities = []

        for category in categories:

            category_entities = []

            files = sorted(
                category["path"].glob("*.txt")
            )

            for file_path in files:

                try:
                    entity = self.load_entity(
                        file_path,
                        category
                    )

                    if entity is not None:
                        category_entities.append(entity)

                except Exception:
                    logger.exception(
                        "Failed to load entity file: %s",
                        file_path
                    )

            category["count"] = len(category_entities)

            entities.extend(category_entities)

        role_options = sorted({
            entity["role"]
            for entity in entities
            if entity["role"]
        }, key=str.lower)

        species_options = sorted({
            entity["species"]
            for entity in entities
            if entity["species"]
        }, key=str.lower)

        return {
            "categories": categories,
            "entities": entities,
            "role_options": role_options,
            "species_options": species_options,
        }
