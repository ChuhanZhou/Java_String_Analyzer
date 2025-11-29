
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

    def get_min_length(self) -> int:

        if not self.strings:
            return 0
        min_str_len = min(len(s) for s in self.strings)
        return min_str_len * self.min_count

    def get_max_length(self) -> Optional[int]:

        if self.max_count == -1:
            return None
        if not self.strings:
            return 0
        max_str_len = max(len(s) for s in self.strings)
        return max_str_len * self.max_count

@dataclass
class BricksAbstractValue:

    bricks: List[Brick] = field(default_factory=list)
    can_be_null: bool = False


    @staticmethod
    def bottom() -> "BricksAbstractValue":
        return BricksAbstractValue([])

    @staticmethod
    def top() -> "BricksAbstractValue":
        return BricksAbstractValue([
            Brick(frozenset(['.*']), 0, -1)
        ], can_be_null=True)

    @staticmethod
    def from_string(s: str) -> "BricksAbstractValue":
        if s is None:
            return BricksAbstractValue.null()
        return BricksAbstractValue([
            Brick(frozenset([s]), 1, 1)
        ])

    @staticmethod
    def null() -> "BricksAbstractValue":
        return BricksAbstractValue(bricks=[], can_be_null=True)


    def is_bottom(self) -> bool:

        return len(self.bricks) == 0 and not self.can_be_null

    def is_top(self) -> bool:

        return len(self.bricks) == 1 and self.bricks[0].is_top

    def is_definitely_null(self) -> bool:

        return self.can_be_null and len(self.bricks) == 0

    def is_definitely_not_null(self) -> bool:

        return not self.can_be_null

    def is_possibly_null(self) -> bool:

        return self.can_be_null and len(self.bricks) > 0


    def __str__(self) -> str:
        if self.is_bottom():
            return "⊥"
        if self.is_top():
            return "⊤"
        if self.is_definitely_null():
            return "null"

        parts = []
        for brick in self.bricks:
            strings_repr = "{" + ", ".join(f'"{s}"' for s in sorted(brick.strings)) + "}"
            max_repr = "∞" if brick.max_count == -1 else str(brick.max_count)
            parts.append(f"[{strings_repr}]^({brick.min_count},{max_repr})")
        
        result = " • ".join(parts) if parts else "ε"
        if self.can_be_null:
            result += " +null"
        return result


    def length(self) -> Tuple[int, Optional[int]]:

        if self.is_bottom():
            return (0, 0)
        
        if self.is_top():
            return (0, None)

        total_min = 0
        total_max = 0
        has_unbounded = False

        for brick in self.bricks:
            total_min += brick.get_min_length()
            
            brick_max = brick.get_max_length()
            if brick_max is None:
                has_unbounded = True
            else:
                total_max += brick_max

        if has_unbounded:
            return (total_min, None)
        return (total_min, total_max)

    def isEmpty(self) -> Optional[bool]:

        if self.is_bottom():
            return None
        
        if self.is_top():
            return None

        min_len, max_len = self.length()
        
        if max_len is not None and max_len == 0:
            return True
        
        if min_len > 0:
            return False
        
        return None


    def startsWith(self, prefix: str) -> Optional[bool]:

        if self.is_bottom():
            return None
        
        if self.is_top():
            return None

        if len(self.bricks) == 0:
            return prefix == ""

        first_brick = self.bricks[0]
        
        if first_brick.min_count == 0:
            return None

        all_start_with = True
        none_start_with = True

        for s in first_brick.strings:
            if s.startswith(prefix):
                none_start_with = False
            else:
                all_start_with = False
            
            if len(prefix) > len(s) and first_brick.max_count == 1:
                return None

        if all_start_with:
            return True
        if none_start_with:
            return False
        return None

    def endsWith(self, suffix: str) -> Optional[bool]:

        if self.is_bottom():
            return None
        
        if self.is_top():
            return None

        if len(self.bricks) == 0:
            return suffix == ""

        last_brick = self.bricks[-1]
        
        if last_brick.max_count == -1 or last_brick.min_count != last_brick.max_count:
            return None

        if last_brick.min_count != 1 or last_brick.max_count != 1:
            return None

        all_end_with = True
        none_end_with = True

        for s in last_brick.strings:
            if s.endswith(suffix):
                none_end_with = False
            else:
                all_end_with = False

        if all_end_with:
            return True
        if none_end_with:
            return False
        return None

    def equals(self, other: "BricksAbstractValue") -> Optional[bool]:

        if self.is_bottom() or other.is_bottom():
            return None
        
        if self.is_top() or other.is_top():
            return None

        if self.is_definitely_null() and other.is_definitely_null():
            return True
        if self.is_definitely_null() != other.is_definitely_null():
            if self.is_definitely_null() or other.is_definitely_null():
                return False

        if (len(self.bricks) == 1 and len(other.bricks) == 1 and
            self.bricks[0].min_count == 1 and self.bricks[0].max_count == 1 and
            other.bricks[0].min_count == 1 and other.bricks[0].max_count == 1):
            
            if self.bricks[0].strings == other.bricks[0].strings:
                if len(self.bricks[0].strings) == 1:
                    return True
                return None
            
            if not (self.bricks[0].strings & other.bricks[0].strings):
                return False

        self_len = self.length()
        other_len = other.length()
        
        self_min, self_max = self_len
        other_min, other_max = other_len
        
        if self_max is not None and other_min > self_max:
            return False
        if other_max is not None and self_min > other_max:
            return False

        return None

    def contains(self, substring: str) -> Optional[bool]:

        if self.is_bottom():
            return None
        
        if self.is_top():
            return None

        for brick in self.bricks:
            if brick.min_count >= 1:
                if all(substring in s for s in brick.strings):
                    return True

        has_top = any(b.is_top for b in self.bricks)
        if not has_top:
            all_not_contain = all(
                all(substring not in s for s in brick.strings)
                for brick in self.bricks
            )
            if all_not_contain:
                return False

        return None


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

                #rule 1
                if brick.is_empty:
                    changed = True
                    i += 1
                    continue

                # rule2: [S]^(n,n) where n > 1 → [S^n]^(1,1)
                if brick.min_count == brick.max_count and brick.min_count > 1:
                    expanded = BricksNormalizer._expand_strings(
                        brick.strings, brick.min_count
                    )
                    new_result.append(Brick(expanded, 1, 1))
                    changed = True
                    i += 1
                    continue

                # rule3
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

                # rule4: [S]^(m,n) where m > 1 → [S^m]^(1,1) • [S]^(0,n-m)
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

                # rule5
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
        if count == 0:
            return frozenset([''])
        result = frozenset([''])
        for _ in range(count):
            result = BricksNormalizer._concat_string_sets(result, strings)
        return result

    @staticmethod
    def _concat_string_sets(s1: frozenset, s2: frozenset) -> frozenset:

        result = set()
        for str1 in s1:
            for str2 in s2:
                result.add(str1 + str2)
        return frozenset(result)



