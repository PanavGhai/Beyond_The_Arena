# Beyond the Arena — Data Parsing & Registry System

## 1. Purpose

Beyond the Arena uses a custom tag-value data format stored in `.txt` files.

The system is designed to separate:

- **Data storage:** `.txt` files containing game information.
- **Parsing:** Reading and interpreting the tag-value format.
- **Registries:** Defining which game concepts and entries are recognised by the system.
- **Definitions:** Storing the actual properties and rules associated with registered entries.
- **Validation:** Checking whether data files are structurally correct and reference valid definitions.
- **Object dispatching:** Routing different object types to their appropriate parsers.

The objective is to make the game data-driven. Adding a new attribute, skill, personality facet, item, or other registered entry should generally require adding data files rather than writing new Python code.

Python should interpret the data generically.

---

# 2. Project Structure

The relevant architecture is:

```text
Game/
│
├── engine/
│   ├── parsing/
│   │   ├── __init__.py
│   │   ├── tag_parser.py
│   │   ├── entity_parser.py
│   │   └── object_dispatcher.py
│   │
│   ├── registries/
│   │   ├── __init__.py
│   │   └── registry_manager.py
│   │
│   └── validation/
│       ├── __init__.py
│       └── entity_validator.py
│
├── data/
│   ├── registries/
│   │   ├── attributes/
│   │   ├── skills/
│   │   └── personality/
│   │       ├── facets.txt
│   │       └── values.txt
│   │
│   ├── definitions/
│   │   ├── attributes/
│   │   ├── skills/
│   │   └── personality/
│   │       ├── facets/
│   │       └── values/
│   │
│   └── compendium/
│       └── entities/
│           ├── tributes/
│           ├── mentors/
│           ├── sponsors/
│           ├── wildlife/
│           └── npcs/
│
└── test_registry.py
```

The directory structure may expand as more game systems are implemented.

## 3. Tag-Value File Format

Every data file uses one tag-value pair per line.

### Basic structure

```text
object.type,"attribute"
object.id,"definition.attribute.agility"
object.version,"1"

attribute.name,"Agility"
attribute.description,"Measures coordination, balance, reflexes, and physical responsiveness."
attribute.category,"physical"
attribute.default,"6"
attribute.minimum,"1"
attribute.maximum,"20"
```

### Rules

1. Each line contains a tag and its value.
2. Values are enclosed in double quotes.
3. Values are initially treated as strings, including numbers and booleans.
4. Tags use dotted namespaces.
5. Blank lines are permitted.
6. Lines beginning with `#` are comments.
7. Repeated tags are permitted.
8. Commas inside quoted values are supported.
9. Every file should have universal metadata.

### Universal metadata

Every data object should have:

```text
object.type,"<object_type>"
object.id,"<unique_identifier>"
object.version,"1"
```

Examples:

```text
object.type,"entity"
object.id,"entity.tribute.001"
object.version,"1"
```

```text
object.type,"skill"
object.id,"definition.skill.archery"
object.version,"1"
```

```text
object.type,"registry"
object.id,"registry.attributes"
object.version,"1"
```

The `object.id` is the object's logical identifier. It is not necessarily its physical filename or directory path.

### Repeated tags

Repeated tags are useful when an object has multiple entries of the same category.

Example:

```text
item.classifications,"classification.weapon"
item.classifications,"classification.tool"
```

Do not assume that every tag has only one value.

---

# 4. Universal Tag Parser

**File:** `engine/parsing/tag_parser.py`

The universal parser is responsible for reading `.txt` files and converting their contents into a structured `TagDocument`.

It does not determine whether a file is an entity, skill, attribute, registry, or another object type.

Its responsibility is simply to interpret the tag-value format.

### Import

```python
from engine.parsing.tag_parser import parse_file
```

### Read a file

```python
from pathlib import Path
from engine.parsing.tag_parser import parse_file

file_path = Path("data/definitions/attributes/agility.txt")

document = parse_file(file_path)
```

`parse_file()` returns a `TagDocument`.

### Available TagDocument methods

| Method | Purpose |
|---|---|
| `get(tag, default=None)` | Retrieves the last value associated with a tag. |
| `get_all(tag)` | Retrieves every value associated with a repeated tag. |
| `has(tag)` | Checks whether a tag exists. |
| `get_group(prefix)` | Retrieves tags belonging to a namespace as a dictionary. |
| `get_group_all(prefix)` | Retrieves grouped tags while preserving repeated values. |
| `to_dict()` | Converts the document into a dictionary. The last duplicate value wins. |

