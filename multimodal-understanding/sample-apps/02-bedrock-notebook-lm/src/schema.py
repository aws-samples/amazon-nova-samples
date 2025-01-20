"""
schema.py
"""

from typing import List

from pydantic import BaseModel, Field


class DialogueItem(BaseModel):
    """A single dialogue item."""

    # speaker: Literal["Host", "Guest"]
    speaker: str
    text: str


class ShortDialogue(BaseModel):
    """The conversation between the host and guest. Input arguments are scratchpad, name_of_guest and dialogue"""

    scratchpad: str

    dialogue: List[DialogueItem] = Field(
        description="A list of dialogue items, typically between 11 to 17 items."
    )


class MediumDialogue(BaseModel):
    """The conversation between the host and guest. Input arguments are scratchpad, name_of_guest and dialogue"""

    scratchpad: str
    dialogue: List[DialogueItem] = Field(
        description="A list of dialogue items, typically between 19 to 29 items for each speaker."
    )
