
# engine/registries/registry_manager.py

from pathlib import Path

from engine.parsing.tag_parser import parse_file


# ==========================================
# 1. REGISTRY MANAGER
# ==========================================

class RegistryManager:
    """
    Loads registries and resolves their references
    to definition files.
    """

    def __init__(self, project_root=None):

        self.project_root = (
            Path(project_root)
            if project_root
            else Path(__file__).resolve().parents[2]
        )

        self.registry_root = (
            self.project_root / "data" / "registries"
        )

        self.definition_root = (
            self.project_root / "data" / "definitions"
        )

        # Registered names mapped to definition IDs.
        self.registries = {
            "attributes": {},
            "skills": {},
            "facets": {},
            "values": {},
            "arenas": {},
            "regions": {},
            "locations": {},
            "tiles": {},
            "body_parts": {},
            "species": {},
            "roles": {},
        }

        # Definition IDs mapped to their file paths.
        self.definition_index = {}

        # Parsed definitions, cached after first access.
        self.definition_cache = {}

        self.load()


    # ======================================
    # 2. INITIAL LOADING
    # ======================================

    def load(self):
        """
        Load all supported registries and index
        all available definition files.
        """

        self.registries = {
            "attributes": {},
            "skills": {},
            "facets": {},
            "values": {},
            "arenas": {},
            "regions": {},
            "locations": {},
            "tiles": {},
            "body_parts": {},
            "species": {},
            "roles": {},
        }

        self.definition_index.clear()
        self.definition_cache.clear()

        self._index_definitions()

        self._load_registry_family(
            "attributes",
            self.registry_root / "attributes"
        )

        self._load_registry_family(
            "skills",
            self.registry_root / "skills"
        )

        self._load_registry_family(
            "facets",
            self.registry_root / "personality",
            filename_filter="facets"
        )

        self._load_registry_family(
            "values",
            self.registry_root / "personality",
            filename_filter="values"
        )

        self._load_registry_family(
            "arenas",
            self.registry_root / "maps",
            filename_filter="arenas"
        )

        self._load_registry_family(
            "regions",
            self.registry_root / "maps",
            filename_filter="regions"
        )

        self._load_registry_family(
            "locations",
            self.registry_root / "maps",
            filename_filter="locations"
        )

        self._load_registry_family(
            "tiles",
            self.registry_root / "maps",
            filename_filter="tiles"
        )

        # Add anatomy registry families without changing existing loaders.
        self._load_registry_family(
            "body_parts",
            self.registry_root / "anatomy",
            filename_filter="body_parts"
        )

        self._load_registry_family(
            "species",
            self.registry_root / "species",
            filename_filter="species"
        )

        self._load_registry_family(
            "roles",
            self.registry_root / "entities",
            filename_filter="roles"
        )


    # ======================================
    # 3. DEFINITION INDEX
    # ======================================

    def _index_definitions(self):
        """
        Index definitions by their object.id.

        This means registry references do not
        need to contain physical file paths.
        """

        if not self.definition_root.exists():
            return

        for file_path in self.definition_root.rglob("*.txt"):

            try:
                document = parse_file(file_path)

            except Exception:
                # Invalid definition files are not indexed.
                continue

            definition_id = document.get("object.id")

            if not definition_id:
                continue

            if definition_id in self.definition_index:
                raise ValueError(
                    f"Duplicate definition ID: {definition_id}\n"
                    f"Files:\n"
                    f"{self.definition_index[definition_id]}\n"
                    f"{file_path}"
                )

            self.definition_index[definition_id] = file_path


    # ======================================
    # 4. REGISTRY LOADING
    # ======================================

    def _load_registry_family(
        self,
        family,
        registry_path,
        filename_filter=None
    ):
        """
        Load all registry files belonging to
        a particular registry family.

        Entries use their final tag segment as
        their lookup name.

        Example:
            attribute.strength
            -> strength
        """

        if not registry_path.exists():
            return

        if registry_path.is_file():
            files = [registry_path]

        else:
            files = sorted(
                registry_path.rglob("*.txt")
            )

        for file_path in files:

            if filename_filter:
                if file_path.stem != filename_filter:
                    continue

            document = parse_file(file_path)

            if document.get("object.type") != "registry":
                raise ValueError(
                    f"Invalid registry file: {file_path}\n"
                    f"Expected object.type = registry."
                )

            for entry in document.entries:

                if entry.tag.startswith("object."):
                    continue

                if entry.tag.startswith("settings."):
                    continue

                name = entry.tag.rsplit(".", 1)[-1]

                definition_id = entry.value

                if name in self.registries[family]:
                    previous = self.registries[family][name]

                    if previous != definition_id:
                        raise ValueError(
                            f"Duplicate registry entry '{name}' "
                            f"in family '{family}'."
                        )

                self.registries[family][name] = definition_id


    # ======================================
    # 5. REGISTRY LOOKUPS
    # ======================================

    def contains(self, family, name):
        """
        Check whether an entry is registered.
        """

        return name in self.registries.get(family, {})


    def get_definition_id(self, family, name):
        """
        Retrieve the definition ID for a
        registered entry.
        """

        return self.registries.get(family, {}).get(name)


    def get_registered_entries(self, family):
        """
        Return all entries in a registry family.
        """

        return dict(
            self.registries.get(family, {})
        )


    # ======================================
    # 6. DEFINITION RESOLUTION
    # ======================================

    def resolve_definition(self, definition_id):
        """
        Retrieve a parsed definition using
        its universal object.id.
        """

        if definition_id in self.definition_cache:
            return self.definition_cache[definition_id]

        file_path = self.definition_index.get(definition_id)

        if file_path is None:
            return None

        document = parse_file(file_path)

        self.definition_cache[definition_id] = document

        return document


    def get_definition(self, family, name):
        """
        Resolve a registry entry directly
        into its parsed definition.
        """

        definition_id = self.get_definition_id(
            family,
            name
        )

        if definition_id is None:
            return None

        return self.resolve_definition(definition_id)


    # ======================================
    # 7. NUMERICAL LIMITS
    # ======================================

    def get_numeric_limits(self, family, name):
        """
        Retrieve minimum and maximum values
        from a definition.

        Supports any definition tag ending
        in .minimum or .maximum.
        """

        definition = self.get_definition(
            family,
            name
        )

        if definition is None:
            return None, None

        minimum = None
        maximum = None

        for entry in definition.entries:

            if entry.tag.endswith(".minimum"):
                minimum = entry.value

            elif entry.tag.endswith(".maximum"):
                maximum = entry.value

        return minimum, maximum