The document also exposes:

- `entries`: All parsed entries in their original order.
- `TagEntry.tag`: The tag name.
- `TagEntry.value`: The string value.
- `TagEntry.line_number`: The original line number.

### Examples

Retrieve an individual value:

```python
name = document.get("attribute.name")
```

Retrieve a value with a fallback:

```python
default = document.get("attribute.default", "6")
```

Retrieve all repeated values:

```python
classifications = document.get_all("item.classifications")
```

Check whether a tag exists:

```python
if document.has("attribute.maximum"):
    maximum = document.get("attribute.maximum")
```

Retrieve a namespace:

```python
attributes = document.get_group("attribute.")
```

Retrieve grouped values while preserving duplicates:

```python
attributes = document.get_group_all("attribute.")
```

Convert the document to a dictionary:

```python
data = document.to_dict()
```

### Important parser behaviour

The universal parser preserves values as strings.

For example:

```python
value = document.get("attribute.default")
```

If the file contains:

```text
attribute.default,"6"
```

The returned value is `"6"`, not `6`.

Convert values explicitly when performing calculations:

```python
default = int(document.get("attribute.default"))
```

For floating-point values:

```python
multiplier = float(document.get("effect.multiplier"))
```

For booleans, do not use `bool(value)` directly because `bool("false")` evaluates to `True`.

Instead:

```python
enabled = document.get("settings.enabled", "false").lower() == "true"
```

### Parser exceptions

The parser provides:

- `TagParserError`
- `TagSyntaxError`

Use these when handling malformed data files.

---

# 5. Registries

**File:** `engine/registries/registry_manager.py`

Registries define which entries the game recognises.

A registry does not contain the complete definition of an entry. It maps a registered key to a definition ID.

For example:

**File:** `data/registries/attributes/attributes.txt`

```text
object.type,"registry"
object.id,"registry.attributes"
object.version,"1"

attribute.strength,"definition.attribute.strength"
attribute.agility,"definition.attribute.agility"
attribute.endurance,"definition.attribute.endurance"
attribute.intelligence,"definition.attribute.intelligence"
attribute.wisdom,"definition.attribute.wisdom"
attribute.charisma,"definition.attribute.charisma"
```

This registry tells the system that six attributes exist.

Their actual properties are stored separately.

### Definition example

**File:** `data/definitions/attributes/agility.txt`

```text
object.type,"attribute"
object.id,"definition.attribute.agility"
object.version,"1"

attribute.name,"Agility"
attribute.description,"Measures coordination, balance, reflexes, and physical responsiveness."
attribute.category,"physical"

attribute.default,"6"
attribute.minimum,"1"
attribute.maximum,"20"
```

### Registry versus definition

| Registry | Definition |
|---|---|
| Lists recognised entries. | Stores actual properties. |
| Maps keys to definition IDs. | Provides the data referenced by those IDs. |
| Controls what can be referenced. | Controls what a registered entry means. |
| Does not define mechanics by itself. | Can describe mechanics and properties interpreted by the engine. |

Adding an entry to a registry does not automatically implement a new Python mechanic. The engine must already understand the relevant definition fields and effect types.

## 5.1 RegistryManager

### Import

```python
from engine.registries.registry_manager import RegistryManager
```

### Initialise

```python
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

registries = RegistryManager(PROJECT_ROOT)
```

The manager loads the registry data and indexes definitions.

### Current registry families

The current implementation recognises:

| Family | Purpose |
|---|---|
| `attributes` | Character attributes |
| `skills` | Character skills |
| `facets` | Personality facets |
| `values` | Personality values |

Current registry counts from the successful test:

| Registry family | Registered entries |
|---|---:|
| Attributes | 6 |
| Skills | 10 |
| Personality facets | 50 |
| Personality values | 16 |
| **Total** | **82** |

These are the current project counts, not permanent limits.

### Current RegistryManager capabilities

The implementation provides:

- Registry loading.
- Registry-family indexing.
- Definition indexing.
- Duplicate definition ID detection.
- Registry membership checks.
- Definition ID lookup.
- Definition resolution.
- Definition retrieval.
- Numeric minimum and maximum retrieval.

The current methods include:

```python
registries.contains(family, name)
registries.get_definition_id(family, name)
registries.get_registered_entries(family)
registries.resolve_definition(definition_id)
registries.get_definition(definition_id)
registries.get_numeric_limits(family, name)
```

