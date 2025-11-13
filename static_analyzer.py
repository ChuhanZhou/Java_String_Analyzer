from pathlib import Path
import argparse


from analyzers import syntaxer
from analyzers import interpreter
from analyzers import abstractInterpreter as abs_interp

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
        
        # Interval Domain
        interval_analyzer = abs_interp.AbstractInterpreter(
            bytecodes, 
            use_interval=True, 
            use_widening=True
        )
        interval_analyzer.analyze(num_params)
        interval_result = interval_analyzer.get_result_string()
        print(f"  Interval Domain: {interval_result}")

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
        analysis_print = f"[Pass Rate]: {passed_case_num/total_case_num*100:.2f}% ({passed_case_num}/{total_case_num})"
        print(analysis_print)
        print('=' * 80)
                
            
            
            
            
    