"""Extraction of executable code from raw model responses.

Models routinely wrap code in markdown fences or surround it with prose,
even when instructed to return code only. Grading must target the code the
model produced rather than its wrapper, so extraction runs before execution.
"""

from __future__ import annotations

_FENCE = "```"


def extract_code(response: str) -> str:
    """Return the code to grade from a raw model response.

    If the response contains a fenced code block, the contents of the first
    block are returned (an unclosed fence yields everything after it).
    Otherwise the response is returned unchanged, so unfenced output grades
    exactly as it did before extraction existed.
    """
    collected: list[str] = []
    in_block = False
    for line in response.splitlines():
        if line.strip().startswith(_FENCE):
            if in_block:
                return "\n".join(collected) + "\n" if collected else ""
            in_block = True
            continue
        if in_block:
            collected.append(line)
    if in_block:
        return "\n".join(collected) + "\n" if collected else ""
    return response
