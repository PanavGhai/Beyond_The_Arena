
# engine/parsing/entity_parser.py

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from engine.parsing.tag_parser import TagDocument


# ==========================================
# 1. PARSER ERROR
# ==========================================

class EntityParseError(Exception):
    """Raised when an entity cannot be converted into an Entity object."""


# ==========================================
# 2. ENTITY DATA MODEL
# ==========================================

@dataclass
class Entity:

    # --------------------------------------
    # Universal metadata
    # --------------------------------------

    id: str
    version: str
    persistent: Optional[bool]

    # --------------------------------------
    # Entity identity
    # --------------------------------------

    name: str

    nickname: str = ""
    pronouns: str = ""
    gender: str = ""

    age: Optional[int] = None

    role: str = ""
    species: str = ""

    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None

    portrait_url: str = ""
    death_portrait_url: str = ""

    description: str = ""

    # --------------------------------------
    # Entity statistics
    # --------------------------------------

    attributes: dict[str, int] = field(default_factory=dict)

    personality_facets: dict[str, int] = field(default_factory=dict)

    personality_values: dict[str, int] = field(default_factory=dict)

    skills: dict[str, int] = field(default_factory=dict)

    # --------------------------------------
    # Additional data
    # --------------------------------------

    extra_tags: dict[str, str] = field(default_factory=dict)

    source_file: Optional[Path] = None


# ==========================================
# 3. VALUE CONVERSION
# ==========================================

def _get_integer(
    document: TagDocument,
    tag: str
) -> Optional[int]:

    value = document.get(tag)

    if value is None or value == "":
        return None

    try:
        return int(value)

    except ValueError as error:
        raise EntityParseError(
            f"Tag '{tag}' must contain an integer. "
            f"Received: {value!r}"
        ) from error


def _get_float(document: TagDocument, tag: str) -> Optional[float]:
    value = document.get(tag)
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError as error:
        raise EntityParseError(
            f"Tag '{tag}' must contain a number. Received: {value!r}"
        ) from error


def _get_boolean(
    document: TagDocument,
    tag: str
) -> Optional[bool]:

    value = document.get(tag)

    if value is None or value == "":
        return None

    normalized = value.strip().lower()

    if normalized in ("true", "1", "yes"):
        return True

    if normalized in ("false", "0", "no"):
        return False

    raise EntityParseError(
        f"Tag '{tag}' must contain a boolean value. "
        f"Received: {value!r}"
    )


def _get_numeric_group(
    document: TagDocument,
    prefix: str
) -> dict[str, int]:

    raw_group = document.get_group(prefix)

    result = {}

    for key, value in raw_group.items():

        try:
            result[key] = int(value)

        except ValueError as error:
            raise EntityParseError(
                f"Tag '{prefix}{key}' must contain an integer. "
                f"Received: {value!r}"
            ) from error

    return result


# ==========================================
# 4. KNOWN ENTITY TAGS
# ==========================================

KNOWN_ENTITY_TAGS = {
    "object.type",
    "object.id",
    "object.version",
    "settings.persistent",

    "entity.name",
    "entity.nickname",
    "entity.pronouns",
    "entity.gender",
    "entity.age",
    "entity.role",
    "entity.species",
    "entity.height_cm",
    "entity.weight_kg",
    "entity.portrait_url",
    "entity.death_portrait_url",
    "entity.description",
}


# ==========================================
# 5. ENTITY PARSER
# ==========================================

def parse_entity(document: TagDocument) -> Entity:
    """
    Convert a TagDocument into a structured Entity.

    This function interprets entity-specific tags.
    It does not read files or validate registries.
    """

    if document.get("object.type") != "entity":
        raise EntityParseError(
            "Cannot parse document as an entity. "
            f"Found object.type={document.get('object.type')!r}"
        )

    # --------------------------------------
    # Extract additional tags
    # --------------------------------------

    known_prefixes = (
        "entity.attributes.",
        "entity.personality.facets.",
        "entity.personality.values.",
        "entity.skills.",
    )

    extra_tags = {}

    for entry in document.entries:

        if entry.tag in KNOWN_ENTITY_TAGS:
            continue

        if any(
            entry.tag.startswith(prefix)
            for prefix in known_prefixes
        ):
            continue

        extra_tags[entry.tag] = entry.value

    # --------------------------------------
    # Construct entity
    # --------------------------------------

    return Entity(

        # Universal metadata

        id=document.get("object.id", ""),
        version=document.get("object.version", ""),
        persistent=_get_boolean(
            document,
            "settings.persistent"
        ),

        # Identity

        name=document.get("entity.name", ""),

        nickname=document.get("entity.nickname", ""),
        pronouns=document.get("entity.pronouns", ""),
        gender=document.get("entity.gender", ""),

        age=_get_integer(document, "entity.age"),

        role=document.get("entity.role", ""),
        species=document.get("entity.species", ""),

        height_cm=_get_float(
            document,
            "entity.height_cm"
        ),

        weight_kg=_get_float(
            document,
            "entity.weight_kg"
        ),

        portrait_url=document.get("entity.portrait_url", ""),
        death_portrait_url=document.get(
            "entity.death_portrait_url",
            ""
        ),

        description=document.get("entity.description", ""),

        # Statistics

        attributes=_get_numeric_group(
            document,
            "entity.attributes."
        ),

        personality_facets=_get_numeric_group(
            document,
            "entity.personality.facets."
        ),

        personality_values=_get_numeric_group(
            document,
            "entity.personality.values."
        ),

        skills=_get_numeric_group(
            document,
            "entity.skills."
        ),

        # Additional information

        extra_tags=extra_tags,

        source_file=document.file_path,
    )
