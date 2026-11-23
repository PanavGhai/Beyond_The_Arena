# Options registries: current status

`genders.txt` and `pronouns.txt` are populated tag-based option registries and are read by the character creator. Their option entries use `gender.<key>.value` / `pronouns.<key>.value` and an optional `enabled` value. The creator shows enabled options only.

`data/registries/options/other.txt` is currently empty. Its schema and consumer behavior remain undocumented until it has populated examples.

The empty `districts.txt` was removed because Sectors are generated per save rather than selected from a global option list. Entity roles use `data/registries/entities/roles.txt`, not the options registry folder.

