
# test_registry.py

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
    / "tributes_001.txt"
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
    print("Type:", entity.get("entity.role"))
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


# ==========================================
# 7. ENTRY POINT
# ==========================================

if __name__ == "__main__":
    main()
