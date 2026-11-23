"""Load species anatomy from registered tag definitions."""
from dataclasses import dataclass
from math import isfinite

class AnatomyValidationError(ValueError):
    """Invalid anatomy or species definition."""

@dataclass(frozen=True)
class PartDefinition:
    name: str
    base_hp: float
    hp_multiplier: float = 1.0
    internal: bool = False
    vital: bool = False
    instant_death_on_loss: bool = False
    movement_multiplier: float = 1.0
    bleed_chance: float = 0.0
    pain_sensitivity: float = 1.0
    enabled: bool = True

@dataclass(frozen=True)
class PartSpec:
    instance_id: str
    part_type: str
    parent_id: str | None = None
    hp_multiplier: float = 1.0

@dataclass(frozen=True)
class VitalityGroup:
    name: str
    part_ids: tuple[str, ...]
    death_condition: str
    hp_loss_on_failure: bool = False
    hp_loss_type: str = "percentage"
    hp_loss_amount: float = 0.0
    hp_loss_per_part: bool = False
    threshold: int | None = None

@dataclass(frozen=True)
class SpeciesDefinition:
    id: str
    name: str
    hp_multiplier: float
    parts: tuple[PartSpec, ...]
    vitality_groups: tuple[VitalityGroup, ...]
    document: object

def _number(document, tag, default):
    raw = document.get(tag)
    if raw is None:
        return default
    try:
        value = float(raw)
    except (TypeError, ValueError) as error:
        raise AnatomyValidationError(f"{tag} must be numeric; got {raw!r}") from error
    if not isfinite(value):
        raise AnatomyValidationError(f"{tag} must be finite")
    return value

def _boolean(document, tag, default=False):
    raw = document.get(tag)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in ("true", "1", "yes"):
        return True
    if normalized in ("false", "0", "no"):
        return False
    raise AnatomyValidationError(f"{tag} must be a boolean; got {raw!r}")

