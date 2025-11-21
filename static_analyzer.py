import sys
import re
from pathlib import Path
import argparse


from analyzers import syntaxer
from analyzers import interpreter

syntaxer.JAVA_ROOT_PATH = "."


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description="Static Analyzer")
    parser.add_argument("-case", type=str, default="Strings", help="Name of test case.")

    args = parser.parse_args()

    case_name = args.case

    # Syntactic Analysis
    methods = syntaxer.get_simplify_ast(case_name)

    # Semantics Analysis
    total_case_num = 0
    passed_case_num = 0
    for method in methods:
        method_name = method.name
        bytecodes = method.bytecodes

        print("[Method] {}:".format(method_name))

        # Dynamic Analysis
        print("\t[Case Test]:")
        if len(method.cases) == 0:
            print("\t\t{}".format("This function has no cases to test.".join(["\033[93m","\033[0m"])))

        for case in method.cases:
            case_parameters = case["inputs"]
            true_result = case["result"]

            case_result, pc_set = interpreter.run_test_case(
                method.bytecodes,
                case_parameters,
                method.parameters
            )
            coverage = len(pc_set) / len(method.bytecodes[1])

            total_case_num += 1
            result = "FAIL".join(["\033[91m","\033[0m"])
            if case_result == true_result:
                result = "PASS".join(["\033[92m","\033[0m"])
                passed_case_num += 1

            print("\t\t[{}|{:5.1f}%] ({}) => {} | {}".format(result,coverage*100,", ".join(str(param) if type(param).__name__ != "str" else "'{}'".format(param) for param in case_parameters),true_result,case_result))

        print("\t[Fuzz Test]:")

        # Static Analysis
    
    analysis_print = "[Case Pass Rate]: {:.2f}% ({}/{})".format(passed_case_num/total_case_num*10**2,passed_case_num,total_case_num)
    print("-"*len(analysis_print))
    print(analysis_print)
    print("-"*len(analysis_print))