from pathlib import Path
import argparse


from analyzers import syntaxer
from analyzers import interpreter
from analyzers import abstractInterpreter as abs_interp
from collections import Counter

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

    total_sign_paths = {"ok": 0, "divide by zero": 0, "assertion error": 0, 
                       "out of bounds": 0, "null pointer": 0, "*": 0}
    total_interval_paths = {"ok": 0, "divide by zero": 0, "assertion error": 0,
                           "out of bounds": 0, "null pointer": 0, "*": 0}
    
    for method in methods:
        method_name = method.name
        bytecodes = method.bytecodes

        num_params = len(method.parameters)

        print(f"\n{'=' * 80}")
        print(f"Method: {method_name}")
        print(f"{'=' * 80}")

        print("\n[Abstract Analysis]")
        
        # Sign Domain
        sign_analyzer = abs_interp.AbstractInterpreter(
            bytecodes, 
            use_interval=False, 
            use_widening=False
        )
        sign_analyzer.analyze(num_params)
        sign_result = sign_analyzer.get_result_string()
        print(f"  Sign Domain:     {sign_result}")
        sign_path_counter = Counter(sign_analyzer.path_results)
        total_sign = len(sign_analyzer.path_results)

        if total_sign > 0:
            print(f"    Total paths: {total_sign}")
            for result, count in sorted(sign_path_counter.items()):
                percentage = (count / total_sign) * 100
                print(f"      - {result}: {count} ({percentage:.1f}%)")
                if result in total_sign_paths:
                    total_sign_paths[result] += count
        
        # Interval Domain
        interval_analyzer = abs_interp.AbstractInterpreter(
            bytecodes, 
            use_interval=True, 
            use_widening=True
        )
        interval_analyzer.analyze(num_params)
        interval_result = interval_analyzer.get_result_string()
        print(f"  Interval Domain: {interval_result}")
        interval_path_counter = Counter(interval_analyzer.path_results)
        total_interval = len(interval_analyzer.path_results)

        if total_interval > 0:
            print(f"    Total paths: {total_interval}")
            for result, count in sorted(interval_path_counter.items()):
                percentage = (count / total_interval) * 100
                print(f"      - {result}: {count} ({percentage:.1f}%)")
                if result in total_interval_paths:
                    total_interval_paths[result] += count

        print(f"\n[Concrete Execution]")
        for case in method.cases:
            case_parameters = case["inputs"]
            expected_result = case["result"]

            result = interpreter.run_test_case(
                method.bytecodes,
                case["inputs"],
                method.parameters
            )

            total_case_num += 1
                
            concrete_match = result == expected_result or (result.startswith("ok") and expected_result == "ok") 
            concrete_mark = "✓" if concrete_match else "✗"

            if concrete_match:
                passed_case_num += 1

            print(f"\n  Test : {case_parameters}")
            print(f"    Expected:  {expected_result}")
            print(f"    Concrete:  {result} {concrete_mark}")

    if total_case_num > 0:
        print(f"\n{'=' * 80}")
        print(f"\n[Sign Domain - Overall Probabilities]")
        total_sign_count = sum(total_sign_paths.values())
        if total_sign_count > 0:
            for outcome in ["ok", "divide by zero", "assertion error", "out of bounds", "null pointer", "*"]:
                count = total_sign_paths[outcome]
                percentage = (count / total_sign_count) * 100
                print(f"  {outcome};{percentage:.1f}%")
        else:
            print("  No paths analyzed")
        
        # 打印 Interval Domain 总体百分比
        print(f"\n[Interval Domain - Overall Probabilities]")
        total_interval_count = sum(total_interval_paths.values())
        if total_interval_count > 0:
            for outcome in ["ok", "divide by zero", "assertion error", "out of bounds", "null pointer", "*"]:
                count = total_interval_paths[outcome]
                percentage = (count / total_interval_count) * 100
                print(f"  {outcome};{percentage:.1f}%")
        else:
            print("  No paths analyzed")
        print("[Concrete Execution Summary]")
        analysis_print = f"[Pass Rate]: {passed_case_num/total_case_num*100:.2f}% ({passed_case_num}/{total_case_num})"
        print(analysis_print)
        print('=' * 80)
                
            
            
            
            
    