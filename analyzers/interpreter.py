
from dataclasses import dataclass
from pathlib import Path
import sys
from loguru import logger

logger.remove()
logger.add(sys.stderr, format="[{level}] {message}")

def run_bytecodes(bytecodes_tuple, input_values):
    modifiers, instructions = bytecodes_tuple
    

    locals_dict = {}
    for i, v in enumerate(input_values):
        locals_dict[i] = v
    
    stack = []
    pc = 0
    

    for _ in range(1000):
        if pc >= len(instructions):
            return "ok"
        
        instruction = instructions[pc]
        offset = instruction[0]
        opcode = instruction[1]
        args = instruction[2:] if len(instruction) > 2 else []
        
        try:
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
                if args[0][0] == "int":
                    stack.append(int(args[0][1]))
                pc += 1
                
            elif opcode == "iload":
                idx = int(args[0]) if args else 0
                stack.append(locals_dict[idx])
                pc += 1
                
            elif opcode == "istore":
                idx = int(args[0]) if args else 0
                locals_dict[idx] = stack.pop()
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
                
            elif opcode in ["if_icmpeq", "if_icmpne", "if_icmplt", "if_icmple", "if_icmpgt", "if_icmpge"]:
                target = int(args[0])
                v2, v1 = stack.pop(), stack.pop()
                
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
                stack.append(-1)
                pc += 1
                
            elif opcode == "dup":
                stack.append(stack[-1])
                pc += 1
                
            elif opcode == "athrow":
                return "assertion error"
                
            elif opcode == "getstatic":
                # $assertionsDisabled = false 
                stack.append(0)
                pc += 1
                
            elif opcode == "ireturn":
                return "ok"
                
            elif opcode == "return":
                return "ok"
                
            elif opcode == "pop":
                stack.pop()
                pc += 1
                
            else:
                pc += 1
                
        except Exception as e:
            return f"error: {e}"
    
    return "*"

def find_target_pc(instructions, target_offset):
    for i, instr in enumerate(instructions):
        if instr[0] == target_offset:
            return i
    return len(instructions)  


def convert_parameters(case_parameters, method_parameters):
    input_values = []
    for i, param in enumerate(case_parameters):
        if i < len(method_parameters):
            param_info = method_parameters[i]
            if isinstance(param_info, dict):
                param_type = param_info.get('type', ('int', False))
                if isinstance(param_type, tuple):
                    param_type = param_type[0]
            else:
                param_type = str(param_info)
            
            
            if param_type == 'bool' or param in ['true', 'false']:
                input_values.append(1 if param == 'true' else 0)
            else:
                input_values.append(int(param))
        else:
            input_values.append(int(param))
    
    return input_values

def run_test_case(bytecodes, case_parameters, method_parameters):
    input_values = convert_parameters(case_parameters, method_parameters)
    return run_bytecodes(bytecodes, input_values)

if __name__ == '__main__':
    opcodes = list(suite.method_opcodes(methodid))
