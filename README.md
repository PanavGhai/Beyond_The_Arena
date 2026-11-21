# Beyond_The_Arena

An open development Hunger Games-inspired simulator. Publicly viewable, but all rights reserved. Commercial use, redistribution, and modification are not permitted without explicit permission from the author.

# Beyond the Arena — Data & Engine Architecture

## 1. Project Overview

Beyond the Arena is a Hunger Games-inspired simulation built with Python and Flask.

The project separates three major responsibilities:

1. **Data:** Stores definitions, templates, configuration and reusable game content.
2. **Engine:** Processes game rules, calculations, interactions and simulation logic.
3. **Interface:** Presents the simulation to the user through the Flask application.

The engine must remain independent of Flask so that the simulation can eventually operate through other interfaces without rewriting its core logic.

### Core architectural principles

- Use plain-text `.txt` files for structured game data.
- Use a consistent tag-value format for all definitions and records.
- Keep reusable definitions separate from individual runtime instances.
- Use registries to define valid tags, types and references.
- Avoid hardcoding game content into Python.
- Make systems modular and independently maintainable.
- Use references between objects rather than duplicating definitions.
- Support multiple classifications and capabilities for a single object.
- Keep gameplay rules configurable wherever practical.

---

# 2. Project Directory Structure

```text
Game/
│
├── app/
│   ├── routes/
│   ├── templates/
│   └── static/
│
├── assets/
│   ├── portraits/
│   ├── tokens/
│   ├── maps/
│   └── ui/
│
├── config/
│   ├── tag_registry.txt
│   ├── effect_registry.txt
│   └── settings.txt
│
├── data/
│   │
│   ├── entities/
│   │   ├── tributes/
│   │   ├── npcs/
│   │   ├── mentors/
│   │   ├── sponsors/
│   │   └── wildlife/
│   │
│   ├── items/
│   │   ├── weapons/
│   │   ├── tools/
│   │   ├── resources/
│   │   ├── consumables/
│   │   ├── equipment/
│   │   └── materials/
│   │
│   ├── classifications/
│   │   ├── items/
│   │   ├── combat/
│   │   └── general/
│   │
│   ├── capabilities/
│   │   ├── combat/
│   │   ├── tools/
│   │   ├── survival/
│   │   ├── crafting/
│   │   └── general/
│   │
│   ├── skills/
│   │   ├── combat/
│   │   │   ├── melee/
│   │   │   └── marksmanship/
│   │   ├── survival/
│   │   ├── crafting/
│   │   └── general/
│   │
│   ├── abilities/
│   │   └── actions/
│   │       ├── combat/
│   │       ├── tools/
│   │       ├── survival/
│   │       ├── crafting/
│   │       └── general/
│   │
│   ├── traits/
│   ├── statuses/
│   ├── conditions/
│   ├── injuries/
│   ├── effects/
│   │   ├── stat_modifiers/
│   │   ├── capabilities/
│   │   ├── restrictions/
│   │   └── special/
│   │
│   ├── anatomy/
│   │   ├── body_parts/
│   │   └── templates/
│   │
│   ├── species/
│   ├── attributes/
│   ├── personality/
│   │   └── facets/
│   │
│   ├── options/
│   │   ├── pronouns/
│   │   ├── roles/
│   │   ├── genders/
│   │   ├── districts/
│   │   └── other/
│   │
│   ├── maps/
│   │   ├── catalogue/
│   │   ├── templates/
│   │   ├── environments/
│   │   └── generated/
│   │
│   ├── events/
│   │   ├── arena/
│   │   ├── encounters/
│   │   ├── sponsor/
│   │   └── weather/
│   │
│   ├── factions/
│   ├── relationships/
│   ├── wildlife/
│   └── other/
│
├── engine/
│   ├── data/
│   │   ├── manager.py
│   │   ├── parser.py
│   │   ├── references.py
│   │   ├── registry.py
│   │   ├── saving.py
│   │   └── validation.py
│   │
│   ├── entities/
│   ├── characters/
│   ├── anatomy/
│   ├── items/
│   ├── inventory/
│   ├── capabilities/
│   ├── skills/
│   ├── actions/
│   │
│   ├── effects/
│   ├── events/
│   ├── map/
│   ├── npc/
│   ├── sponsors/
│   ├── wildlife/
│   │
│   ├── simulation/
│   ├── persistence/
│   └── logging/
│
├── instance/
│   ├── saves/
│   ├── cache/
│   ├── logs/
│   └── exports/
│
├── docs/
│   └── DATA_ARCHITECTURE.md
│
├── requirements.txt
├── run.py
├── README.md
└── .gitignore
```

