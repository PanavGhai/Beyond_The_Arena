"""Small anatomy-derived calculations; injury severity stays with damage logic."""

from engine.anatomy.definitions import AnatomyLoader


def pain_sanity_loss(base_pain_sanity_loss, part_type, mental_resistance, loader: AnatomyLoader):
    """Apply configured part sensitivity and caller-provided wisdom resistance."""
    if base_pain_sanity_loss < 0:
        raise ValueError("Base pain sanity loss cannot be negative")
    if not 0 <= mental_resistance <= 1:
        raise ValueError("Mental resistance must be between 0 and 1")
    sensitivity = loader.load_part(part_type).pain_sensitivity
    return base_pain_sanity_loss * sensitivity * (1 - mental_resistance)
