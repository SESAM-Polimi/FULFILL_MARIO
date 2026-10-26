from dataclasses import dataclass, field
import json
import math
from pathlib import Path
import re
from types import MappingProxyType

MEASURES = {
    "D": "Plant-based diets",
    "S": "Smaller/shared living spaces",
    "M": "Smaller cars (fuel economy and tailpipe emissions)",
    "P": "Shared washing machines",
    "F": "Less air travel",
    "B": "More cycling (less car travel)",
}
YEARS = (2011, 2020, 2025, 2030, 2035, 2040, 2045, 2050)
BACKGROUNDS = ("REF", "NZE", "BAU")


@dataclass(frozen=True)
class Case:
    background: str = "NZE"
    year: int = 2050
    measures: tuple = tuple(MEASURES)
    adoption: dict = field(default_factory=dict)
    name: str = ""

    def __post_init__(self):
        if self.background not in BACKGROUNDS:
            raise ValueError(f"background must be one of {BACKGROUNDS}")
        if type(self.year) is not int or self.year not in YEARS:
            raise ValueError(f"year must be one of {YEARS}; no interpolation is inferred")
        if isinstance(self.measures, str):
            raise ValueError("measures must be a list/tuple of measure codes")
        if len(set(self.measures)) != len(self.measures) or set(self.measures) - MEASURES.keys():
            raise ValueError(f"Use distinct measures from {tuple(MEASURES)}")
        if not isinstance(self.adoption, dict) or set(self.adoption) - set(self.measures):
            raise ValueError("adoption may only contain selected measures")
        for code, value in self.adoption.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"adoption[{code}] must be a finite number between 0 and 1")
        if self.name and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", self.name):
            raise ValueError("name must use letters, numbers, periods, underscores or hyphens")
        object.__setattr__(self, "measures", tuple(self.measures))
        object.__setattr__(self, "adoption", MappingProxyType(dict(self.adoption)))

    @property
    def identifier(self):
        return self.name or f"{self.background}_{'-'.join(self.measures) or '0'}_{self.year}"

    def strength(self, code):
        return float(self.adoption.get(code, 1.0)) if code in self.measures else 0.0

    def to_dict(self):
        return dict(name=self.identifier, background=self.background, year=self.year,
                    measures=list(self.measures), adoption=dict(self.adoption))

    @classmethod
    def from_json(cls, path):
        value = json.loads(Path(path).read_text())
        if not isinstance(value, dict):
            raise ValueError("A case must be a JSON object")
        unknown = set(value) - {"name", "background", "year", "measures", "adoption"}
        if unknown:
            raise ValueError(f"Unknown case fields: {sorted(unknown)}")
        return cls(**value)

    @classmethod
    def paper(cls, background="NZE", measure="All", year=2050):
        measure = str(measure)
        if measure not in ("All", "0", *MEASURES):
            raise ValueError(f"Unknown paper measure {measure}")
        selected = tuple(MEASURES) if measure == "All" else (() if measure == "0" else (measure,))
        return cls(background, year, selected, name=f"{background}_{measure}_{year}")
