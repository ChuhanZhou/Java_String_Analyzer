from pathlib import Path
import argparse
from typing import Dict, Set, List, Any


from analyzers import syntaxer
from analyzers import interpreter
from analyzers import abstractInterpreter as abs_interp
from collections import Counter

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

    total_sign_paths = {"ok": 0, "divide by zero": 0, "assertion error": 0, 
                       "out of bounds": 0, "null pointer": 0, "*": 0}
    total_interval_paths = {"ok": 0, "divide by zero": 0, "assertion error": 0,
                           "out of bounds": 0, "null pointer": 0, "*": 0}
    is_strings = True

    method_results = {}
    
    for method in methods:
        method_name = method.name
        bytecodes = method.bytecodes

        num_params = len(method.parameters)

        print(f"\n{'=' * 80}")
        print(f"Method: {method_name}")
        print(f"{'=' * 80}")

        print("\n[Abstract Analysis]")

        param_types = []
        for param in method.parameters:
            param_name = str(param.name if hasattr(param, 'name') else param).lower()
            param_type_str = str(param.type if hasattr(param, 'type') else '').lower()
            
            if 'string' in param_type_str or 's' == param_name or 'str' in param_name:
                param_types.append('String')
            elif 'int' in param_type_str or any(c in param_name for c in ['i', 'n', 'x', 'y']):
                param_types.append('int')
            else:
                param_types.append('int')
        
        
        if not is_strings:
            # Sign Domain
            sign_analyzer = abs_interp.AbstractInterpreter(
                bytecodes, 
                use_interval=False, 
                use_widening=False,
                use_string=False,
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
                use_widening=True,
                use_string=False,
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
        else:
            print("\n[1] Prefix/Suffix Abstraction")
            prefix_analyzer = abs_interp.AbstractInterpreter(
                bytecodes, 
                use_interval=True, 
                use_widening=True,
                use_string= True,
                string_abstraction_type='prefix'
            )
            prefix_analyzer.analyze(num_params, param_types=param_types)
            prefix_result = prefix_analyzer.get_string_analysis_summary()
            prefix_errors = prefix_analyzer.get_error_set()

            print(f"  Result: {prefix_result}")

            print("\n[2] Bricks (Regex) Abstraction")
            bricks_analyzer = abs_interp.AbstractInterpreter(
                bytecodes,
                use_interval=True,
                use_widening=True,
                use_string=True,
                string_abstraction_type='bricks'
            )
            bricks_analyzer.analyze(num_params, param_types=param_types)
            bricks_result = bricks_analyzer.get_string_analysis_summary()
            bricks_errors = bricks_analyzer.get_error_set()

            print(f"  Result: {bricks_result}")

            print("\n[3] Integrated Abstraction")
            integrated_analyzer = abs_interp.AbstractInterpreter(
                bytecodes,
                use_interval=True,
                use_widening=True,
                use_string=True,
                string_abstraction_type='integrated'
            )

            integrated_analyzer.analyze(num_params, param_types=param_types)
            integrated_result = integrated_analyzer.get_string_analysis_summary()
            integrated_errors = integrated_analyzer.get_error_set()

            print(f"  Result: {integrated_result}")

            method_results[method_name] = {
                'prefix_errors': prefix_errors,
                'bricks_errors': bricks_errors,
                'integrated_errors': integrated_errors,
                'conc_errors': set()
            }

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
          

            if concrete_match:
                passed_case_num += 1
            
            if is_strings:
                result_lower = result.lower()
                if result != "ok":
                    error_id = f"{method_name}_{str(case_parameters)}_{result}"
                    method_results[method_name]['conc_errors'].add(error_id)


            print(f"\n  Test : {case_parameters}")
            print(f"    Expected:  {expected_result}")
            print(f"    Concrete:  {result}")


    if total_case_num > 0:
        if not is_strings:
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

            print(f"\n[Interval Domain - Overall Probabilities]")
            total_interval_count = sum(total_interval_paths.values())
            if total_interval_count > 0:
                for outcome in ["ok", "divide by zero", "assertion error", "out of bounds", "null pointer", "*"]:
                    count = total_interval_paths[outcome]
                    percentage = (count / total_interval_count) * 100
                    print(f"  {outcome};{percentage:.1f}%")
            else:
                print("  No paths analyzed")
        else:
            print(f"\n{'=' * 80}")
            print(f"[String Analysis Accuracy Statistics]")
            print('=' * 80)
            
            for abstraction_type in ['prefix', 'bricks', 'integrated']:
                print(f"\n[{abstraction_type.upper()} Abstraction Accuracy]")

                all_predicted_errors = set()
                all_actual_errors = set()

                for method_name, results in method_results.items():
                    abs_errors = results[f'{abstraction_type}_errors']

                    for error_type in abs_errors:
                        all_predicted_errors.add(f"{method_name}_{error_type}")

                    all_actual_errors.update(results['conc_errors'])

                true_positives = []
                false_positives = []
                false_negatives = []

                for method_name, results in method_results.items():
                    abs_errors = results[f'{abstraction_type}_errors']
                    conc_error_types = set()
                    for error_id in results['conc_errors']:
                        parts = error_id.rsplit('_', 1)
                        if len(parts) == 2:
                            conc_error_types.add(parts[1])

                    tp = abs_errors.intersection(conc_error_types)
                    if tp:
                        true_positives.extend([f"{method_name}_{e}" for e in tp])

                    fp = abs_errors.difference(conc_error_types)
                    if fp:
                        false_positives.extend([f"{method_name}_{e}" for e in fp])

                    fn = conc_error_types.difference(abs_errors)
                    if fn:
                        false_negatives.extend([f"{method_name}_{e}" for e in fn])

                tp_count = len(true_positives)
                fp_count = len(false_positives)
                fn_count = len(false_negatives)

                predicted_total = tp_count + fp_count          
                actual_total = tp_count + fn_count


                if predicted_total > 0:
                    fp_rate = (fp_count / predicted_total) * 100
                else:
                    fp_rate = 0.0

                if actual_total > 0:
                    fn_rate = (fn_count / actual_total) * 100
                else:
                    fn_rate = 0.0 


                print(f"\n[Abstract Interpreter Precision Summary]")
                print(f" True Positives (TP): {tp_count}")
                print(f" False Positives (FP): {fp_count}")
                if false_positives:
                    fp_types = sorted(list(false_positives))
                    print(f" FP Types: {fp_types}")
                print(f" False Negatives (FN): {fn_count}")
                if false_negatives:
                    fn_types = sorted(list(false_negatives))
                    print(f" FN Types: {fn_types}")
                print("--------------------------------------------------")
                print(f" [FP Rate]: {fp_rate:.2f}%")
                print(f" [FN Rate]: {fn_rate:.2f}%")
        

        analysis_print = f"[Concrete Pass Rate]: {passed_case_num/total_case_num*100:.2f}% ({passed_case_num}/{total_case_num})"
        print(analysis_print)
        print('=' * 80)
                
            
            
            
            
    