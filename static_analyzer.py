import sys
import argparse

from analyzers import syntaxer

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

            # Perform semantic analysis on each case of the method in interpreter