This is the intended organisational structure. Existing modules may remain in their current locations until their responsibilities are migrated.

---

# 3. Universal Data Format

All structured game definitions and records use `.txt` files with a consistent tag-value format.

### Example

```text
object.type,"item"
object.id,"item.spear"
object.version,"1"

item.name,"Spear"
item.description,"A long pointed weapon."
```

### Formatting rules

1. One tag-value pair per line.
2. Tags use lowercase dotted notation.
3. Values are enclosed in double quotation marks.
4. Repeated tags are allowed only when the registry permits them.
5. Lines beginning with `#` are comments.
6. Empty values and missing values must have consistent, documented meanings.
7. References use stable object IDs.
8. Files must follow the same parsing and validation rules.

### Universal metadata

Every definition should contain:

```text
object.type,"..."
object.id,"..."
object.version,"1"
```

`object.type` identifies the definition type, `object.id` uniquely identifies it, and `object.version` allows future compatibility management.

---

# 4. Registries

Registries define which tags are valid and how the engine interprets them.

## 4.1 Tag Registry

Location: `config/tag_registry.txt`

The registry should define:

| Field | Purpose |
|---|---|
| tag | Exact tag name |
| type | Expected value type |
| object_type | Which objects may use it |
| multiplicity | Single or multiple values |
| required | Whether the tag is mandatory |
| reference_target | Expected referenced object type |
| default | Default value, if applicable |
| minimum | Numeric lower bound |
| maximum | Numeric upper bound |
| description | Explanation of the tag |

The registry must be the authoritative source for data validation.

## 4.2 Effect Registry

Location: `config/effect_registry.txt`

Defines available effect paths, their value types, application rules, stacking behaviour and applicable contexts.

For example:

```text
effect.path,"stat.strength"
effect.type,"multiplier"
effect.stack_rule,"multiply"
effect.context,"global"
```

---

# 5. Data Definitions vs Runtime Instances

This distinction is fundamental.

## 5.1 Definitions

Definitions describe what something is.

Examples:

- A spear.
- A wolf species.
- A bleeding status.
- A particular trait.
- A body-part template.
- A combat action.

Definitions are reusable and should not contain information belonging to one specific simulation instance.

## 5.2 Runtime Instances

Instances represent individual objects created during a simulation.

Examples:

- A specific spear carried by a tribute.
- A particular wolf in the arena.
- A specific tribute's injured arm.
- An individual relationship between two characters.

Instances may have unique IDs and mutable properties.

### Example: Item definition

```text
object.type,"item"
object.id,"item.spear"
object.version,"1"

item.name,"Spear"
item.classifications,"classification.weapon"
item.classifications,"classification.tool"
item.capabilities,"capability.melee_attack"
item.capabilities,"capability.piercing"
item.capabilities,"capability.fishing"
item.skills,"skill.piercing"
item.skills,"skill.fishing"

item.properties.weight,"2.5"
item.properties.durability_max,"100"
```

### Example: Runtime item instance

```text
object.type,"item_instance"
object.id,"instance.item.00001"
object.version,"1"

item_instance.definition,"item.spear"
item_instance.owner,"entity.tribute.001"
item_instance.durability_current,"78"
item_instance.quantity,"1"
```

The definition describes the spear. The instance describes this particular spear.

This allows multiple copies of the same item to have different durability, owners, modifications and conditions without duplicating the original definition.

---

# 6. Item Architecture

## 6.1 Items Are Not Mutually Exclusive Types

An item must not be restricted to being either a weapon, a tool or a resource.

A single object can serve multiple purposes.

Examples:

