from enum import Enum
from typing import Any, Dict, List, TypeAlias, Union


JSONType: TypeAlias = Union[Dict[str, Any], List[Any], str, int, float, bool]

STRING_SCHEMA = {"type": "string"}


class AssertType(Enum):
    EXACT = "exact"
    CONTAINS = "contains"
