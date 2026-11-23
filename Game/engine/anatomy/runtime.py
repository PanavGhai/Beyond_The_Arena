"""Runtime anatomy instances with per-instance parent links."""
from dataclasses import dataclass, field
from engine.anatomy.definitions import AnatomyLoader, SpeciesDefinition

@dataclass
class BodyPartInstance:
    id: str
    part_type: str
    parent_id: str | None
    max_hp: float
    current_hp: float
    destroyed: bool = False
    injuries: list[dict] = field(default_factory=list)
    instant_death_on_loss: bool = False

@dataclass
class AnatomyState:
    species_id: str
    parts: dict[str, BodyPartInstance]
    species_hp_multiplier: float = 1.0
    base_max_hp: float = 100.0
    dead: bool = False
    injuries: dict[str, list[dict]] = field(default_factory=dict)
    vitality_groups: tuple = ()

    @classmethod
    def create(cls, species: SpeciesDefinition, loader: AnatomyLoader, base_max_hp=100.0):
        parts = {}
        for spec in species.parts:
            definition = loader.load_part(spec.part_type)
            maximum = definition.base_hp * definition.hp_multiplier * spec.hp_multiplier * species.hp_multiplier
            parts[spec.instance_id] = BodyPartInstance(spec.instance_id, spec.part_type, spec.parent_id, maximum, maximum)
            parts[spec.instance_id].instant_death_on_loss = definition.instant_death_on_loss
        return cls(species.id, parts, species.hp_multiplier, float(base_max_hp), vitality_groups=species.vitality_groups)

    def children_of(self, instance_id):
        return [part for part in self.parts.values() if part.parent_id == instance_id and not part.destroyed]

    def damage(self, instance_id, amount, *, internal=False, loader=None):
        if amount < 0:
            raise ValueError("Damage amount cannot be negative")
        part = self._part(instance_id)
        if loader is None:
            raise ValueError("AnatomyLoader is required to enforce internal-part damage rules")
        definition = loader.load_part(part.part_type)
        if definition.internal and not internal:
            raise ValueError(f"{instance_id} is internal; damage must be marked internal")
        if part.destroyed:
            return 0.0
        part.current_hp = max(0.0, part.current_hp - amount)
        if part.current_hp == 0:
            self.destroy(instance_id, loader=loader)
        return part.current_hp

    def destroy(self, instance_id, *, loader=None):
        self._part(instance_id)
        lost, stack = [], [instance_id]
        while stack:
            current = stack.pop()
            part = self.parts[current]
            if part.destroyed:
                continue
            part.destroyed = True
            part.current_hp = 0.0
            lost.append(current)
            stack.extend(child.id for child in self.children_of(current))
        if any(self.parts[key].instant_death_on_loss for key in lost):
            self.dead = True
        for group in self.vitality_groups:
            values = [self.parts[key].destroyed for key in group.part_ids]
            if (group.death_condition == "all_destroyed" and all(values)) or (
                group.death_condition == "any_destroyed" and any(values)) or (
                group.death_condition == "threshold_destroyed" and sum(values) >= group.threshold):
                self.dead = True
        return lost

    def movement_multiplier(self, loader):
        result = 1.0
        for part in self.parts.values():
            if part.destroyed:
                result *= loader.load_part(part.part_type).movement_multiplier
        return result

    def current_max_hp(self):
        # Character max HP is independent from the sum of body-part HP.
        return max(0.0, self.base_max_hp - self._vitality_hp_loss())

    def _vitality_hp_loss(self):
        loss = 0.0
        base_max = self.base_max_hp
        for group in self.vitality_groups:
            destroyed_count = sum(self.parts[key].destroyed for key in group.part_ids)
            total_count = len(group.part_ids)
            if not group.hp_loss_on_failure or not destroyed_count:
                continue
            if group.death_condition == "all_destroyed":
                failed = destroyed_count == total_count
            elif group.death_condition == "any_destroyed":
                failed = destroyed_count > 0
            elif group.death_condition == "threshold_destroyed":
                failed = destroyed_count >= group.threshold
            else:  # never
                failed = False
            if group.hp_loss_per_part:
                count = destroyed_count
            elif failed:
                count = 1
            else:
                count = 0
            unit_loss = (base_max * group.hp_loss_amount if group.hp_loss_type == "percentage"
                         else group.hp_loss_amount)
            loss += unit_loss * count
        return loss

    def _part(self, instance_id):
        try:
            return self.parts[instance_id]
        except KeyError as error:
            raise KeyError(f"Unknown body part instance: {instance_id}") from error

    def to_dict(self):
        return {"species_id": self.species_id, "species_hp_multiplier": self.species_hp_multiplier,
                "base_max_hp": self.base_max_hp, "dead": self.dead,
                "parts": {key: vars(part).copy() for key, part in self.parts.items()},
                "injuries": self.injuries,
                "vitality_groups": [{"name": g.name, "part_ids": list(g.part_ids),
                                     "death_condition": g.death_condition,
                                     "hp_loss_on_failure": g.hp_loss_on_failure,
                                     "hp_loss_type": g.hp_loss_type,
                                     "hp_loss_amount": g.hp_loss_amount,
                                     "hp_loss_per_part": g.hp_loss_per_part,
                                     "threshold": g.threshold}
                                    for g in self.vitality_groups]}

    @classmethod
    def from_dict(cls, data):
        from engine.anatomy.definitions import VitalityGroup
        parts = {key: BodyPartInstance(**value) for key, value in data["parts"].items()}
        groups = tuple(VitalityGroup(g["name"], tuple(g["part_ids"]), g["death_condition"],
                                     g.get("hp_loss_on_failure", False), g.get("hp_loss_type", "percentage"),
                                     g.get("hp_loss_amount", 0.0), g.get("hp_loss_per_part", False),
                                     g.get("threshold"))
                       for g in data.get("vitality_groups", []))
        return cls(data["species_id"], parts, data.get("species_hp_multiplier", 1.0),
                   data.get("base_max_hp", 100.0), data.get("dead", False),
                   data.get("injuries", {}), groups)
