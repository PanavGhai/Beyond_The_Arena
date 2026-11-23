# Entities and tribute sheets

The project has six populated entity files, all tribute sheets. There are no populated NPC, mentor, sponsor, or wildlife examples from which to document their category-specific formats. Entity parsing is implemented by `engine/parsing/entity_parser.py`; it creates a shared `Entity` record and preserves unrecognized tags in `extra_tags`.

## File and metadata

Current tribute sheets belong under `data/compendium/entities/tributes/` and use `object.type,"entity"`. Their `object.id` is the stable identity and `object.version` is text. `entity.role` selects the registered Compendium category and matching folder; `entity.name` is required by `EntityValidator`.

```text
object.type,"entity"
object.id,"entity.tribute.001"
object.version,"1"
settings.hardcore,"false"

entity.role,"tributes"
entity.name,"Katniss Everdeen"
entity.nickname,"Catnip"
entity.pronouns,"She/Her"
entity.gender,"Female"
entity.age,"16"
entity.species,"species.human"
entity.height_cm,"165"
entity.weight_kg,"54"
entity.portrait_url,"https://i.pinimg.com/originals/37/fd/d0/37fdd07cbd6a006abdef535aa1124c21.jpg"
entity.death_portrait_url,"bw"
entity.description,"Skilled hunter and archer from District 12. Resourceful, independent and determined, she is an expert at survival, tracking, trapping and using a bow."

entity.attributes.strength,"14"
entity.attributes.agility,"18"
entity.skills.tracking,"20"
entity.personality.facets.bravery,"80"
entity.personality.values.family,"100"
```

Replace example statistic names with keys present in their corresponding registries. Values in grouped statistic tags must be whole-number text and within definition min/max when those limits are present (facets and values currently default to 0–100 if no limit is defined).

## Known entity fields

| Tag | Entity parser behavior | Validation/runtime status |
|---|---|---|
| `object.type`, `object.id`, `object.version` | Stored as identity/version fields | Validator requires all three and nonempty values; `object.type` must equal `entity`. |
| `settings.hardcore` | Optional string tag | Current tribute files and new characters default to `false`; only Tribute creation may set it to `true`. It remains in `extra_tags`; no gameplay effect is implemented yet. |
| `settings.persistent` | Legacy optional boolean | The parser still recognizes this older setting as a boolean. Current tribute sheets use `settings.hardcore` instead. |
| `entity.role`, `entity.name` | Strings | Both required and nonempty; role must be in the roles registry. |
| `entity.nickname`, `entity.pronouns`, `entity.gender` | Strings, default empty | No additional category or enum validation found. |
| `entity.age` | Optional integer | Character creation enforces the configured age bounds. |
| `entity.height_cm`, `entity.weight_kg` | Optional floating-point numbers | Character creation enforces configured bounds. |
| `entity.pronouns`, `entity.gender`, `entity.species` | Strings | New character creation validates them against option/species registries. |
| `entity.portrait_url`, `entity.death_portrait_url`, `entity.description` | Strings | Not validated by entity validator. |
| `entity.attributes.<key>` | Integer-valued group | Must be registered; whole number; definition limits applied. |
| `entity.skills.<key>` | Integer-valued group | Must be registered; whole number; definition limits applied. |
| `entity.personality.facets.<key>` | Integer-valued group | Must be registered; whole number; definition limits or temporary 0–100 fallback. |
| `entity.personality.values.<key>` | Integer-valued group | Must be registered; whole number; definition limits or temporary 0–100 fallback. |

`entity_parser` does not parse traits, relationships, inventory/equipment, or category-specific structures into dedicated fields. Unknown tags are retained in `extra_tags`, but this is not evidence those features are consumed by simulation.

## Category support

The dispatcher registers only `entity`. It does not dispatch separate tribute/NPC/mentor/sponsor/wildlife parsers. The entity validator checks the shared entity contract and the four numeric groups; it does not enforce valid category names or category-specific required fields. NPCs, mentors, sponsors, wildlife, traits, and relationships need implementation/data evidence before stronger schemas can be stated.
