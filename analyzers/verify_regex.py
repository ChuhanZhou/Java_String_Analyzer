from analysis import StringAnalyzer
from abstract import Brick, BricksAbstractValue


def verify_regex_abstraction():
    """
    Verification script for 'RegexAbstractionExample.java'.
    Demonstrates: Structure preservation, Suffix checks, and Branch merging.
    """
    analyzer = StringAnalyzer()
    print("===========================================================")
    print("   VERIFICATION: RegexAbstractionExample.java ")
    print("===========================================================\n")

    # ---------------------------------------------------------
    # Scenario 1: Server Log Generation
    # Goal: Verify structure [Prefix] -> [Loop] -> [Suffix]
    # ---------------------------------------------------------
    print("--- Scenario 1: Server Log Generation ---")

    # 1. Prefix
    v_prefix = analyzer.analyze_assignment("[INFO] ")

    # 2. Loop Body Simulation
    loop_brick = Brick(frozenset(["."]), 1, -1)
    v_loop = BricksAbstractValue([loop_brick])

    # 3. Suffix
    v_suffix = analyzer.analyze_assignment("\n")

    # Concatenate: Prefix + Loop + Suffix
    v_temp = analyzer.analyze_concatenation(v_prefix, v_loop)
    v_log = analyzer.analyze_concatenation(v_temp, v_suffix)

    print(f"Abstract State: {v_log}")

    # Verification:
    bricks = v_log.bricks
    if len(bricks) == 3:
        head_ok = any("[INFO]" in s for s in bricks[0].strings)
        tail_ok = "\n" in list(bricks[2].strings)[0]
        if head_ok and tail_ok:
            print("✅ PASS: Structure preserved (Prefix ... Suffix).")
        else:
            print("❌ FAIL: Content mismatch.")
    else:
        print(f"❌ FAIL: Expected 3 bricks, got {len(bricks)}. Structure lost.")
    print("")

    # ---------------------------------------------------------
    # Scenario 2: HTTP Protocol Construction
    # Goal: Verify suffix validation even after Normalization
    # ---------------------------------------------------------
    print("--- Scenario 2: HTTP Protocol Construction ---")

    v_start = analyzer.analyze_assignment("GET /")
    v_resource = analyzer.analyze_assignment("index.html")
    v_proto = analyzer.analyze_assignment(" HTTP/1.1")

    # Concatenate
    # NOTE: All bricks are (1, 1). The Normalizer will merge them into ONE brick.
    # e.g., [{"GET /index.html HTTP/1.1"}]^(1,1)
    v_req_temp = analyzer.analyze_concatenation(v_start, v_resource)
    v_req = analyzer.analyze_concatenation(v_req_temp, v_proto)

    print(f"Abstract State: {v_req}")

    # Verification:
    # Since bricks are merged, verify the suffix inside the strings of the last brick.
    last_brick = v_req.bricks[-1]
    is_suffix_ok = any(s.endswith(" HTTP/1.1") for s in last_brick.strings)

    if is_suffix_ok:
        print("✅ PASS: Suffix ' HTTP/1.1' successfully verified inside merged brick.")
    else:
        print("❌ FAIL: Suffix check failed.")
    print("")

    # ---------------------------------------------------------
    # Scenario 3: SQL Safety (Branch Merging)
    # Goal: Verify keyword preservation after Merge (LUB) and Concatenation
    # ---------------------------------------------------------
    print("--- Scenario 3: SQL Safety (Branch Merging) ---")

    v_true = analyzer.analyze_assignment("DELETE")
    v_false = analyzer.analyze_assignment("SELECT")

    # Merge (LUB): Result is a set of strings [{"DELETE", "SELECT"}]^(1,1)
    v_merged = analyzer.merge_values(v_true, v_false)

    v_sql_suffix = analyzer.analyze_assignment(" * FROM users")

    # Concatenate:
    # The Normalizer merges the suffix into the set.
    v_final = analyzer.analyze_concatenation(v_merged, v_sql_suffix)

    print(f"Abstract State: {v_final}")

    # Verification:
    # Check if the specific keyword "DELETE" is present at the start of any string in the set.
    first_brick_strings = v_final.bricks[0].strings

    has_delete = any(s.startswith("DELETE") for s in first_brick_strings)
    has_select = any(s.startswith("SELECT") for s in first_brick_strings)

    if has_delete and has_select:
        print("✅ PASS: Keywords 'DELETE' and 'SELECT' preserved in merged strings.")
    else:
        print("❌ FAIL: Keywords lost.")
    print("")


if __name__ == "__main__":
    verify_regex_abstraction()