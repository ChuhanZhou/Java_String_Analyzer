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
    total_case_num = 0
    passed_case_num = 0
    for method in methods:
        method_name = method.name
        bytecodes = method.bytecodes

        print("[Method] {}:".format(method_name))

        for case in method.cases:
            case_parameters = case["inputs"]
            true_result = case["result"]

            analysis_result = interpreter.run_test_case(
                method.bytecodes,
                case["inputs"],
                method.parameters
            )

            total_case_num += 1
            result = "FAIL"
            if analysis_result == true_result:
                result = "PASS"
                passed_case_num += 1

            print("\t[{}] ({}) => {} | {}".format(result,", ".join(case_parameters),analysis_result,true_result))
    
    analysis_print = "[Pass Rate]: {:.2f}% ({}/{})".format(passed_case_num/total_case_num*10**2,passed_case_num,total_case_num)
    print("-"*len(analysis_print))
    print(analysis_print)
    print("-"*len(analysis_print))