Consult the actual `registry_manager.py` implementation for exact return types and optional arguments before changing how these methods are called.

### Examples

Check whether a skill is registered:

```python
if registries.contains("skills", "archery"):
    print("Archery is registered.")
```

Retrieve its definition ID:

```python
definition_id = registries.get_definition_id(
    "skills",
    "archery"
)
```

Retrieve all registered skills:

```python
skills = registries.get_registered_entries("skills")

for name, definition_id in skills.items():
    print(name, definition_id)
```

Retrieve a definition:

```python
definition = registries.get_definition(
    "definition.attribute.agility"
)
```

Retrieve numeric limits:

```python
minimum, maximum = registries.get_numeric_limits(
    "attributes",
    "agility"
)
```

Check the actual method implementation before relying on the last example's unpacking behaviour.

### Registry loading rules

1. Registry files must have `object.type,"registry"`.
2. Every registry needs a unique `object.id`.
3. Registry entries must point to definition IDs.
4. Definitions must exist under `data/definitions/`.
5. The definition's `object.id` must match the ID referenced by the registry.
6. Registry entries must not be duplicated with conflicting definition IDs.
7. When adding or changing data files after initial loading, reload the manager before expecting its indexes to reflect the changes.

---

# 6. Entity Definitions and Entity Data

Entities are stored in:

```text
data/compendium/entities/
```

Current entity categories include:

- Tributes
- Mentors
- Sponsors
- Wildlife
- NPCs

Example:

```text
data/compendium/entities/tributes/tribute_001.txt
```

An entity file contains the actual character data.

It references registered attributes, skills, personality facets, and values.

### Example entity structure

```text
object.type,"entity"
object.id,"entity.tribute.001"
object.version,"1"
settings.hardcore,"false"

entity.role,"tributes"

entity.name,"Katniss Everdeen"
entity.nickname,"Catnip"
entity.pronouns,"She/Her"
entity.gender,"female"
entity.age,"16"
entity.species,"species.human"

entity.attributes.strength,"14"
entity.attributes.agility,"18"
entity.attributes.endurance,"17"
entity.attributes.intelligence,"15"
entity.attributes.wisdom,"18"
entity.attributes.charisma,"9"

entity.skills.archery,"20"
entity.skills.hunting,"20"
entity.skills.tracking,"20"

entity.personality.facets.bravery,"80"
entity.personality.facets.friendliness,"91"

entity.personality.values.family,"100"
entity.personality.values.loyalty,"100"
```

The complete entity can contain many more fields.

### Important distinction

The entity file stores the character's actual values.

The definition files describe what those values mean.

For example:

```text
entity.attributes.agility,"18"
```

Stores Katniss's Agility score.

Meanwhile:

```text
definition.attribute.agility
```

Describes Agility's name, description, default value, minimum, maximum, and other properties.

Do not duplicate definition information inside every entity.

---

# 7. Entity Validator

**File:** `engine/validation/entity_validator.py`

The validator checks whether an entity is structurally valid and whether its registered values reference valid definitions.

### Import

```python
from engine.validation.entity_validator import EntityValidator
```

### Initialise

```python
validator = EntityValidator(registries)
```

The validator receives an already-loaded `RegistryManager`.

### Validate an entity

```python
entity = parse_file(ENTITY_PATH)

report = validator.validate(entity)
```

The returned report contains:

| Property | Purpose |
|---|---|
| `report.valid` | Whether validation succeeded. |
| `report.errors` | Errors that cause validation failure. |
| `report.warnings` | Issues that do not necessarily invalidate the entity. |

### Display validation results

```python
print("VALID:", report.valid)

for error in report.errors:
    print("[ERROR]", error)

for warning in report.warnings:
    print("[WARNING]", warning)
```

### Current validation responsibilities

The current implementation checks:

- Required metadata and entity fields.
- Whether the object is an entity.
- Whether registered attribute references exist.
- Whether registered skill references exist.
- Whether personality facet references exist.
- Whether personality value references exist.
- Whether the supplied values are numeric.
- Whether numeric values are whole numbers.
- Whether values fall within the applicable definition limits.
- Whether duplicate entries or malformed group names occur.

The validator currently has fallback limits for personality facets and values of 0–100.

Entity roles and species are checked against registries. Sectors belong to a game save and are not an entity identity field. Hardcore is stored as a tag but has no gameplay implementation yet.

---

# 8. The Parsing Pipeline