class BricksAnalysis:

    MAX_LIST_LENGTH = 10
    MAX_STRING_COUNT = 5
    MAX_INDEX_RANGE = 10

    @staticmethod
    def concat(v1: BricksAbstractValue, v2: BricksAbstractValue) -> BricksAbstractValue:

        if v1.is_bottom() or v2.is_bottom():
            return BricksAbstractValue.bottom()

        if v1.is_top() or v2.is_top():
            return BricksAbstractValue.top()

        result_bricks = v1.bricks + v2.bricks
        normalized = BricksNormalizer.normalize(result_bricks)
        

        can_be_null = v1.can_be_null or v2.can_be_null

        return BricksAbstractValue(normalized, can_be_null)

    @staticmethod
    def substring(v: BricksAbstractValue, begin: int, end: int) -> BricksAbstractValue:

        if v.is_bottom():
            return BricksAbstractValue.bottom()

        if v.is_top():
            return BricksAbstractValue.top()

        normalized_bricks = BricksNormalizer.normalize(v.bricks)

        if len(normalized_bricks) > 0:
            first_brick = normalized_bricks[0]
            if first_brick.min_count == 1 and first_brick.max_count == 1:
                if all(len(s) >= end for s in first_brick.strings):
                    extracted = frozenset(
                        s[begin:end] for s in first_brick.strings
                    )
                    return BricksAbstractValue([Brick(extracted, 1, 1)])

        return BricksAbstractValue.top()

    @staticmethod
    def contains(v: BricksAbstractValue, char: str) -> Optional[bool]:

        if v.is_bottom():
            return None

        if v.is_top():
            return None

        for brick in v.bricks:
            if brick.min_count >= 1:
                if all(char in s for s in brick.strings):
                    return True

        has_top = any(b.is_top for b in v.bricks)
        if not has_top:
            all_not_contain = all(
                all(char not in s for s in brick.strings)
                for brick in v.bricks
            )
            if all_not_contain:
                return False

        return None

    @staticmethod
    def lub(v1: BricksAbstractValue, v2: BricksAbstractValue) -> BricksAbstractValue:

        if v1.is_bottom():
            return v2
        if v2.is_bottom():
            return v1

        if v1.is_top() or v2.is_top():
            return BricksAbstractValue.top()

        bricks1 = BricksNormalizer.normalize(v1.bricks)
        bricks2 = BricksNormalizer.normalize(v2.bricks)

        aligned1, aligned2 = BricksAnalysis._align_brick_lists(bricks1, bricks2)

        result_bricks = []
        for b1, b2 in zip(aligned1, aligned2):
            lub_brick = BricksAnalysis._brick_lub(b1, b2)
            result_bricks.append(lub_brick)

        normalized = BricksNormalizer.normalize(result_bricks)

        can_be_null = v1.can_be_null or v2.can_be_null

        return BricksAbstractValue(normalized, can_be_null)

    @staticmethod
    def widening(v_old: BricksAbstractValue, v_new: BricksAbstractValue) -> BricksAbstractValue:

        if len(v_new.bricks) > BricksAnalysis.MAX_LIST_LENGTH:
            return BricksAbstractValue.top()

        result = BricksAnalysis.lub(v_old, v_new)

        widened_bricks = []
        for brick in result.bricks:

            if len(brick.strings) > BricksAnalysis.MAX_STRING_COUNT:
                widened_bricks.append(Brick(frozenset(['.*']), 0, -1))
                continue

            range_size = brick.max_count - brick.min_count \
                if brick.max_count != -1 else float('inf')
            if range_size > BricksAnalysis.MAX_INDEX_RANGE:
                widened_bricks.append(Brick(
                    brick.strings,
                    0,
                    -1
                ))
                continue

            widened_bricks.append(brick)

        return BricksAbstractValue(widened_bricks, result.can_be_null)

    @staticmethod
    def _align_brick_lists(bricks1: List[Brick], bricks2: List[Brick]) -> Tuple[List[Brick], List[Brick]]:

        if len(bricks1) == len(bricks2):
            return bricks1, bricks2

        if len(bricks1) < len(bricks2):
            shorter, longer = bricks1, bricks2
        else:
            shorter, longer = bricks2, bricks1

        empty_brick = Brick(frozenset(['']), 0, 0)
        aligned_shorter = []

        shorter_idx = 0
        for longer_brick in longer:
            if shorter_idx < len(shorter) and shorter[shorter_idx] == longer_brick:
                aligned_shorter.append(shorter[shorter_idx])
                shorter_idx += 1
            else:
                aligned_shorter.append(empty_brick)

        while shorter_idx < len(shorter):
            aligned_shorter.append(shorter[shorter_idx])
            shorter_idx += 1

        if len(bricks1) < len(bricks2):
            return aligned_shorter, longer
        else:
            return longer, aligned_shorter

    @staticmethod
    def _brick_lub(b1: Brick, b2: Brick) -> Brick:

        strings = b1.strings | b2.strings
        min_count = min(b1.min_count, b2.min_count)
        max_count = max(b1.max_count, b2.max_count) \
            if b1.max_count != -1 and b2.max_count != -1 else -1

        return Brick(strings, min_count, max_count)


class StringAnalyzer:


    def __init__(self):
        self.analysis = BricksAnalysis()

    def analyze_assignment(self, value: str) -> BricksAbstractValue:

        return BricksAbstractValue.from_string(value)

    def analyze_concatenation(self, left: BricksAbstractValue,
                              right: BricksAbstractValue) -> BricksAbstractValue:

        return self.analysis.concat(left, right)

    def analyze_substring(self, value: BricksAbstractValue,
                          start: int, end: int) -> BricksAbstractValue:

        return self.analysis.substring(value, start, end)

    def check_contains(self, value: BricksAbstractValue, char: str) -> Optional[bool]:

        return self.analysis.contains(value, char)

    def merge_values(self, v1: BricksAbstractValue,
                     v2: BricksAbstractValue) -> BricksAbstractValue:

        return self.analysis.lub(v1, v2)

    def widen_values(self, v_old: BricksAbstractValue,
                     v_new: BricksAbstractValue) -> BricksAbstractValue:

        return self.analysis.widening(v_old, v_new)


