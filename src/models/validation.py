from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Validation:
    """Result of a validation operation."""
    valid: bool
    errors: List[str] = field(default_factory=list)
