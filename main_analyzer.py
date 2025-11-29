import argparse
import math

from analyzers import syntaxer
from analyzers import interpreter
from analyzers import fuzzer
from analyzers import abstractInterpreter as abs_interp
from collections import Counter

syntaxer.JAVA_ROOT_PATH = "."


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Static Analyzer")
    parser.add_argument("-case", type=str, default="Strings", help="Name of test case.")
    parser.add_argument("-abs", type=str, default="str", help="Type of abstraction (str|int)")

    args = parser.parse_args()

    case_name = args.case

    print("Analyzing methods in {}.java".format(case_name))

    # Syntactic Analysis
    methods = syntaxer.get_simplify_ast(case_name)

    # Semantic Analysis
    total_case_num = 0
    passed_case_num = 0

    dynamic_results = {"ok":0}
    static_results = {"ok":0}

    case_covers = []
    fuzz_covers = []
    integrate_covers = []
    pre_suf_covers = []
    bricks_covers = []

    total_sign_paths = {"ok": 0, "divide by zero": 0, "assertion error": 0,
                        "out of bounds": 0, "null pointer": 0, "*": 0}
    total_interval_paths = {"ok": 0, "divide by zero": 0, "assertion error": 0,
                            "out of bounds": 0, "null pointer": 0, "*": 0}
    is_strings = args.abs == "str"
    method_results = {}

    for method in methods:
        method_name = method.name
        bytecodes = method.bytecodes

        print("\n[Method] {}:".format(method_name))
        if is_strings:
            method_results[method_name] = {
                'prefix_errors': set(),
                'bricks_errors': set(),
                'integrated_errors': set(),
                'conc_errors': set()
            }

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

            if is_strings:
                if case_result != "ok":
                    error_id = f"{method_name}_{str(case_parameters)}_{case_result}"
                    method_results[method_name]['conc_errors'].add(error_id)

            print("\t\t[{}|{:5.1f}%] ({}) -> {} | {}".format(result,coverage*100,", ".join(str(param) if type(param).__name__ != "str" else "'{}'".format(param) for param in case_parameters),true_result,case_result))

        if len(method.cases) == 0:
            print("\t\t{}".format("This function has no cases to test.".join(["\033[93m","\033[0m"])))
        else:
            total_coverage = len(total_pc_set) / len(method.bytecodes[1])
            case_covers.append(total_coverage)
            print("\t\t[Total coverage]: {:.1f}%".format(total_coverage*100))

        # Coverage-guided Fuzz Test
        print("\t[Fuzz Test]:")
        interest, total_pc_set, results = fuzzer.coverage_guided_fuzzing(method,"\t\t")

        total_coverage = len(total_pc_set) / len(method.bytecodes[1])
        fuzz_covers.append(total_coverage)
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

        print("\t\t[Result]:")
        for result_type in results:
            if sum(results.values())>0:
                print("\t\t\t[{}]: {:.1f}% | {}".format(result_type,results[result_type]/sum(results.values())*100,results[result_type]))
                if result_type not in dynamic_results:
                    dynamic_results[result_type] = 0
                dynamic_results[result_type]+=results[result_type]/sum(results.values())*100

        # Static Analysis
        print("\t[Static Analysis]")
        num_params = len(method.parameters)

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
            integrated_coverage = len(integrated_analyzer.pc_set) / len(method.bytecodes[1])
            integrate_covers.append(integrated_coverage)
            print("\t\t[Integrated Abstraction | {:.1f}%]: {}".format(integrated_coverage*100,integrated_result))
            integrated_results = integrated_result.split(" and ")
            for result in integrated_results:
                if result not in static_results:
                    static_results[result] = 0
                static_results[result] += 1/len(integrated_results)

            prefix_analyzer = abs_interp.AbstractInterpreter(
                bytecodes,
                use_interval=True,
                use_widening=True,
                use_string=True,
                string_abstraction_type='prefix'
            )
            prefix_analyzer.analyze(num_params, param_types=param_types)
            prefix_result = prefix_analyzer.get_string_analysis_summary()
            prefix_errors = prefix_analyzer.get_error_set()
            prefix_coverage = len(prefix_analyzer.pc_set) / len(method.bytecodes[1])
            pre_suf_covers.append(prefix_coverage)
            print("\t\t\t[Prefix/Suffix Abstraction | {:.1f}%]: {}".format(prefix_coverage*100,prefix_result))

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
            bricks_coverage = len(bricks_analyzer.pc_set) / len(method.bytecodes[1])
            bricks_covers.append(bricks_coverage)
            print("\t\t\t[Bricks (Regex) Abstraction | {:.1f}%]: {}".format(bricks_coverage*100,bricks_result))

            method_results[method_name]['prefix_errors'] = prefix_errors
            method_results[method_name]['bricks_errors'] = bricks_errors
            method_results[method_name]['integrated_errors'] = integrated_errors

    case_pass_rate = 0
    case_avg_cover = 0
    fuzz_avg_cover = 0
    integrate_avg_cover = 0
    pre_suf_avg_cover = 0
    bricks_avg_cover = 0

    if total_case_num>0:
        case_pass_rate = passed_case_num / total_case_num * 10 ** 2
    if len(case_covers)>0:
        case_avg_cover = sum(case_covers) / len(case_covers)
    if len(fuzz_covers)>0:
        fuzz_avg_cover = sum(fuzz_covers) / len(fuzz_covers)
    if len(integrate_covers)>0:
        integrate_avg_cover = sum(integrate_covers) / len(integrate_covers)
    if len(pre_suf_covers)>0:
        pre_suf_avg_cover = sum(pre_suf_covers)/len(pre_suf_covers)
    if len(bricks_covers)>0:
        bricks_avg_cover = sum(bricks_covers) / len(bricks_covers)

    analysis_print = [
        "[Case Pass Rate]: {:.2f}% ({}/{})".format(case_pass_rate,passed_case_num,total_case_num),
        "[Dynamic Analysis Result]",]

    for result_type in dynamic_results:
        if sum(dynamic_results.values()) > 0:
            analysis_print.append("\t[{}]: {:.1f}%".format(result_type, dynamic_results[result_type] / sum(dynamic_results.values()) * 100))

    analysis_print.append("[Static Analysis Result]")

    for result_type in static_results:
        if sum(static_results.values())>0:
            analysis_print.append("\t[{}]: {:.1f}%".format(result_type, static_results[result_type] / sum(static_results.values()) * 100))

    analysis_print += [
        "[Average Coverage]",
        "\t[Case Test]: {:.2f}%".format(case_avg_cover*100),
        "\t[Fuzz Test]: {:.2f}%".format(fuzz_avg_cover*100),
        "\t[Integrated Abstraction]: {:.2f}%".format(integrate_avg_cover*100),
        "\t\t[Prefix/Suffix Abstraction]: {:.2f}%".format(pre_suf_avg_cover*100),
        "\t\t[Bricks (Regex) Abstraction]: {:.2f}%".format(bricks_avg_cover*100),
        ]
    print("=" * max(len(info.expandtabs())+2 for info in analysis_print))
    print("Analysis Conclusion")
    print("=" * max(len(info.expandtabs())+2 for info in analysis_print))
    print("\n".join(analysis_print))
    print("-" * max(len(info.expandtabs())+2 for info in analysis_print))

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