| Item | Classifications | Capabilities |
|---|---|---|
| Rock | Resource, Weapon | Melee attack, Throwing |
| Knuckledusters | Weapon | Unarmed combat |
| Dagger | Weapon, Tool | Piercing, Fundamental tool use |
| Spear | Weapon, Tool | Piercing, Fishing, Throwing |
| Sword | Weapon | Slashing |
| Machete | Weapon, Tool | Slashing, Cutting |
| Club | Resource, Weapon, Craftable | Bashing |
| Metal Pipe | Resource, Weapon, Craftable | Bashing |
| Mace | Weapon | Bashing |
| Axe | Weapon, Tool | Slashing, Woodcutting |
| Sling | Weapon | Throwing |
| Boomerang | Weapon | Throwing |
| Bow | Weapon | Archery |
| Crossbow | Weapon | Archery |
| Slingshot | Weapon | Archery |
| Blowgun | Weapon | Miscellaneous marksmanship |
| Pipegun | Weapon | Gunmanship |
| Shotgun | Weapon | Gunmanship |
| Rifle | Weapon | Gunmanship |
| Pistol | Weapon | Gunmanship |
| Rocket Launcher | Weapon | Gunmanship |

These are illustrative assignments. Actual definitions should be configurable.

## 6.2 Four Separate Concepts

Every item system must distinguish four concepts.

### A. Item Definition

Describes the actual object.

Example: `item.spear`

### B. Classification

Describes what kind of item it is.

Examples:

- Weapon
- Tool
- Resource
- Consumable
- Equipment

An item may have multiple classifications.

### C. Capability

Describes what the item can be used to do.

Examples:

- Melee attack
- Piercing
- Fishing
- Woodcutting
- Cutting
- Throwing

An item may have multiple capabilities.

### D. Skill Association

Describes which skills are relevant when using the item.

Examples:

- Melee
- Piercing
- Fishing
- Woodcutting
- Marksmanship

A capability and a skill are not interchangeable.

For example, a spear has the capability to fish, but the character's Fishing skill determines how proficiently they perform the fishing action.

## 6.3 Classification Definitions

Location: `data/classifications/`

Classifications should themselves be reusable definitions.

Example:

```text
object.type,"classification"
object.id,"classification.weapon"
object.version,"1"

classification.name,"Weapon"
classification.description,"An item intended for combat."
```

Other examples:

- `classification.tool`
- `classification.resource`
- `classification.craftable`
- `classification.consumable`
- `classification.equipment`

A classification should not automatically grant an action or skill.

For example, being classified as a weapon does not automatically mean an item can perform every kind of attack.

## 6.4 Capability Definitions

Location: `data/capabilities/`

Capabilities describe supported functionality.

Example:

```text
object.type,"capability"
object.id,"capability.fishing"
object.version,"1"

capability.name,"Fishing"
capability.category,"tools"
capability.description,"Allows an object to be used for fishing."
```

Other examples:

```text
capability.melee_attack
capability.piercing
capability.slashing
capability.bashing
capability.throwing
capability.archery
capability.gunmanship
capability.woodcutting
capability.cutting
capability.fishing
capability.crafting
```

Capabilities are reusable references. Items reference them instead of redefining them.

## 6.5 Item Properties

Item properties should be separated according to functionality.

A spear might have:

```text
item.properties.weight,"2.5"
item.properties.durability_max,"100"

weapon.damage,"12"
weapon.damage_type,"piercing"
weapon.range,"2"
weapon.attack_speed,"1.0"

tool.fishing.efficiency,"1.2"
```

An item should only define properties relevant to its capabilities.

The engine must not assume that every item has weapon damage, fishing efficiency or other unrelated properties.

---

# 7. Skills Architecture

Location: `data/skills/`

Skills are hierarchical definitions.

A skill may have:

- A parent skill.
- Child skills.
- A general bonus.
- Associated actions.
- Associated capabilities.
- Configurable progression rules.

## 7.1 Proposed Skill Hierarchy

```text
Combat
├── Melee
│   ├── Unarmed
│   ├── Piercing
│   ├── Slashing
│   └── Bashing
│
└── Marksmanship
    ├── Throwing
    ├── Archery
    ├── Miscellaneous
    └── Gunmanship

Survival
├── Fishing
├── Woodcutting
└── Other survival skills

General
└── Fundamental
```

This is a starting hierarchy, not a fixed restriction.

Skills may be added, removed or reorganised through data definitions.

## 7.2 General Bonuses

Some skills provide general bonuses to their child skills.

For example:

- Melee provides a general combat bonus.
- Marksmanship provides a general ranged combat bonus.
- Throwing may provide a general bonus to throwing-related actions.

The engine must support configurable inheritance.

Do not assume that every parent skill automatically contributes a fixed amount to every child skill.

## 7.3 Skill Definition Example

