
# engine/parsing/object_dispatcher.py

from pathlib import Path
from typing import Any, Callable

from engine.parsing.tag_parser import (
    TagDocument,
    parse_file
)

from engine.parsing.entity_parser import parse_entity


# ==========================================
# 1. DISPATCHER ERRORS
# ==========================================

class ObjectDispatcherError(Exception):
    """Base exception for object dispatcher errors."""


class UnknownObjectTypeError(ObjectDispatcherError):
    """Raised when no parser is registered for an object type."""


class DuplicateParserError(ObjectDispatcherError):
    """Raised when a parser is already registered for an object type."""


# ==========================================
# 2. OBJECT DISPATCHER
# ==========================================

class ObjectDispatcher:
    """
    Routes TagDocuments to specialised parsers.

    Each parser is registered against an object.type.
    """

    def __init__(self):

        self.parsers: dict[str, Callable[[TagDocument], Any]] = {}

    # --------------------------------------
    # Register parser
    # --------------------------------------

    def register(
        self,
        object_type: str,
        parser: Callable[[TagDocument], Any],
        replace: bool = False
    ):

        object_type = object_type.strip().lower()

        if not object_type:
            raise ValueError("Object type cannot be empty.")

        if object_type in self.parsers and not replace:

            raise DuplicateParserError(
                f"A parser for '{object_type}' is already registered."
            )

        self.parsers[object_type] = parser

    # --------------------------------------
    # Check parser registration
    # --------------------------------------

    def is_registered(self, object_type: str) -> bool:

        return object_type.strip().lower() in self.parsers

    # --------------------------------------
    # List registered object types
    # --------------------------------------

    def registered_types(self) -> list[str]:

        return sorted(self.parsers.keys())

    # --------------------------------------
    # Parse an existing document
    # --------------------------------------

    def parse(self, document: TagDocument) -> Any:

        object_type = document.get("object.type")

        if not object_type:

            raise ObjectDispatcherError(
                "Document does not contain 'object.type'."
            )

        object_type = object_type.strip().lower()

        parser = self.parsers.get(object_type)

        if parser is None:

            raise UnknownObjectTypeError(
                f"No parser registered for object.type='{object_type}'. "
                f"Registered types: {self.registered_types()}"
            )

        return parser(document)

    # --------------------------------------
    # Parse a file directly
    # --------------------------------------

    def parse_file(self, file_path: str | Path) -> Any:

        document = parse_file(file_path)

        return self.parse(document)


# ==========================================
# 3. DEFAULT DISPATCHER
# ==========================================

dispatcher = ObjectDispatcher()

dispatcher.register(
    "entity",
    parse_entity
)


# ==========================================
# 4. CONVENIENCE FUNCTION
# ==========================================

def parse_object(file_path: str | Path) -> Any:
    """
    Parse a file and automatically select its object parser.
    """

    return dispatcher.parse_file(file_path)
