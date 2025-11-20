
from dataclasses import dataclass
from pathlib import Path
import sys

class StringBuilderModel:
    def __init__(self, initial_value=""):
        self.parts = [str(initial_value)]
        self.reference_id = id(self)

    def append(self, value):
        self.parts.append("null" if value is None else str(value))
        return self

    def toString(self):
        return "".join(self.parts)

    def __repr__(self):
        return f"<StringBuilderRef ID={self.reference_id}>"

def run_bytecodes(bytecodes_tuple, input_values):
    modifiers, instructions = bytecodes_tuple
    

    locals_dict = {}
    for i, v in enumerate(input_values):
        locals_dict[i] = v
    
    stack = []
    pc = 0
 

    for _ in range(50000):
        if pc >= len(instructions):
            return "ok"
        
        
        instruction = instructions[pc]
        
        offset = instruction[0]
        opcode = instruction[1]
        args = instruction[2:] if len(instruction) > 2 else []


        if opcode == "iconst":
            if args[0] == "m1":
                stack.append(-1)
            else:
                stack.append(int(args[0]))
            pc += 1
            
        elif opcode == "bipush" or opcode == "sipush":
            stack.append(int(args[0]))
            pc += 1
            
        elif opcode == "ldc":
            if isinstance(args[0], tuple) and len(args[0]) >= 2:
                const_type = args[0][0]
                const_value = args[0][1]
                if const_type == "int":
                    stack.append(int(const_value))
                elif const_type == "str":
                    stack.append(str(const_value))
                else:
                    stack.append(const_value)
            else:
                stack.append(args[0])

            pc += 1

        elif opcode == "aconst":
            # Load null reference
            if args[0] == "null":
                stack.append(None)
            pc += 1
            
        elif opcode == "iload":
            idx = int(args[0]) if args else 0
            stack.append(locals_dict.get(idx, 0))
            pc += 1

        elif opcode == "aload":
            # Load reference from local variable (for strings/objects)
            idx = int(args[0]) if args else 0
            value = locals_dict.get(idx)
            stack.append(value)
            pc += 1
            
        elif opcode == "istore":
            idx = int(args[0]) if args else 0
            locals_dict[idx] = stack.pop()
            pc += 1
        
        elif opcode == "astore":
            # Store reference to local variable (for strings/objects)
            idx = int(args[0]) if args else 0
            value = stack.pop()

            # Ensure strings stay as strings
            if isinstance(value, str) or value is None:
                locals_dict[idx] = value
            else:
                locals_dict[idx] = value
            pc += 1
            
        elif opcode == "iadd":
            v2, v1 = stack.pop(), stack.pop()
            stack.append(v1 + v2)
            pc += 1
            
        elif opcode == "isub":
            v2, v1 = stack.pop(), stack.pop()
            stack.append(v1 - v2)
            pc += 1
            
        elif opcode == "imul":
            v2, v1 = stack.pop(), stack.pop()
            stack.append(v1 * v2)
            pc += 1
            
        elif opcode == "idiv":
            v2, v1 = stack.pop(), stack.pop()
            if v2 == 0:
                return "divide by zero"
            stack.append(v1 // v2)
            pc += 1

        elif opcode == "iinc":
            # Increment local variable
            idx = int(args[0])
            const = int(args[1])
            locals_dict[idx] = locals_dict.get(idx, 0) + const
            pc += 1

        elif opcode == "invokevirtual":
            # Handle virtual method calls (String methods, etc.)
            method_info = args[0]
            method_desc = str(method_info)

            if "tostring" in method_desc.lower():
                builder_ref = stack.pop() 

                if isinstance(builder_ref, StringBuilderModel):
                    final_string = builder_ref.toString()
                    stack.append(final_string) 
                else:
                    if builder_ref is None:
                        return "null pointer exception"
                    stack.append(str(builder_ref))

            
            # String.length()
            elif "length" in method_desc.lower():
                string_obj = stack.pop()
                if string_obj is None:
                    return "null pointer exception"
                # Type check - must be string
                if not isinstance(string_obj, str):
                    return "type error"
                stack.append(len(string_obj))
   
            # String.isEmpty()
            elif "isempty" in method_desc.lower():
                string_obj = stack.pop()
                if string_obj is None:
                    return "null pointer exception"
                if not isinstance(string_obj, str):
                    return "type error"
                stack.append(1 if len(string_obj) == 0 else 0)
            
            # String.charAt(int)
            elif "charat" in method_desc.lower():
                index = stack.pop()
                string_obj = stack.pop()
                if string_obj is None:
                    return "null pointer exception"
                if not isinstance(string_obj, str):
                    return "type error"
                if index < 0 or index >= len(string_obj):
                    return "index out of bounds"
                stack.append(string_obj[index])
            
            # String.substring(int, int)
            elif "substring" in method_desc.lower():
                # Check if it's substring(int, int) or substring(int)
                if "(int)" in method_desc.replace(" ", ""):
                    # substring(int) - from index to end
                    start = stack.pop()
                    string_obj = stack.pop()
                    if string_obj is None:
                        return "null pointer exception"
                    if not isinstance(string_obj, str):
                        return "type error"
                    if start < 0 or start > len(string_obj):
                        return "index out of bounds"
                    stack.append(string_obj[start:])
                else:
                    # substring(int, int)
                    end = stack.pop()
                    start = stack.pop()
                    string_obj = stack.pop()
                    if string_obj is None:
                        return "null pointer exception"
                    if not isinstance(string_obj, str):
                        return "type error"
                    if start < 0 or end > len(string_obj):
                        return "index out of bounds"
                    if start > end:
                        return "index range exception"
                    stack.append(string_obj[start:end])
            
            # String.contains(CharSequence)
            elif "contains" in method_desc.lower():
                substr = stack.pop()
                string_obj = stack.pop()
                if string_obj is None or substr is None:
                    return "null pointer exception"
                if not isinstance(string_obj, str):
                    return "type error"
                stack.append(1 if substr in string_obj else 0)
            
            # String.equals(Object)
            elif "equals" in method_desc.lower():
                other = stack.pop()
                string_obj = stack.pop()
                if string_obj is None:
                    return "null pointer exception"
                stack.append(1 if string_obj == other else 0)
            
            # String.concat(String)
            elif "concat" in method_desc.lower():
                other = stack.pop()
                string_obj = stack.pop()
                if string_obj is None or other is None:
                    return "null pointer exception"
                if not isinstance(string_obj, str):
                    return "type error"
                stack.append(string_obj + str(other))

            elif "append" in method_desc.lower():
                arg = stack.pop()
                builder_ref = stack.pop()

                if builder_ref is None:
                    return "null pointer exception"
                if not isinstance(builder_ref, StringBuilderModel):
                    pass 
                
                builder_ref.append(arg)
                stack.append(builder_ref)
            
            # String.split(String)
            elif "split" in method_desc.lower():
                delimiter = stack.pop()
                string_obj = stack.pop()
                if string_obj is None or delimiter is None:
                    return "null pointer exception"
                if not isinstance(string_obj, str):
                    return "type error"
                # Handle empty delimiter - Java throws exception for empty regex
                if delimiter == "":
                    # Split into individual characters
                    stack.append(list(string_obj))
                else:
                    # Return array as list
                    stack.append(string_obj.split(delimiter))
            
            # String.toLowerCase()
            elif "tolowercase" in method_desc.lower():
                string_obj = stack.pop()
                if string_obj is None:
                    return "null pointer exception"
                if not isinstance(string_obj, str):
                    return "type error"
                stack.append(string_obj.lower())
            
            # String.toUpperCase()
            elif "touppercase" in method_desc.lower():
                string_obj = stack.pop()
                if string_obj is None:
                    return "null pointer exception"
                if not isinstance(string_obj, str):
                    return "type error"
                stack.append(string_obj.upper())
            
            # String.replace(CharSequence, CharSequence)
            elif "replace" in method_desc.lower():
                replacement = stack.pop()
                target = stack.pop()
                string_obj = stack.pop()
                if string_obj is None or target is None or replacement is None:
                    return "null pointer exception"
                if not isinstance(string_obj, str):
                    return "type error"
                stack.append(string_obj.replace(target, replacement))
            
            # String.trim()
            elif "trim" in method_desc.lower():
                string_obj = stack.pop()
                if string_obj is None:
                    return "null pointer exception"
                if not isinstance(string_obj, str):
                    return "type error"
                stack.append(string_obj.strip())
            
            # String.startsWith(String)
            elif "startswith" in method_desc.lower():
                prefix = stack.pop()
                string_obj = stack.pop()
                if string_obj is None or prefix is None:
                    return "null pointer exception"
                if not isinstance(string_obj, str):
                    return "type error"
                stack.append(1 if string_obj.startswith(prefix) else 0)
            
            # String.matches(String) - for regex
            elif "matches" in method_desc.lower():
                regex = stack.pop()
                string_obj = stack.pop()
                if string_obj is None or regex is None:
                    return "null pointer exception"
                if not isinstance(string_obj, str):
                    return "type error"
                import re
                try:
                    stack.append(1 if re.fullmatch(regex, string_obj) else 0)
                except:
                    stack.append(0)
            
            else:
                # Unknown method - just pop the object and any args
                if stack:
                    stack.pop()
            
            pc += 1
        
        elif opcode == "invokestatic":
            # Handle static method calls
            method_info = args[0]
            method_desc = str(method_info)
            
            # Integer.parseInt(String)
            if "parseint" in method_desc.lower():
                string_obj = stack.pop()
                if string_obj is None:
                    return "null pointer exception"
                try:
                    # Java's parseInt doesn't allow leading/trailing spaces
                    if string_obj != string_obj.strip():
                        return "number format exception"
                    stack.append(int(string_obj))
                except ValueError:
                    return "number format exception"
            elif "concatenate" in method_desc.lower() or "concat" in method_desc.lower():
                if len(stack) >= 2:
                    s2 = stack.pop()
                    s1 = stack.pop()

                    sb = StringBuilderModel()
                    sb.append(s1)
                    sb.append(s2)
                    result = sb.toString()
                    stack.append(result)
            else:
                # Unknown static method - do nothing
                pass
            
            pc += 1
        
        elif opcode == "invokedynamic":
            # Handle dynamic invocation (used for String concatenation)
            dynamic_info = args[0]
            
            if isinstance(dynamic_info, dict):
                # Get parameter count
                param_count = len(dynamic_info.get("parameters", []))
                
                # Get values list (constants and None placeholders for variables)
                values = dynamic_info.get("values", [])
                
                # Pop required number of values from stack (in reverse)
                stack_values = []
                for _ in range(param_count):
                    if stack:
                        stack_values.append(stack.pop())
                
                # Check for null values in stack
                for val in stack_values:
                    if val is None:
                        return "null pointer exception"
                
                # Reverse to get correct order
                stack_values.reverse()
                
                # Build result using values list
                result_parts = []
                stack_idx = 0
                for val in values:
                    if val is None:
                        if stack_idx < len(stack_values):
                            v = stack_values[stack_idx]
                            result_parts.append("null" if v is None else str(v))
                            stack_idx += 1
                    else:
                        # This is a constant
                        result_parts.append(str(val))
                
                # Concatenate all parts
                result = "".join(result_parts)
                stack.append(result)
            
            pc += 1
            
        elif opcode in ["if_icmpeq", "if_icmpne", "if_icmplt", "if_icmple", "if_icmpgt", "if_icmpge"]:
            target = int(args[0])
            v2, v1 = stack.pop(), stack.pop()

            #print(f"DEBUG STACK FINAL: v1={v1} | v2={v2} | Remainder={stack}")
            
            should_jump = False
            if opcode == "if_icmpeq":
                should_jump = (v1 == v2)
            elif opcode == "if_icmpne":
                should_jump = (v1 != v2)
            elif opcode == "if_icmplt":
                should_jump = (v1 < v2)
            elif opcode == "if_icmple":
                should_jump = (v1 <= v2)
            elif opcode == "if_icmpgt":
                should_jump = (v1 > v2)
            elif opcode == "if_icmpge":
                should_jump = (v1 >= v2)
            
            if should_jump:
                for i, instr in enumerate(instructions):
                    if instr[0] == target:
                        pc = i
                        break
            else:
                pc += 1

        elif opcode in ["if_acmpeq", "if_acmpne"]:
            # Reference comparison
            target = int(args[0])
            v2, v1 = stack.pop(), stack.pop()
            
            should_jump = False
            if opcode == "if_acmpeq":
                should_jump = (v1 == v2)
            elif opcode == "if_acmpne":
                should_jump = (v1 != v2)
            
            if should_jump:
                for i, instr in enumerate(instructions):
                    if instr[0] == target:
                        pc = i
                        break
            else:
                pc += 1
                
        elif opcode in ["ifeq", "ifne", "iflt", "ifle", "ifgt", "ifge"]:
            target = int(args[0])
            v = stack.pop()
            
            should_jump = False
            if opcode == "ifeq":
                should_jump = (v == 0)
            elif opcode == "ifne":
                should_jump = (v != 0)
            elif opcode == "iflt":
                should_jump = (v < 0)
            elif opcode == "ifle":
                should_jump = (v <= 0)
            elif opcode == "ifgt":
                should_jump = (v > 0)
            elif opcode == "ifge":
                should_jump = (v >= 0)
            
            if should_jump:
                for i, instr in enumerate(instructions):
                    if instr[0] == target:
                        pc = i
                        break
            else:
                pc += 1
        
        elif opcode in ["ifnull", "ifnonnull"]:
            target = int(args[0])
            v = stack.pop()
            
            should_jump = False
            if opcode == "ifnull":
                should_jump = (v is None)
            elif opcode == "ifnonnull":
                should_jump = (v is not None)
            
            if should_jump:
                for i, instr in enumerate(instructions):
                    if instr[0] == target:
                        pc = i
                        break
            else:
                pc += 1
                
        elif opcode == "goto":
            target = int(args[0])
            for i, instr in enumerate(instructions):
                if instr[0] == target:
                    pc = i
                    break
                    
        elif opcode == "invokespecial":
            # check if AssertionError
            if "AssertionError" in str(args):
                return "assertion error"
            pc += 1
            
        elif opcode == "new":
            if args[0] == ('class', 'java/lang/StringBuilder'):
                stack.append(StringBuilderModel())
            else:
                stack.append(-1)
            pc += 1
            
        elif opcode == "dup":
            if stack:
                val = stack[-1]
                stack.append(val)
            pc += 1
        
        elif opcode == "dup2":
            if len(stack) >= 2:
                val2 = stack[-1]
                val1 = stack[-2]
                stack.append(val1)
                stack.append(val2)
            pc += 1
            
        elif opcode == "athrow":
            return "assertion error"
            
        elif opcode == "getstatic":
            # $assertionsDisabled = false 
            stack.append(0)
            pc += 1
        
        elif opcode == "putfield":
            # Store value into field 
            stack.pop()  # value
            stack.pop()  # object reference
            pc += 1
            
        elif opcode == "getfield":
            # Get field from object (for now, just pop object and push placeholder)
            stack.pop()  # object reference
            stack.append(0)
            pc += 1
            
        elif opcode == "ireturn":
            return "ok"
            
        elif opcode == "return":
            return "ok"
        
        elif opcode == "areturn":
            # Return reference (string/object)
            return "ok"
            
        elif opcode == "pop":
            if stack:
                stack.pop()
            pc += 1
        
        elif opcode == "pop2":
            if stack:
                stack.pop()
            if stack:
                stack.pop()
            pc += 1
            
        else:
            pc += 1
    
    return "*"


def run_test_case(bytecodes, case_parameters, method_parameters):
    input_values = case_parameters
    return run_bytecodes(bytecodes, input_values)