```text
object.type,"skill"
object.id,"skill.piercing"
object.version,"1"

skill.name,"Piercing"
skill.parent,"skill.melee"
skill.category,"combat"
skill.description,"Proficiency with piercing attacks."
```

A character's skill progression belongs to their runtime character data, not the reusable skill definition.

---

# 8. Action Architecture

Location: `data/abilities/actions/`

An item capability does not automatically perform an action.

Instead, actions define what the character can attempt, the requirements, and how the result is resolved.

This distinction allows the same item to support several different actions.

## 8.1 Action Requirements

An action may require:

- A particular capability.
- A particular skill.
- A particular item classification.
- A specific target.
- A minimum attribute or skill level.
- A required condition.
- A particular environment.
- Stamina or other resources.

Not every action needs every requirement.

## 8.2 Example: Fishing With a Spear

```text
object.type,"action"
object.id,"action.fish_with_spear"
object.version,"1"

action.name,"Fish with Spear"
action.required_capabilities,"capability.fishing"
action.required_skills,"skill.fishing"
action.required_classifications,"classification.tool"
action.target_type,"water"
action.stamina_cost,"5"
```

## 8.3 Example: Spear Attack

```text
object.type,"action"
object.id,"action.attack_with_spear"
object.version,"1"

action.name,"Spear Attack"
action.required_capabilities,"capability.melee_attack"
action.required_capabilities,"capability.piercing"
action.required_skills,"skill.piercing"
action.required_classifications,"classification.weapon"
action.target_type,"entity"
action.stamina_cost,"4"
```

## 8.4 Action Resolution

The action engine should:

1. Receive the requested action.
2. Identify the acting character.
3. Check whether the character has access to the required item.
4. Check whether the item has the required capabilities and classifications.
5. Check the character's relevant skills and attributes.
6. Check environmental and target requirements.
7. Calculate costs and success chances.
8. Resolve the action.
9. Apply damage, effects, resource changes or other outcomes.
10. Update the simulation state and record the result.

The action definition describes the requirements and rules. Python handles the actual execution.

---

# 9. Character and Entity Architecture

Entities include:

- Tributes
- NPCs
- Mentors
- Sponsors
- Wildlife

All entities should share a common identity system.

Their individual files should store different aspects of their state.

Suggested organisation for a character instance:

```text
entity.tribute.001/
├── identity.txt
├── attributes.txt
├── stats.txt
├── personality.txt
├── anatomy.txt
├── relationships.txt
├── inventory.txt
├── equipment.txt
├── traits.txt
├── skills.txt
├── statuses.txt
├── abilities.txt
├── history.txt
└── memory.txt
```

The exact storage mechanism can be implemented using separate files or another persistence arrangement, but the logical separation should remain.

## 9.1 Identity

Stores stable identifying information:

- Name
- Nickname
- Pronouns
- Gender
- Age
- District
- Role
- Species
- Portrait

Derived values should not be stored as independent authoritative values when they can be calculated reliably.

## 9.2 Attributes and Stats

Attributes represent fundamental characteristics.

Stats represent measurable gameplay values, such as:

- Health
- Stamina
- Strength
- Agility
- Perception

The exact distinction between attributes and stats should be maintained consistently throughout the engine.

## 9.3 Personality

Personality should use reusable facet definitions and character-specific values.

## 9.4 Traits

Traits are reusable definitions referenced by entities.

They can provide:

- Stat modifiers
- Capabilities
- Skill bonuses
- Restrictions
- Special effects

Traits can be assigned during character generation or acquired during the simulation.

## 9.5 Relationships

Relationships must support individual connections between entities.

The system should support directional relationships, since two characters do not necessarily feel the same way about each other.

## 9.6 Memory and History

Memory records relevant past experiences.

History records important events in an entity's life or simulation.

These should remain separate from static identity data.

---

# 10. Anatomy and Species

Location:

- `data/anatomy/body_parts/`
- `data/anatomy/templates/`
- `data/species/`

Anatomy should be definition-driven.

## 10.1 Body-Part Definitions

Each body-part definition describes:

- Name
- Category
- Function
- Health
- Vulnerability
- Associated attributes or effects
- Consequences of damage or loss

## 10.2 Anatomy Templates

Species reference anatomy templates.

For example, a human anatomy template defines the expected body parts for a human entity.

## 10.3 Individual Body-Part Instances

Every individual body part must have its own runtime state.

For example, an entity with three hearts must have three independently tracked heart instances.

