"""
TRINKER - Build Order Data Models
Dataclasses representing a build order and its individual steps.
These are the canonical in-memory representations used throughout the app.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BuildStep:
    """
    One instruction in a build order sequence.

    Attributes:
        index:       1-based step number (for display).
        time_str:    Target game time string, e.g. '2:30' or '~3:00'.
        time_sec:    Target game time in seconds (derived from time_str).
        population:  Villager / total pop count at this step.
        food:        Target food count (None = not specified).
        wood:        Target wood count (None = not specified).
        gold:        Target gold count (None = not specified).
        stone:       Target stone count (None = not specified).
        description: Main instruction text, e.g. "Build lumber camp".
        notes:       Optional supplemental hint or context.
        age:         Dark/Feudal/Castle/Imperial (None = no age change).
    """
    index:       int
    description: str
    time_str:    str        = ""
    time_sec:    int        = 0
    population:  int        = 0
    food:        Optional[int] = None
    wood:        Optional[int] = None
    gold:        Optional[int] = None
    stone:       Optional[int] = None
    notes:       str        = ""
    age:         Optional[str] = None   # "Dark" | "Feudal" | "Castle" | "Imperial"

    def to_dict(self) -> dict:
        return {
            "index":       self.index,
            "description": self.description,
            "time_str":    self.time_str,
            "time_sec":    self.time_sec,
            "population":  self.population,
            "food":        self.food,
            "wood":        self.wood,
            "gold":        self.gold,
            "stone":       self.stone,
            "notes":       self.notes,
            "age":         self.age,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BuildStep":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class BuildOrder:
    """
    A complete build order with metadata and step list.

    Attributes:
        id:          Database primary key (None for unsaved records).
        external_id: Identifier from external source (e.g. buildorderguide.com slug).
        name:        Human-readable build order name.
        civ:         Civilization name, e.g. 'Spanish', 'Any'.
        strategy:    Short strategy label, e.g. 'Fast Castle', 'Scout Rush'.
        difficulty:  'Easy' | 'Medium' | 'Hard'.
        tags:        List of searchable tags, e.g. ['rush', 'knights', 'meta'].
        author:      Creator name / credit.
        source_url:  URL this was imported from.
        steps:       Ordered list of BuildStep objects.
        notes:       Free-form notes / overview text.
        is_favorite: Whether user has starred this build.
        created_at:  ISO-8601 creation timestamp.
        updated_at:  ISO-8601 last-modified timestamp.
    """
    name:        str
    civ:         str              = "Any"
    strategy:    str              = ""
    difficulty:  str              = "Medium"
    tags:        list[str]        = field(default_factory=list)
    author:      str              = ""
    source_url:  str              = ""
    steps:       list[BuildStep]  = field(default_factory=list)
    notes:       str              = ""
    is_favorite: bool             = False
    id:          Optional[int]    = None
    external_id: Optional[str]    = None
    created_at:  str              = ""
    updated_at:  str              = ""

    @property
    def step_count(self) -> int:
        return len(self.steps)

    @property
    def estimated_feudal_sec(self) -> Optional[int]:
        """Return the estimated time to Feudal age from steps, if present."""
        for step in self.steps:
            if step.age and "feudal" in step.age.lower():
                return step.time_sec
        return None

    def to_dict(self) -> dict:
        return {
            "id":          self.id,
            "external_id": self.external_id,
            "name":        self.name,
            "civ":         self.civ,
            "strategy":    self.strategy,
            "difficulty":  self.difficulty,
            "tags":        self.tags,
            "author":      self.author,
            "source_url":  self.source_url,
            "steps":       [s.to_dict() for s in self.steps],
            "notes":       self.notes,
            "is_favorite": self.is_favorite,
            "created_at":  self.created_at,
            "updated_at":  self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BuildOrder":
        steps = [BuildStep.from_dict(s) for s in d.pop("steps", [])]
        bo = cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
        bo.steps = steps
        return bo
