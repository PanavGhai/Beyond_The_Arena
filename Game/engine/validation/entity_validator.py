
# engine/validation/entity_validator.py

from dataclasses import dataclass, field


# ==========================================
# 1. VALIDATION REPORT
# ==========================================

@dataclass
class ValidationReport:

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def valid(self):
        return len(self.errors) == 0

    def add_error(self, message):
        self.errors.append(message)

    def add_warning(self, message):
        self.warnings.append(message)

    def to_dict(self):
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


# ==========================================
# 2. ENTITY VALIDATOR
# ==========================================

class EntityValidator:
    """
    Validates entity documents against the
    loaded registries and their definitions.
    """

    REQUIRED_FIELDS = [
        "object.type",
        "object.id",
        "object.version",
        "entity.role",
        "entity.name",
    ]

    GROUPS = {
        "entity.attributes.": "attributes",
        "entity.skills.": "skills",
        "entity.personality.facets.": "facets",
        "entity.personality.values.": "values",
    }

    # Temporary fallback until facet and value
    # definitions specify their own limits.
    FALLBACK_LIMITS = {
        "facets": (0, 100),
        "values": (0, 100),
    }

    def __init__(self, registry_manager):
        self.registries = registry_manager


    # ======================================
    # 3. MAIN VALIDATION
    # ======================================

    def validate(self, document):
        """
        Validate a parsed entity document.
        """

        report = ValidationReport()

        self._validate_required_fields(
            document,
            report
        )

        if document.get("object.type") != "entity":
            report.add_error(
                "Object type must be 'entity'."
            )

            return report

        self._validate_entity_groups(
            document,
            report
        )

        role = document.get("entity.role")
        if role and not self.registries.contains("roles", role):
            report.add_error(f"Unregistered entity role: {role} (entity.role)")

        # Species references are optional, but when present they must resolve
        # through the additive species registry family.
        species_reference = document.get("entity.species")
        if species_reference:
            species_name = species_reference.rsplit(".", 1)[-1]
            if not self.registries.contains("species", species_name):
                report.add_error(
                    f"Unregistered species: {species_reference} (entity.species)"
                )

        return report


    # ======================================
    # 4. REQUIRED FIELDS
    # ======================================

    def _validate_required_fields(self, document, report):

        for tag in self.REQUIRED_FIELDS:

            if not document.has(tag):
                report.add_error(
                    f"Missing required field: {tag}"
                )

            elif not document.get(tag):
                report.add_error(
                    f"Required field cannot be empty: {tag}"
                )


    # ======================================
    # 5. GROUP VALIDATION
    # ======================================

    def _validate_entity_groups(self, document, report):

        for prefix, family in self.GROUPS.items():

            entries = [
                entry
                for entry in document.entries
                if entry.tag.startswith(prefix)
            ]

            seen = set()

            for entry in entries:

                name = entry.tag[len(prefix):]

                if not name:
                    report.add_error(
                        f"Invalid empty entry in {prefix}"
                    )
                    continue

                if "." in name:
                    report.add_error(
                        f"Unexpected nested tag: {entry.tag}"
                    )
                    continue

                if name in seen:
                    report.add_error(
                        f"Duplicate entity entry: {entry.tag}"
                    )
                    continue

                seen.add(name)

                self._validate_registered_value(
                    family=family,
                    name=name,
                    value=entry.value,
                    tag=entry.tag,
                    report=report
                )


    # ======================================
    # 6. REGISTRY VALIDATION
    # ======================================

    def _validate_registered_value(
        self,
        family,
        name,
        value,
        tag,
        report
    ):

        if not self.registries.contains(family, name):
            report.add_error(
                f"Unregistered {family[:-1] if family != 'values' else 'value'}: "
                f"{name} ({tag})"
            )

            return

        definition_id = self.registries.get_definition_id(
            family,
            name
        )

        definition = self.registries.resolve_definition(
            definition_id
        )

        if definition is None:

            report.add_error(
                f"Missing definition '{definition_id}' "
                f"referenced by {tag}."
            )

            return

        self._validate_numeric_value(
            family=family,
            name=name,
            value=value,
            tag=tag,
            report=report
        )


    # ======================================
    # 7. NUMERIC VALIDATION
    # ======================================

    def _validate_numeric_value(
        self,
        family,
        name,
        value,
        tag,
        report
    ):

        try:
            numeric_value = float(value)

        except (ValueError, TypeError):
            report.add_error(
                f"Value for {tag} must be numeric; received '{value}'."
            )
            return

        if not numeric_value.is_integer():
            report.add_error(
                f"Value for {tag} must be a whole number; "
                f"received '{value}'."
            )
            return

        minimum, maximum = self.registries.get_numeric_limits(
            family,
            name
        )

        # Apply temporary fallback limits only
        # when the definition does not specify them.
        if family in self.FALLBACK_LIMITS:

            fallback_min, fallback_max = (
                self.FALLBACK_LIMITS[family]
            )

            if minimum is None:
                minimum = str(fallback_min)

            if maximum is None:
                maximum = str(fallback_max)

        try:

            if minimum is not None:
                minimum = float(minimum)

            if maximum is not None:
                maximum = float(maximum)

        except (ValueError, TypeError):

            report.add_error(
                f"Invalid numerical limits in the definition "
                f"of '{name}'."
            )
            return

        if minimum is not None and numeric_value < minimum:

            report.add_error(
                f"{tag} is below its minimum of {minimum:g}."
            )

        if maximum is not None and numeric_value > maximum:

            report.add_error(
                f"{tag} exceeds its maximum of {maximum:g}."
            )