Each can have:

- Its own health.
- Its own injuries.
- Its own condition.
- Its own functionality.

Damage to one heart should not automatically be treated as damage to all three.

## 10.4 Species Definitions

Species definitions reference anatomy templates and provide species-specific properties.

This allows the same anatomy engine to support humans, animals and other creatures.

---

# 11. Effects System

Effects should be reusable and independent of the system that produces them.

Effects may originate from:

- Traits
- Statuses
- Injuries
- Equipment
- Items
- Consumables
- Terrain
- Weather
- Events
- Sponsor gifts
- Environmental conditions

The effects engine should resolve all relevant modifiers consistently.

## 11.1 Modifier Types

At minimum:

- Flat addition
- Multiplier
- Override
- Restriction
- Conditional effect

## 11.2 Stacking Rules

Multipliers must multiply rather than add together.

For example:

```text
Base value = 100
Multiplier A = 0.9
Multiplier B = 0.9

Final value = 100 × 0.9 × 0.9
Final value = 81
```

For ordinary additive and multiplicative modifiers, the proposed calculation order is:

\[
Effective = (Base + \sum Additions)\times\prod Multipliers
\]

Overrides and restrictions should have their own explicitly defined resolution rules.

The effect registry must define how each effect behaves.

---

# 12. Maps and Environments

Location: `data/maps/`

Map definitions should be separated into:

1. Map templates.
2. Environment definitions.
3. Map configurations.
4. Generated maps.

The environment and map dimensions should be independent.

For example:

- Forest, 15 × 15.
- Desert, 15 × 15.
- Frost, 15 × 15.
- Forest, 25 × 25.

A map template describes layout rules and possible zones.

An environment describes terrain, climate, hazards, resources and other environmental characteristics.

A generated map is a specific runtime arena.

---

# 13. Events and Simulation

Location: `data/events/`

Events should be data-driven wherever practical.

Suggested categories:

- Arena events
- Encounters
- Sponsor events
- Weather events

The simulation engine controls:

- Day and night cycles.
- Turn progression.
- Character decisions.
- Arena events.
- Sponsor interventions.
- Environmental changes.
- Death and elimination.
- Victory conditions.

Event definitions describe what can happen. The engine determines when and how an event occurs.

---

# 14. Engine Architecture

The Python engine should be separated into independent systems.

| Module | Responsibility |
|---|---|
| `data/` | Loading, parsing, validating and saving data |
| `entities/` | Entity management |
| `characters/` | Character calculations and behaviour |
| `anatomy/` | Body-part and injury management |
| `items/` | Item definitions and instances |
| `inventory/` | Ownership, quantity and equipment |
| `capabilities/` | Capability checks |
| `skills/` | Skill progression and proficiency |
| `actions/` | Action requirements and execution |
| `effects/` | Modifier resolution |
| `events/` | Event management and resolution |
| `map/` | Map generation, zoning and coordinates |
| `npc/` | NPC behaviour and interactions |
| `sponsors/` | Sponsor behaviour and interventions |
| `wildlife/` | Wildlife behaviour |
| `simulation/` | Main simulation loop |
| `persistence/` | Saving and loading simulation state |
| `logging/` | Simulation logs |

Each system should have a clear responsibility.

Systems should communicate through defined interfaces rather than accessing one another's internal implementation.

---

# 15. Data Manager

The Data Manager is the central access point for static game definitions.

It should:

1. Locate data files.
2. Parse their contents.
3. Validate definitions.
4. Index definitions by ID.
5. Resolve references.
6. Cache frequently used definitions.
7. Provide definitions to engine systems.
8. Support safe updates where permitted.

Individual gameplay systems should not independently read and parse data files.

## 15.1 Parser

`engine/data/parser.py`

Responsible only for converting the tag-value file format into structured Python data.

It should not contain gameplay logic.

## 15.2 Registry

`engine/data/registry.py`

Loads and manages tag and effect registries.

## 15.3 Reference Resolver

`engine/data/references.py`

Resolves references between definitions and detects missing or invalid references.

## 15.4 Validation

`engine/data/validation.py`

Checks file structure, required tags, value types, allowed references and constraints.

## 15.5 Saving

`engine/data/saving.py`

Handles safe file writing, including temporary files and atomic replacement where possible.

## 15.6 Manager

`engine/data/manager.py`

Provides the central interface used by the rest of the engine.

---

# 16. Flask Interface

