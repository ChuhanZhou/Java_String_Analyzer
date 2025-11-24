import sys
import re
from pathlib import Path
import argparse


from analyzers import syntaxer
from analyzers import interpreter
from analyzers import fuzzer

syntaxer.JAVA_ROOT_PATH = "."


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Static Analyzer")
    parser.add_argument("-case", type=str, default="Strings", help="Name of test case.")

    args = parser.parse_args()

    case_name = args.case

    print("Analyzing methods in {}.java".format(case_name))

    # Syntactic Analysis
    methods = syntaxer.get_simplify_ast(case_name)

    # Semantics Analysis
    total_case_num = 0
    passed_case_num = 0
    for method in methods:
        method_name = method.name
        bytecodes = method.bytecodes

        print("\n[Method] {}:".format(method_name))

        # Dynamic Analysis
        print("\t[Case Test]:")

        total_pc_set = set()
        for case in method.cases:
            case_parameters = case["inputs"]
            true_result = case["result"]

            case_result, pc_set = interpreter.run_test_case(
                method.bytecodes,
                case_parameters,
                method.parameters
            )

            coverage = len(pc_set) / len(method.bytecodes[1])
            total_pc_set |= pc_set

            total_case_num += 1
            result = "FAIL".join(["\033[91m","\033[0m"])
            if case_result == true_result:
                result = "PASS".join(["\033[92m","\033[0m"])
                passed_case_num += 1

            print("\t\t[{}|{:5.1f}%] ({}) -> {} | {}".format(result,coverage*100,", ".join(str(param) if type(param).__name__ != "str" else "'{}'".format(param) for param in case_parameters),true_result,case_result))

        if len(method.cases) == 0:
            print("\t\t{}".format("This function has no cases to test.".join(["\033[93m","\033[0m"])))
        else:
            total_coverage = len(total_pc_set) / len(method.bytecodes[1])
            print("\t\t[Total coverage]: {:.1f}%".format(total_coverage*100))

        # Coverage-guided Fuzz Test
        print("\t[Fuzz Test]:")
        interest, total_pc_set = fuzzer.coverage_guided_fuzzing(method,"\t\t")

        total_coverage = len(total_pc_set) / len(method.bytecodes[1])
        print("\t\t[Total coverage]: {:.1f}%".format(total_coverage * 100))

        print("\t\t[Interest]:")
        report = []
        if len(method.parameters) == 0:
            report.append("\t\t\tThis method has no parameter.")

        for i,parameter in enumerate(method.parameters):
            type_str = parameter["type"][0]
            if parameter["type"][1]:
                type_str += "[]"
            report.append("\t\t\t({} {}): {}".format(type_str, parameter["name"], list(interest[i])))
        print("\n".join(report))

        # Static Analysis


    
    analysis_print = "[Case Pass Rate]: {:.2f}% ({}/{})".format(passed_case_num/total_case_num*10**2,passed_case_num,total_case_num)
    print("-"*len(analysis_print))
    print(analysis_print)
    print("-"*len(analysis_print))