The intended overall flow is:

```text
             .txt data file
                   |
                   v
             Tag Parser
                   |
                   v
              TagDocument
                   |
                   v
            Object Dispatcher
                   |
          +--------+--------+
          |                 |
          v                 v
     Entity Parser     Other Parsers
          |
          v
     Entity Object
          |
          v
    Entity Validator
          |
          v
    Registry Manager
          |
          v
    Validated Entity
```

### Responsibilities

**Tag Parser**

Reads the raw file and produces a structured document.

**Object Dispatcher**

Identifies the object's type and routes it to the appropriate parser.

**Entity Parser**

Interprets entity-specific fields and produces an entity representation.

**Registry Manager**

Provides access to registered entries and their definitions.

**Entity Validator**

Checks whether the entity's contents are valid against the available registries and definitions.

The universal tag parser should not contain entity-specific logic.

Likewise, the entity parser should not independently implement the universal tag-reading format.

---

# 9. Object Dispatcher and Entity Parser

The project contains:

```text
engine/parsing/object_dispatcher.py
engine/parsing/entity_parser.py
```

These modules are intended to support the type-specific parsing layer.

Their responsibilities should remain distinct:

### Object Dispatcher

- Determine the object's type using `object.type`.
- Select the appropriate parser.
- Pass the parsed document to that parser.
- Report unknown object types.
- Prevent conflicting parser registrations.

The previous public API included:

```python
from engine.parsing.object_dispatcher import (
    ObjectDispatcher,
    ObjectDispatcherError,
    UnknownObjectTypeError,
    DuplicateParserError,
    dispatcher,
    parse_object,
)
```

### Entity Parser

- Interpret entity-specific tags.
- Organise entity identity, attributes, skills, personality, and other fields.
- Produce an entity representation.
- Avoid duplicating universal tag parsing.

The previous public API included:

```python
from engine.parsing.entity_parser import (
    Entity,
    EntityParseError,
    parse_entity,
)
```

**Important:** The exact constructor signatures, return types, and internal methods of these two modules must be checked against their actual implementations before modifying or extending them. Do not invent new interfaces based solely on this documentation.

---

# 10. Complete Registry and Validation Test

The following is the current working test script.

**File:** `test_registry.py`

```python
from pathlib import Path

from engine.parsing.tag_parser import parse_file
from engine.registries.registry_manager import RegistryManager
from engine.validation.entity_validator import EntityValidator


# ==========================================
# 1. PROJECT PATHS
# ==========================================

PROJECT_ROOT = Path(__file__).resolve().parent

ENTITY_PATH = (
    PROJECT_ROOT
    / "data"
    / "compendium"
    / "entities"
    / "tributes"
    / "tribute_001.txt"
)


# ==========================================
# 2. DISPLAY HELPERS
# ==========================================

def print_section(title):
    print(f"\n{'=' * 10} {title} {'=' * 10}")


def display_report(report):

    print("\nVALID:", report.valid)

    print("\nERRORS:")

    if report.errors:
        for error in report.errors:
            print(f"  [ERROR] {error}")
    else:
        print("  None")

    print("\nWARNINGS:")

    if report.warnings:
        for warning in report.warnings:
            print(f"  [WARNING] {warning}")
    else:
        print("  None")


# ==========================================
# 3. LOAD REGISTRIES
# ==========================================

def load_registries():

    print_section("LOADING REGISTRIES")

    registries = RegistryManager(PROJECT_ROOT)

    for family, entries in registries.registries.items():

        print(f"\n{family.upper()}: {len(entries)} registered")

        for name, definition_id in entries.items():
            print(f"  {name} -> {definition_id}")

    print(
        f"\nIndexed definitions: "
        f"{len(registries.definition_index)}"
    )

    return registries


# ==========================================
# 4. LOAD ENTITY
# ==========================================

def load_entity():

    print_section("LOADING ENTITY")

    if not ENTITY_PATH.is_file():
        raise FileNotFoundError(
            f"Entity file not found: {ENTITY_PATH}"
        )

    entity = parse_file(ENTITY_PATH)

    print("Name:", entity.get("entity.name"))
    print("ID:", entity.get("object.id"))
    print("Type:", entity.get("object.type"))
    print("Entity role:", entity.get("entity.role"))

    print("Total tag entries:", len(entity.entries))

    return entity


# ==========================================
# 5. VALIDATE ENTITY
# ==========================================

def validate_entity(entity, registries):

    print_section("ENTITY VALIDATION")

    validator = EntityValidator(registries)

    report = validator.validate(entity)

    display_report(report)

    return report


# ==========================================
# 6. MAIN
# ==========================================

def main():

    print("\n")
    print("#" * 50)
    print("       BEYOND THE ARENA - REGISTRY TEST")
    print("#" * 50)

    registries = load_registries()

    entity = load_entity()

    report = validate_entity(
        entity,
        registries
    )

    print_section("FINAL RESULT")

    if report.valid:
        print("Entity passed validation.")
    else:
        print("Entity failed validation.")

    print(
        f"\nErrors: {len(report.errors)}"
        f"\nWarnings: {len(report.warnings)}"
    )

    print("\n" + "#" * 50)


if __name__ == "__main__":
    main()
```