Flask is the presentation layer.

It should handle:

- Pages and navigation.
- User input.
- Character selection.
- Simulation controls.
- Displaying maps.
- Displaying character information.
- Displaying event logs.
- Save selection and management.

Flask should not independently implement combat, skills, item usage or simulation calculations.

Instead, it calls the engine and displays the results.

This keeps the engine usable independently of the web interface.

---

# 17. Data and Runtime Separation

Static definitions belong in `data/`.

Mutable simulation state belongs in `instance/`.

For example:

| Information | Location |
|---|---|
| Spear definition | `data/items/` |
| Fishing capability | `data/capabilities/` |
| Piercing skill definition | `data/skills/` |
| Fishing action definition | `data/abilities/actions/` |
| Tribute's spear instance | `instance/saves/` |
| Tribute's current skill level | `instance/saves/` |
| Tribute's current injuries | `instance/saves/` |
| Current arena state | `instance/saves/` |

A simulation must not accidentally modify the original static definitions when changing an instance.

---

# 18. Implementation Order

Implementation should follow dependency order rather than attempting to build every system simultaneously.

## Phase 1 — Data Foundation

1. Finalise tag-value syntax.
2. Implement parser.
3. Implement tag registry.
4. Implement validation.
5. Implement reference resolution.
6. Implement Data Manager.
7. Implement safe saving.

## Phase 2 — Definitions

1. Entity definitions.
2. Attributes and stats.
3. Species.
4. Anatomy.
5. Classifications.
6. Capabilities.
7. Skills.
8. Items.
9. Actions.
10. Traits and effects.
11. Statuses and injuries.

## Phase 3 — Runtime Instances

1. Entity instances.
2. Item instances.
3. Inventory.
4. Equipment.
5. Character skills.
6. Anatomy state.
7. Relationships.
8. Memory and history.

## Phase 4 — Gameplay Systems

1. Attribute calculations.
2. Effect resolution.
3. Capability checks.
4. Skill calculations.
5. Action requirements.
6. Action execution.
7. Combat.
8. Tool usage.
9. Resource gathering.
10. Crafting.

## Phase 5 — Simulation

1. Turn progression.
2. Character behaviour.
3. NPC behaviour.
4. Map generation.
5. Events.
6. Sponsors.
7. Wildlife.
8. Arena progression.
9. Victory conditions.

## Phase 6 — Interface

1. Flask routes.
2. Character management.
3. Map display.
4. Simulation controls.
5. Event logs.
6. Save management.

---

# 19. Non-Negotiable Architectural Rules

1. **Do not hardcode game definitions in Python.** Reusable game content belongs in data files.
2. **Do not make classifications mutually exclusive.** An item can be a weapon and a tool simultaneously.
3. **Do not confuse classifications with capabilities.** Being a weapon does not automatically grant every combat capability.
4. **Do not confuse capabilities with skills.** An item provides functionality; a character's proficiency determines how well they use it.
5. **Do not assume an item capability automatically executes an action.** Actions must have their own definitions and requirements.
6. **Do not duplicate definitions for individual instances.** Instances reference reusable definitions.
7. **Do not let gameplay systems parse files independently.** Use the Data Manager.
8. **Do not store derived values as authoritative data unnecessarily.**
9. **Do not assume all entities have identical anatomy or capabilities.**
10. **Do not treat relationships as necessarily reciprocal.**
11. **Do not let Flask contain core simulation logic.**
12. **Do not make the hierarchy rigid.** New skills, capabilities, actions and classifications should be addable through data definitions.
13. **Do not move or rename existing modules without checking their imports and dependencies.**
14. **Keep runtime state separate from static definitions.**

---

# 20. Final Architectural Goal

The intended system should allow new gameplay content to be introduced primarily through data files.

For example, adding a new item should not require writing a new Python class simply because the item has a different name or combination of properties.

A new item should be able to:

- Reference multiple classifications.
- Reference multiple capabilities.
- Reference multiple skills.
- Define only the properties relevant to its functionality.
- Be used by any compatible action.
- Have multiple individual instances with different runtime states.

Likewise, adding a new skill or action should primarily involve creating a definition and configuring its requirements.

Python should provide the systems that interpret and execute those definitions.

**The overall design principle is:**

> Data defines what exists. Registries define what is valid. The engine defines how things behave. The simulation maintains what happens. The interface lets the user interact with it.