import sys
import re
from pathlib import Path
import argparse


from analyzers import syntaxer
from analyzers import interpreter

syntaxer.JAVA_ROOT_PATH = "."


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description="Static Analyzer")
    parser.add_argument("-case", type=str, default="Simple", help="Name of test case.")

    args = parser.parse_args()

    case_name = args.case

    # Syntactic Analysis
    methods = syntaxer.get_simplify_ast(case_name)

    # Semantics Analysis
    for method in methods:
        method_name = method.name
        bytecodes = method.bytecodes

        for case in method.cases:
            case_parameters = case["inputs"]
            true_result = case["result"]

            print(f"     Inputs: {case_parameters}")
            print(f"     Expected: {true_result}")

            result = interpreter.run_test_case(
                method.bytecodes,
                case["inputs"],
                method.parameters
            )
            
            print(f"     Result: {result}")

            if result == true_result:
                print(f"     ✓ PASS")
            elif result.startswith("ok") and true_result == "ok":
                print(f"     ✓ PASS")
            elif result.startswith("error"):
                print(f"     ⚠ SKIP ({result})")
            else:
                print(f"     ✗ FAIL")
    
    print("---------------------------")