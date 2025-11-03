import sys
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

        print(f"\n[DEBUG] Method: '{method.name}', Return Type: '{method.return_type}'")
    
        print(f"\n[Analyzer] Starting analysis for method: {method_name}")

        for case in method.cases:
            case_parameters = case["inputs"]
            true_result = case["result"]

            # Perform semantic analysis on each case of the method in interpreter

    jvm_interpreter = interpreter.Interpreter()
    
    result_parser = interpreter.Interpreter()

    for method in methods:
        method_name = method.name
        bytecodes = method.bytecodes
        print(f"\n[Analyzer] Starting analysis for method: {method_name}")

        for i, case in enumerate(method.cases):
            case_parameters = case["inputs"]
            true_result = case["result"]
            
            try:
                # Use the parser to get the expected output
                expected_output = result_parser._parse_expected_result(true_result)
                
                # Run the main interpreter
                actual_output = jvm_interpreter.execute_method(method, case_parameters)
                
                if actual_output == expected_output:
                    print(f"  Case {i+1:2d} PASSED: Input {case_parameters} -> Result {actual_output}")
                else:
                    print(f"  Case {i+1:2d} FAILED: Input {case_parameters}, Expected {expected_output}, Got {actual_output}")
            
            # ** FIX 1: This block catches the expected errors **
            except (AssertionError, ArithmeticError) as e:
                actual_output_str = str(e) # e.g., "assertion error" or "divide by zero"
                
                # Re-parse expected output
                expected_output = result_parser._parse_expected_result(true_result)

                if expected_output == "assertion error" and isinstance(e, AssertionError):
                    print(f"  Case {i+1:2d} PASSED (Caught Expected Error): Input {case_parameters} -> Result {actual_output_str}")
                
                elif expected_output == "divide by zero" and isinstance(e, ArithmeticError):
                     print(f"  Case {i+1:2d} PASSED (Caught Expected Error): Input {case_parameters} -> Result {actual_output_str}")
                
                else:
                    print(f"  Case {i+1:2d} FAILED (Wrong Error): Input {case_parameters}, Expected {expected_output}, Got {actual_output_str}")

            except NotImplementedError as e:
                print(f"  Case {i+1:2d} SKIPPED: Missing Opcode: {e}")
            except Exception as e:
                # ** FIX 3: Correct the typo '2ds' to '2d' **
                print(f"  Case {i+1:2d} FAILED (Runtime Error): {type(e).__name__}: {e}")