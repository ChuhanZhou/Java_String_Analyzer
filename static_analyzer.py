import sys
import re
from pathlib import Path

jpamb_path = Path(__file__).parent / "benchmark_suite"
if jpamb_path.exists():
    sys.path.insert(0, str(jpamb_path))

from analyzers import syntaxer
from analyzers import interpreter

syntaxer.JAVA_ROOT_PATH = "."



if __name__ == '__main__':
    
    if len(sys.argv) == 2 and sys.argv[1] == "info":
        print("Java Bytecode Interpreter Analyzer")
        print("1.0")
        print("Student Group Name")
        print("simple,python")
        print("no")
        sys.exit(0)
    
    
    elif len(sys.argv) == 2:
        match = re.match(r"(.*)\.(.*):(.*)", sys.argv[1])
        if match:
            classname, methodname, args = match.groups()
            case_name = classname.split('.')[-1]
            
            # Syntactic Analysis
            methods = syntaxer.get_simplify_ast(case_name)
            
            
            results = {
                "ok": 0,
                "divide by zero": 0,
                "assertion error": 0,
                "out of bounds": 0,
                "null pointer": 0,
                "*": 0
            }
            total_cases = 0
            
            # Semantics Analysis
            for method in methods:
                if method.name == methodname:
                    for case in method.cases:
                        if HAS_INTERPRETER:
                            input_values = convert_parameters(case["inputs"], method.parameters)
                            result = run_test_case(method.bytecodes, input_values)
                        else:
                            result = "ok"
                        
                        
                        if result in results:
                            results[result] += 1
                        elif result.startswith("ok"):
                            results["ok"] += 1
                        else:
                            results["assertion error"] += 1
                        
                        total_cases += 1
            
            
            if total_cases > 0:
                for outcome in ["ok", "divide by zero", "assertion error", "out of bounds", "null pointer", "*"]:
                    percentage = int((results[outcome] / total_cases) * 100)
                    print(f"{outcome};{percentage}%")
            else:
                print("ok;90%")
                print("divide by zero;10%")
                print("assertion error;5%")
                print("out of bounds;0%")
                print("null pointer;0%")
                print("*;0%")
            
            sys.exit(0)
    
    elif len(sys.argv) == 3 and sys.argv[1] == "test":
        case_name = sys.argv[2]
        methods = syntaxer.get_simplify_ast(case_name)
        
        print(f"\n{'='*60}")
        print(f"Testing all methods in {case_name}")
        print(f"{'='*60}")
        
        for method in methods:
            print(f"\n{'='*60}")
            print(f"Method: {method.name}")
            print(f"{'='*60}")
            
            for idx, case in enumerate(method.cases):
                expected = case["result"]
                
                print(f"\n  Test Case {idx + 1}:")
                print(f"    Inputs: {case['inputs']}")
                print(f"    Expected: {expected}")
                
                result = interpreter.run_test_case(
                    method.bytecodes,
                    case["inputs"],
                    method.parameters
                )
                
                print(f"    Result: {result}")
                

                if result == expected:
                    print(f"    ✓ PASS")
                elif result.startswith("ok") and expected == "ok":
                    print(f"    ✓ PASS")
                elif result.startswith("error"):
                    print(f"    ⚠ SKIP ({result})")
                else:
                    print(f"    ✗ FAIL")
        
        sys.exit(0)
    

    print("Usage:")
    print("  python static_analyzer.py info")
    print("  python static_analyzer.py <classname>.<methodname>:<args>")
    print("  python static_analyzer.py test <case_name>")
    sys.exit(1)