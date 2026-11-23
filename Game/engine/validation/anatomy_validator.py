"""Validate registered anatomy and species definitions."""
from engine.anatomy.definitions import AnatomyLoader, AnatomyValidationError

class AnatomyValidator:
    def __init__(self, registry_manager):
        self.registries = registry_manager

    def validate(self):
        try:
            AnatomyLoader(self.registries).validate_all()
        except (AnatomyValidationError, TypeError, ValueError) as error:
            return {"valid": False, "errors": [str(error)]}
        return {"valid": True, "errors": []}
