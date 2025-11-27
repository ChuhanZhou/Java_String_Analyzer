from dataclasses import dataclass, field
from typing import Set, List, Optional, Tuple
from enum import Enum


@dataclass(frozen=True)
class Brick:
    strings: frozenset
    min_count: int
    max_count: int

    def __post_init__(self):
        if self.min_count < 0:
            raise ValueError("min_count can not < 0")
        if self.max_count != -1 and self.max_count < self.min_count:
            raise ValueError("max_count must >= min_count")

    @property
    def is_empty(self) -> bool:
        return len(self.strings) == 0 and self.min_count == 0 and self.max_count == 0

    @property
    def is_top(self) -> bool:
        return self.max_count == -1 and self.min_count == 0

    @property
    def is_normalized_form(self) -> bool:
        return (self.min_count == 1 and self.max_count == 1) or \
            (self.min_count == 0 and self.max_count > 0)


@dataclass
class BricksAbstractValue:
    bricks: List[Brick] = field(default_factory=list)

    @staticmethod
    def bottom():
        return BricksAbstractValue([])

    @staticmethod
    def top():
        return BricksAbstractValue([
            Brick(frozenset(['.*']), 0, -1)
        ])

    @staticmethod
    def from_string(s: str):
        return BricksAbstractValue([
            Brick(frozenset([s]), 1, 1)
        ])

    def is_bottom(self) -> bool:
        return len(self.bricks) == 0

    def is_top(self) -> bool:
        return len(self.bricks) == 1 and self.bricks[0].is_top

    def __str__(self) -> str:
        if self.is_bottom():
            return "⊥"
        if self.is_top():
            return "⊤"

        parts = []
        for brick in self.bricks:
            strings_repr = "{" + ", ".join(f'"{s}"' for s in sorted(brick.strings)) + "}"
            max_repr = "∞" if brick.max_count == -1 else str(brick.max_count)
            parts.append(f"[{strings_repr}]^({brick.min_count},{max_repr})")
        return " • ".join(parts)


class BricksNormalizer:

    @staticmethod
    def normalize(bricks: List[Brick]) -> List[Brick]:
        result = list(bricks)
        changed = True

        while changed:
            changed = False
            new_result = []
            i = 0

            while i < len(result):
                brick = result[i]

                if brick.is_empty:
                    changed = True
                    i += 1
                    continue

                if brick.min_count == brick.max_count and brick.min_count > 1:
                    expanded = BricksNormalizer._expand_strings(
                        brick.strings, brick.min_count
                    )
                    new_result.append(Brick(expanded, 1, 1))
                    changed = True
                    i += 1
                    continue

                if i + 1 < len(result):
                    next_brick = result[i + 1]
                    if brick.strings == next_brick.strings:
                        merged = Brick(
                            brick.strings,
                            brick.min_count + next_brick.min_count,
                            (brick.max_count + next_brick.max_count)
                            if brick.max_count != -1 and next_brick.max_count != -1
                            else -1
                        )
                        new_result.append(merged)
                        changed = True
                        i += 2
                        continue

                if brick.min_count > 1 and brick.max_count != brick.min_count:
                    expanded = BricksNormalizer._expand_strings(
                        brick.strings, brick.min_count
                    )
                    new_result.append(Brick(expanded, 1, 1))
                    new_max = (brick.max_count - brick.min_count) \
                        if brick.max_count != -1 else -1
                    new_result.append(Brick(brick.strings, 0, new_max))
                    changed = True
                    i += 1
                    continue

                if brick.min_count == 1 and brick.max_count == 1:
                    if i + 1 < len(result):
                        next_brick = result[i + 1]
                        if next_brick.min_count == 1 and next_brick.max_count == 1:
                            merged_strings = BricksNormalizer._concat_string_sets(
                                brick.strings, next_brick.strings
                            )
                            new_result.append(Brick(merged_strings, 1, 1))
                            changed = True
                            i += 2
                            continue

                new_result.append(brick)
                i += 1
            result = new_result
        return result

    @staticmethod
    def _expand_strings(strings: frozenset, count: int) -> frozenset:
        return frozenset(s * count for s in strings)

    @staticmethod
    def _concat_string_sets(s1: frozenset, s2: frozenset) -> frozenset:
        result = set()
        for str1 in s1:
            for str2 in s2:
                result.add(str1 + str2)
        return frozenset(result)