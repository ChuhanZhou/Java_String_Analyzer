from typing import List, Optional, Tuple
from abstract import Brick, BricksAbstractValue, BricksNormalizer


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

        return BricksAbstractValue(normalized)

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

        return BricksAbstractValue(normalized)

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

        return BricksAbstractValue(widened_bricks)

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


def demonstrate_bricks_analysis():
    analyzer = StringAnalyzer()

def demonstrate_bricks_analysis():
    analyzer = StringAnalyzer()

    print("Bricks Demonstration\n")

    print("Example 1: String Concatenation")
    v1 = analyzer.analyze_assignment("SELECT ")
    v2 = analyzer.analyze_assignment("FROM")
    v_concat = analyzer.analyze_concatenation(v1, v2)
    print(f"  'SELECT ' + 'FROM' = {v_concat}")

    print("\nExample 2: Conditional Branch Merging")
    v_then = analyzer.analyze_assignment("path/to/file")
    v_else = analyzer.analyze_assignment("path/to/dir")
    v_merged = analyzer.merge_values(v_then, v_else)
    print(f"  merge('path/to/file', 'path/to/dir') = {v_merged}")

    print()
    print("Widening\n")

    print("【Trigger 1: String Count Exceeded (> 5)】")
    print("Simulating Loop: Adding different numbers in each iteration")

    v = analyzer.analyze_assignment("")

    for i in range(7):
        new_char = analyzer.analyze_assignment(str(i))
        v_new = analyzer.analyze_concatenation(v, new_char)
        v_widened = analyzer.widen_values(v, v_new)

        print(f"Iteration {i}:")
        print(f"  v_new = {v_new}")

        if not v_widened.is_top():
            string_count = len(v_widened.bricks[0].strings) if v_widened.bricks else 0
            print(f"  widening → {v_widened}")
            print(f"  String Count: {string_count}")
        else:
            print(f"  widening → ⊤  ← Widening Triggered! String Count Exceeded 5")
            break

        v = v_widened
        print()

    print()
    print("【Trigger 2: Index Range Exceeded (max - min > 10)】")
    print("Simulating Loop: Repeat count constantly increasing")

    # Assuming BricksAbstractValue and Brick definitions exist elsewhere
    v_init = BricksAbstractValue([Brick(frozenset(["x"]), 1, 1)])
    print(f"Initial: {v_init}")

    v_iter1 = BricksAbstractValue([Brick(frozenset(["x"]), 1, 3)])
    v_w1 = analyzer.widen_values(v_init, v_iter1)
    print(f"\nIteration 1: {v_iter1}")
    print(f"  widening → {v_w1}")

    v_iter2 = BricksAbstractValue([Brick(frozenset(["x"]), 1, 7)])
    v_w2 = analyzer.widen_values(v_w1, v_iter2)
    print(f"\nIteration 2: {v_iter2}")
    print(f"  widening → {v_w2}")

    v_iter3 = BricksAbstractValue([Brick(frozenset(["x"]), 1, 15)])
    v_w3 = analyzer.widen_values(v_w2, v_iter3)
    print(f"\nIteration 3: {v_iter3}")
    print(f"  Range: 15-1 = 14 > 10  ← Exceeded!")
    print(f"  widening → {v_w3}")

    print()
    print("【Trigger 3: Brick List Length Exceeded (> 10)】")
    print("Simulating Loop: Inserting characters at different positions in each iteration\n")

    bricks = []
    for i in range(12):
        # Assuming Brick is defined
        bricks.append(Brick(frozenset([str(i)]), 1, 1))

    v_many_bricks = BricksAbstractValue(bricks[:11])
    print(f"Constructed abstract value with {len(v_many_bricks.bricks)} bricks")
    print(f"Brick List: {v_many_bricks}")

    v_base = BricksAbstractValue([Brick(frozenset(["base"]), 1, 1)])
    v_widened_final = analyzer.widen_values(v_base, v_many_bricks)

    print(f"\nwidening Result: {v_widened_final}")

    print("\nExample 4: Character Containment Check")
    v_test = analyzer.analyze_assignment("SELECT")
    contains_s = analyzer.check_contains(v_test, 'SE')
    contains_x = analyzer.check_contains(v_test, 'X')
    print(f"  'SELECT' contains 'SE': {contains_s}")
    print(f"  'SELECT' contains 'X': {contains_x}")

    print("\nExample 5: Substring Operation")

    print("\nCase 1: Successful Extraction (Single String)")
    v1 = analyzer.analyze_assignment("SELECT * FROM users")
    v_sub1 = analyzer.analyze_substring(v1, 0, 6)
    print(f"  'SELECT * FROM users' get [0:6] = {v_sub1}")

    print("\nCase 2: Successful Extraction (Multiple Strings)")
    v_path1 = analyzer.analyze_assignment("path/to/file.txt")
    v_path2 = analyzer.analyze_assignment("path/to/dir_name")
    v_merged = analyzer.merge_values(v_path1, v_path2)
    print(f"  Original Value: {v_merged}")
    v_sub2 = analyzer.analyze_substring(v_merged, 0, 7)
    print(f"  extract first 7 characters [0:7]: {v_sub2}")

    print("\nCase 3: Extraction Failed (String Too Short)")
    v3 = analyzer.analyze_assignment("short")
    print(f"  Original Value: {v3}")
    v_sub3 = analyzer.analyze_substring(v3, 0, 10)
    print(f"  Attempting to extract [0:10]: {v_sub3}")
    print(f"  → String length is only 5, cannot extract 10 characters, returning ⊤")

    print("\nCase 4: Extraction Failed (Uncertain Repeat Count)")
    v4 = analyzer.analyze_assignment("x")
    v4_repeat = BricksAbstractValue([Brick(frozenset(["x"]), 1, 3)])
    print(f"  Original Value: {v4_repeat}  (Represents 'x', 'xx', or 'xxx')")
    v_sub4 = analyzer.analyze_substring(v4_repeat, 0, 2)
    print(f"  Attempting to extract [0:2]: {v_sub4}")
    print(f"  → Not in ^(1,1) form, cannot determine what to extract, returning ⊤")

    print("\nCase 5: Successful Extraction (Prefix Check)")
    v_prefix = analyzer.analyze_assignment("prefix")
    v_suffix = BricksAbstractValue([Brick(frozenset(["suffix"]), 0, 1)])
    v5 = analyzer.analyze_concatenation(v_prefix, v_suffix)
    print(f"  Original Value: {v5}  (Could be 'prefix' or 'prefixsuffix')")
    v_sub5 = analyzer.analyze_substring(v5, 0, 4)
    print(f"  Attempting to extract [0:4]: {v_sub5}")
    print(f"  → Code only checks the first brick")

    print("\nCase 6: Extraction Failed (Range Spans Multiple Bricks)")
    v_part1 = analyzer.analyze_assignment("ab")
    v_part2 = BricksAbstractValue([Brick(frozenset(["cd"]), 0, 1)])
    v6 = analyzer.analyze_concatenation(v_part1, v_part2)
    print(f"  Original Value: {v6}")
    print(f"  Possible Strings: 'ab' (2 chars) or 'abcd' (4 chars)")

    v_sub6 = analyzer.analyze_substring(v6, 0, 3)
    print(f"  Attempting to extract [0:3]: {v_sub6}")


    print("SQL Security Analysis Demonstration\n")

    print("Scenario 1: Definitely Safe SQL")
    safe_sql = analyzer.analyze_assignment("SELECT id FROM users")
    safe_command = analyzer.analyze_substring(safe_sql, 0, 6)
    print(f"  SQL: {safe_sql}")
    print(f"  Command: {safe_command}")

    check_d = analyzer.check_contains(safe_command, 'D')
    print(f"  Contains 'D': {check_d}")

    print("\nScenario 2: Definitely Dangerous SQL")
    danger_sql = analyzer.analyze_assignment("DELETE FROM users")
    danger_command = analyzer.analyze_substring(danger_sql, 0, 6)
    print(f"  SQL: {danger_sql}")
    print(f"  Command: {danger_command}")
    check_d2 = analyzer.check_contains(danger_command, 'DELETE')
    print(f"  Contains 'DELETE': {check_d2}")


    print("\nScenario 3: Uncertain Scenario (Most Common)")
    sql1 = analyzer.analyze_assignment("SELECT id FROM users")
    sql2 = analyzer.analyze_assignment("DELETE FROM users")
    merged_sql = analyzer.merge_values(sql1, sql2)
    merged_command = analyzer.analyze_substring(merged_sql, 0, 6)
    print(f"  SQL: {merged_sql}")
    print(f"  Command: {merged_command}")

    check_d3 = analyzer.check_contains(merged_command, 'D')
    print(f"  Contains 'D': {check_d3}")

    if check_d3 == True:
        print("  ⚠️ Dangerous: Definitely contains DELETE-related characters!")
    elif check_d3 == None:
        print("  ⚠️ Warning: May contain DELETE command, further checks needed!")
    else:
        print("  ✓ Safe: Definitely does not contain DELETE")


if __name__ == "__main__":
    demonstrate_bricks_analysis()
