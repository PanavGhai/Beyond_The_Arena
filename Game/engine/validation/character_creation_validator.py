"""Server-side validation for new-character form submissions."""

from math import isfinite
from math import floor
from urllib.parse import urlparse

from engine.validation.entity_validator import ValidationReport


class CharacterCreationValidator:
    def validate(self, form, references):
        report = ValidationReport()
        settings = references["settings"]
        role_by_id = {item["id"]: item for item in references["roles"]}
        species_ids = {item["id"] for item in references["species"]}
        gender_values = {item["name"] for item in references["genders"]}
        pronoun_values = {item["name"] for item in references["pronouns"]}

        def required(key, label):
            value = form.get(key, "").strip()
            if not value:
                report.add_error(f"{label} is required.")
            return value

        name = required("name", "Name")
        role = required("role", "Role")
        species = required("species", "Species")
        pronouns = required("pronouns", "Pronouns")
        gender = required("gender", "Gender")
        if role and role not in role_by_id:
            report.add_error("Select a role from the registered roles.")
        hardcore = form.get("hardcore", "").strip().lower() in ("true", "on", "1")
        if hardcore and role != "tributes":
            report.add_error("Hardcore can only be enabled for Tributes.")
        if species and species not in species_ids:
            report.add_error("Select a species from the species registry.")
        if role == "tributes" and species != "species.human":
            report.add_error("Tributes must use the Human species.")
        if pronouns and pronouns not in pronoun_values:
            report.add_error("Select pronouns from the pronouns registry.")
        if gender and gender not in gender_values:
            report.add_error("Select a gender from the genders registry.")
        if len(name) > 100:
            report.add_error("Name cannot exceed 100 characters.")
        if len(form.get("nickname", "")) > 100:
            report.add_error("Nickname cannot exceed 100 characters.")
        if len(form.get("description", "")) > 2000:
            report.add_error("Description cannot exceed 2,000 characters.")

        def number(key, label, minimum, maximum, integer=False):
            raw = form.get(key, "").strip()
            if not raw:
                report.add_error(f"{label} is required.")
                return None
            try:
                value = int(raw) if integer else float(raw)
            except ValueError:
                report.add_error(f"{label} must be a {'whole number' if integer else 'number'}.")
                return None
            if not isfinite(value) or not minimum <= value <= maximum:
                report.add_error(f"{label} must be between {minimum:g} and {maximum:g}.")
                return None
            return value

        number("age", "Age", float(settings.get("character_creation.identity.age.minimum", "13")),
               float(settings.get("character_creation.identity.age.maximum", "99999")), integer=True)
        number("height_cm", "Height (cm)", float(settings.get("character_creation.identity.height_cm.minimum", "60")),
               float(settings.get("character_creation.identity.height_cm.maximum", "500")))
        number("weight_kg", "Weight (kg)", float(settings.get("character_creation.identity.weight_kg.minimum", "30")),
               float(settings.get("character_creation.identity.weight_kg.maximum", "9999")))

        portrait = required("portrait_url", "Portrait URL")
        death_portrait = form.get("death_portrait_url", "").strip()
        for label, value in (("Portrait URL", portrait), ("Death portrait URL", death_portrait)):
            if value and value.lower() != "bw":
                parsed = urlparse(value)
                if parsed.scheme not in ("http", "https") or not parsed.netloc:
                    report.add_error(f"{label} must be an http or https URL.")

        attributes = references["attributes"]
        attribute_ids = {item["id"] for item in attributes}
        attribute_points = 0
        for item in attributes:
            value = number(f"attribute_{item['id']}", item["name"], item["minimum"], item["maximum"], integer=True)
            if value is not None:
                attribute_points += value - item["default"]
        unknown_attributes = self._submitted_ids(form, "attribute_") - attribute_ids
        if unknown_attributes:
            report.add_error(f"Unregistered attributes: {', '.join(sorted(unknown_attributes))}.")
        attribute_budget = int(settings.get("character_creation.attribute.additional_points", "18"))
        if attribute_points != attribute_budget:
            report.add_error(f"Attribute allocation must use exactly {attribute_budget} additional points.")

        skills = references["skills"]
        skill_ids = {item["id"] for item in skills}
        skill_points = 0
        for item in skills:
            creation_max = min(item["maximum"], item["creation_maximum"])
            value = number(f"skill_{item['id']}", item["name"], item["minimum"], creation_max, integer=True)
            if value is not None:
                skill_points += value - item["default"]
        unknown_skills = self._submitted_ids(form, "skill_") - skill_ids
        if unknown_skills:
            report.add_error(f"Unregistered skills: {', '.join(sorted(unknown_skills))}.")
        skill_budget = int(settings.get("character_creation.skill.additional_points_per_registered_skill", "3")) * len(skills)
        if skill_points != skill_budget:
            report.add_error(f"Skill allocation must use exactly {skill_budget} additional points.")

        for family, prefix in (("facets", "facet_"), ("values", "value_")):
            entries = references[family]
            ids = {item["id"] for item in entries}
            for item in entries:
                number(f"{prefix}{item['id']}", item["name"], item["minimum"], item["maximum"], integer=True)
            unknown = self._submitted_ids(form, prefix) - ids
            if unknown:
                report.add_error(f"Unregistered {family}: {', '.join(sorted(unknown))}.")

            by_id = {item["id"]: item for item in entries}
            for item in entries:
                opposite_id = item.get("opposite", "")
                if not opposite_id:
                    continue
                opposite = by_id.get(opposite_id)
                if opposite is None or opposite.get("opposite") != item["id"]:
                    report.add_error(f"Invalid opposite link for {item['name']}.")
                    continue
                if item["id"] >= opposite_id:
                    continue
                try:
                    current = float(form.get(f"{prefix}{item['id']}", ""))
                    other = int(form.get(f"{prefix}{opposite_id}", ""))
                except (TypeError, ValueError):
                    continue
                span = item["maximum"] - item["minimum"]
                ratio = (current - item["minimum"]) / span if span else 0
                expected = floor(opposite["maximum"] - ratio * (opposite["maximum"] - opposite["minimum"]) + 0.5)
                if other != expected:
                    report.add_error(f"{item['name']} and {opposite['name']} must use opposite values.")

        return report

    @staticmethod
    def _submitted_ids(form, prefix):
        return {key[len(prefix):] for key in form.keys() if key.startswith(prefix)}