Run it from the `Game` directory:

```powershell
.\venv\Scripts\python.exe test_registry.py
```

### Last confirmed test result

```text
ATTRIBUTES: 6 registered
SKILLS: 10 registered
FACETS: 50 registered
VALUES: 16 registered

Indexed definitions: 82

Name: Katniss Everdeen
ID: entity.tribute.001
Type: entity
Entity category: tribute
Total tag entries: 100

VALID: True

ERRORS:
  None

WARNINGS:
  None

Entity passed validation.
```

This confirms that the current registry loading, definition indexing, tag parsing, and entity validation pipeline works for the tested entity.

---

# 11. Rules for Future Development

Any AI or developer working on this project must follow these rules.

## Data architecture

1. Keep game data in `.txt` tag-value files.
2. Keep Python responsible for interpreting and processing that data.
3. Do not hardcode lists of attributes, skills, facets, values, or other registry entries into Python.
4. Use registries as the authoritative source of recognised entries.
5. Use definitions as the authoritative source of entry properties.
6. Keep actual character data in the appropriate compendium or runtime instance files.
7. Do not duplicate definitions inside entity files.
8. Keep universal metadata consistent.

## Parser architecture

1. `tag_parser.py` must remain universal.
2. Do not put entity-specific logic into the universal parser.
3. Use the object dispatcher for type-specific parser selection.
4. Keep each object parser responsible for its own object type.
5. Do not duplicate parsing functionality across modules.
6. Preserve repeated tags and their values.
7. Keep parsed values as strings until explicit conversion is needed.
8. Handle malformed files with meaningful exceptions.

## Registry architecture

1. New registered entries should be discovered through registry files.
2. Definitions should be resolved through their IDs.
3. Avoid hardcoding physical file paths when an ID lookup is available.
4. Ensure IDs are unique.
5. Ensure registry references resolve to existing definitions.
6. Do not silently accept invalid registry files.
7. Avoid requiring Python changes for ordinary data additions.

## Validation architecture

1. Validate references against registries.
2. Validate numeric values against their definitions.
3. Distinguish errors from warnings.
4. Do not silently ignore invalid data.
5. Keep validation separate from parsing.
6. Do not make the universal parser responsible for deciding whether an entity is valid.

## General development

1. Preserve existing working functionality.
2. Inspect the existing implementation before changing a module.
3. Do not assume a method or class exists without checking its actual source.
4. Do not introduce unnecessary modules or duplicate responsibilities.
5. Prefer reusable, registry-driven solutions over individual hardcoded implementations.
6. When modifying an interface, update all dependent imports and callers.
7. Explain any required changes to existing data files when changing the parsing or validation system.

---

# 12. Current Implementation Status

| Component | Status |
|---|---|
| Universal tag parser | Implemented and tested |
| TagDocument methods | Implemented and tested |
| Registry manager | Implemented and tested |
| Attribute registry loading | Working |
| Skill registry loading | Working |
| Personality facet registry loading | Working |
| Personality value registry loading | Working |
| Definition indexing | Working |
| Entity validator | Implemented and tested |
| Katniss entity validation | Passed |
| Entity parser | Exists; implementation needs inspection before extending |
| Object dispatcher | Exists; implementation needs inspection before extending |
| Automatic compendium loading | Not confirmed as integrated |
| Validation of all entity references | Not yet confirmed |
| Runtime instance loading and saving | Future integration |

**Final instruction to future AI assistants:** Treat this document as the architectural specification, but treat the actual Python source files as the authority on current method signatures and implementation details. If the two disagree, identify the discrepancy before changing code. Do not invent missing functionality or claim that an unimplemented feature already exists.