class AnatomyLoader:
    """Resolve part and species definitions through RegistryManager."""
    def __init__(self, registries):
        self.registries = registries

    def load_part(self, name):
        document = self.registries.get_definition("body_parts", name)
        if document is None:
            raise AnatomyValidationError(f"Unregistered or missing body part: {name}")
        if document.get("object.type") != "body_part":
            raise AnatomyValidationError(f"{name} definition must have object.type=body_part")
        part = PartDefinition(
            name=name, base_hp=_number(document, "body_part.base_hp", 1.0),
            hp_multiplier=_number(document, "body_part.hp_multiplier", 1.0),
            internal=_boolean(document, "body_part.internal"),
            vital=_boolean(document, "body_part.vital"),
            instant_death_on_loss=_boolean(document, "body_part.instant_death_on_loss"),
            movement_multiplier=_number(document, "body_part.movement_multiplier", 1.0),
            bleed_chance=_number(document, "body_part.bleed_chance", 0.0),
            pain_sensitivity=_number(document, "body_part.pain_sensitivity", 1.0),
            enabled=_boolean(document, "body_part.enabled", True))
        if part.base_hp <= 0 or part.hp_multiplier <= 0 or part.pain_sensitivity < 0:
            raise AnatomyValidationError(f"Invalid HP or pain value in {name}")
        if not 0 <= part.movement_multiplier <= 1:
            raise AnatomyValidationError(f"{name} movement_multiplier must be between 0 and 1")
        if not 0 <= part.bleed_chance <= 1:
            raise AnatomyValidationError(f"{name} bleed_chance must be between 0 and 1")
        return part

    def load_species(self, name):
        document = self.registries.get_definition("species", name)
        if document is None:
            raise AnatomyValidationError(f"Unregistered or missing species: {name}")
        if document.get("object.type") != "species":
            raise AnatomyValidationError(f"{name} definition must have object.type=species")
        species_id = document.get("object.id", "")
        hp_multiplier = _number(document, "species.hp_multiplier", 1.0)
        if hp_multiplier <= 0:
            raise AnatomyValidationError(f"{species_id} species.hp_multiplier must be positive")
        grouped = {}
        prefix = "species.body_parts."
        for entry in document.entries:
            if entry.tag.startswith(prefix):
                rest = entry.tag[len(prefix):]
                if "." not in rest:
                    raise AnatomyValidationError(f"Expected an instance field in {entry.tag}")
                instance_id, field = rest.rsplit(".", 1)
                fields = grouped.setdefault(instance_id, {})
                if field in fields:
                    raise AnatomyValidationError(f"Duplicate species anatomy field: {entry.tag}")
                fields[field] = entry.value
        if not grouped:
            raise AnatomyValidationError(f"{species_id} defines no body part instances")
        parts = []
        for instance_id, fields in grouped.items():
            part_type = fields.get("type")
            if not instance_id or not part_type:
                raise AnatomyValidationError(f"{species_id} instance {instance_id!r} needs a type")
            part_definition = self.load_part(part_type)
            if not part_definition.enabled:
                raise AnatomyValidationError(f"{species_id} uses disabled body-part type {part_type}")
            try:
                multiplier = float(fields.get("hp_multiplier", "1"))
            except ValueError as error:
                raise AnatomyValidationError(f"{instance_id} hp_multiplier must be numeric") from error
            if not isfinite(multiplier) or multiplier <= 0:
                raise AnatomyValidationError(f"{instance_id} hp_multiplier must be positive")
            parts.append(PartSpec(instance_id, part_type, fields.get("parent") or None, multiplier))
        ids = {part.instance_id for part in parts}
        for part in parts:
            if part.parent_id and part.parent_id not in ids:
                raise AnatomyValidationError(f"{species_id}:{part.instance_id} references missing parent {part.parent_id}")
            if part.parent_id == part.instance_id:
                raise AnatomyValidationError(f"{species_id}:{part.instance_id} cannot parent itself")
        self._validate_acyclic(species_id, {part.instance_id: part.parent_id for part in parts})
        groups = {}
        prefix = "species.vitality_groups."
        for entry in document.entries:
            if entry.tag.startswith(prefix):
                rest = entry.tag[len(prefix):]
                if "." not in rest:
                    raise AnatomyValidationError(f"Expected vitality group field in {entry.tag}")
                group_name, field = rest.rsplit(".", 1)
                groups.setdefault(group_name, {"parts": []})
                if field == "part":
                    groups[group_name]["parts"].append(entry.value)
                else:
                    groups[group_name][field] = entry.value
        vitality_groups = []
        for group_name, fields in groups.items():
            requested = tuple(fields["parts"])
            members_list = []
            for reference in requested:
                if reference in ids:
                    members_list.append(reference)
                else:
                    members_list.extend(p.instance_id for p in parts if p.part_type == reference)
            members = tuple(dict.fromkeys(members_list))
            condition = fields.get("death_condition", "all_destroyed")
            if not members:
                raise AnatomyValidationError(f"{species_id} vitality group {group_name} has missing parts")
            if condition not in ("all_destroyed", "any_destroyed", "threshold_destroyed", "never"):
                raise AnatomyValidationError(f"Unsupported death condition {condition!r} in {group_name}")
            hp_loss_type = fields.get("hp_loss_type", "percentage")
            hp_loss_amount = float(fields.get("hp_loss_amount", "0"))
            if hp_loss_type not in ("percentage", "flat") or not isfinite(hp_loss_amount) or hp_loss_amount < 0:
                raise AnatomyValidationError(f"Invalid max HP loss configuration in {group_name}")
            if hp_loss_type == "percentage" and hp_loss_amount > 1:
                raise AnatomyValidationError(f"{group_name} percentage HP loss must be between 0 and 1")
            hp_loss_enabled = _parse_bool(fields.get("hp_loss_on_failure", "false"), group_name)
            per_part = _parse_bool(fields.get("hp_loss_per_part", "false"), group_name)
            threshold = None
            if condition == "threshold_destroyed":
                try:
                    threshold = int(fields.get("threshold", ""))
                except ValueError as error:
                    raise AnatomyValidationError(f"{group_name} requires an integer destruction threshold") from error
                if not 1 <= threshold <= len(members):
                    raise AnatomyValidationError(f"{group_name} threshold must be between 1 and its member count")
            vitality_groups.append(VitalityGroup(
                group_name, members, condition, hp_loss_enabled,
                hp_loss_type, hp_loss_amount, per_part, threshold
            ))
        return SpeciesDefinition(species_id, document.get("species.name", name), hp_multiplier,
                                 tuple(parts), tuple(vitality_groups), document)

    @staticmethod
    def _validate_acyclic(species_id, parents):
        for start in parents:
            seen, current = set(), start
            while current:
                if current in seen:
                    raise AnatomyValidationError(f"{species_id} attachment cycle at {current}")
                seen.add(current)
                current = parents.get(current)

    def validate_all(self):
        parts = {name: self.load_part(name) for name in self.registries.get_registered_entries("body_parts")}
        species = {name: self.load_species(name) for name in self.registries.get_registered_entries("species")}
        return {"body_parts": parts, "species": species}


def _parse_bool(value, context):
    normalized = value.strip().lower()
    if normalized in ("true", "1", "yes"):
        return True
    if normalized in ("false", "0", "no"):
        return False
    raise AnatomyValidationError(f"{context} boolean value is invalid: {value!r}")
