
# engine/parsing/tag_parser.py

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# ==========================================
# 1. PARSER ERRORS
# ==========================================

class TagParserError(Exception):
    """Base exception for tag parser errors."""


class TagSyntaxError(TagParserError):
    """Raised when a tag-value line has invalid syntax."""

    def __init__(self, file_path: Path, line_number: int, message: str):
        self.file_path = file_path
        self.line_number = line_number
        self.message = message

        super().__init__(
            f"{file_path}:{line_number}: {message}"
        )


# ==========================================
# 2. TAG ENTRY
# ==========================================

@dataclass(frozen=True)
class TagEntry:
    """
    Represents one tag-value pair from a file.
    """

    tag: str
    value: str
    line_number: int


# ==========================================
# 3. PARSED DOCUMENT
# ==========================================

class TagDocument:
    """
    Stores the parsed contents of a tag-value file.

    Entries are kept in their original order.
    Repeated tags are preserved.
    """

    def __init__(self, file_path: Path, entries: list[TagEntry]):
        self.file_path = file_path
        self.entries = entries

    # --------------------------------------
    # Retrieve a single value
    # --------------------------------------

    def get(self, tag: str, default: Optional[str] = None) -> Optional[str]:
        """
        Return the last occurrence of a tag.

        Returns the default if the tag does not exist.
        """

        for entry in reversed(self.entries):
            if entry.tag == tag:
                return entry.value

        return default

    # --------------------------------------
    # Retrieve all occurrences
    # --------------------------------------

    def get_all(self, tag: str) -> list[str]:
        """
        Return every value associated with a tag.
        """

        return [
            entry.value
            for entry in self.entries
            if entry.tag == tag
        ]

    # --------------------------------------
    # Check tag existence
    # --------------------------------------

    def has(self, tag: str) -> bool:
        """
        Check whether a tag exists.
        """

        return any(
            entry.tag == tag
            for entry in self.entries
        )

    # --------------------------------------
    # Retrieve a group of tags
    # --------------------------------------

    def get_group(self, prefix: str) -> dict[str, str]:
        """
        Return tags beginning with a specified prefix.

        Example:
            get_group("entity.attributes.")

        Returns:
            {
                "strength": "14",
                "agility": "18"
            }
        """

        result = {}

        for entry in self.entries:
            if entry.tag.startswith(prefix):
                key = entry.tag[len(prefix):]
                result[key] = entry.value

        return result

    # --------------------------------------
    # Retrieve a group with repeated tags
    # --------------------------------------

    def get_group_all(self, prefix: str) -> dict[str, list[str]]:
        """
        Return all values for tags beginning with a prefix.
        """

        result = {}

        for entry in self.entries:
            if entry.tag.startswith(prefix):
                key = entry.tag[len(prefix):]

                result.setdefault(key, []).append(entry.value)

        return result

    # --------------------------------------
    # Convert document into a dictionary
    # --------------------------------------

    def to_dict(self) -> dict[str, str]:
        """
        Convert the document into a dictionary.

        When duplicate tags exist, the last value is retained.
        """

        result = {}

        for entry in self.entries:
            result[entry.tag] = entry.value

        return result


# ==========================================
# 4. UNIVERSAL FILE PARSER
# ==========================================

def parse_file(file_path: str | Path) -> TagDocument:
    """
    Read and parse a tag-value .txt file.

    Expected format:
        tag.name,"value"

    Returns:
        TagDocument
    """

    file_path = Path(file_path)

    if not file_path.is_file():
        raise FileNotFoundError(
            f"Tag file not found: {file_path}"
        )

    entries = []

    with file_path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        for line_number, raw_line in enumerate(file, start=1):

            stripped_line = raw_line.strip()

            # Ignore blank lines.
            if not stripped_line:
                continue

            # Ignore comments.
            if stripped_line.startswith("#"):
                continue

            try:
                row = next(
                    csv.reader(
                        [raw_line],
                        strict=True,
                        skipinitialspace=True
                    )
                )

            except csv.Error as error:
                raise TagSyntaxError(
                    file_path,
                    line_number,
                    f"Invalid CSV syntax: {error}"
                ) from error

            # Every entry must contain exactly two fields.
            if len(row) != 2:
                raise TagSyntaxError(
                    file_path,
                    line_number,
                    "Expected exactly two fields: tag,value"
                )

            tag = row[0].strip()
            value = row[1]

            if not tag:
                raise TagSyntaxError(
                    file_path,
                    line_number,
                    "Tag name cannot be empty."
                )

            entries.append(
                TagEntry(
                    tag=tag,
                    value=value,
                    line_number=line_number
                )
            )

    return TagDocument(
        file_path=file_path,
        entries=entries
    )
