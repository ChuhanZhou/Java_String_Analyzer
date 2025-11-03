from typing import List, Any, Dict, Optional, Tuple

class Interpreter:
    """
    Final robust Java Bytecode Interpreter with fixes for:
    1. Correctly catching expected exceptions (AssertionError, ArithmeticError).
    2. Robustly enforcing 'void' return types (checking for 'void' OR None).
    """
    
    def __init__(self):
        self.operand_stack: List[Any] = []
        self.local_vars: List[Any] = []
        self.return_value: Optional[Any] = None
        self.assertions_disabled: int = 0 

    # --- Utility Methods ---

    def _parse_inputs(self, inputs: List[str], parameters: List[Dict[str, str]]) -> List[Any]:
        parsed = []
        for i, raw_input in enumerate(inputs):
            param_type = parameters[i]['type']
            if param_type in ['int', 'long']:
                parsed.append(int(raw_input))
            elif param_type == 'boolean':
                parsed.append(raw_input.lower() == 'true')
            elif 'String' in param_type:
                parsed.append(raw_input.strip('"'))
            else:
                parsed.append(raw_input) 
        return parsed
    
    def _parse_expected_result(self, result_str: str) -> Any:
        result_str = result_str.strip()
        
        if result_str.lower() == 'ok':
            return None 
        if "assertion error" in result_str.lower():
            return "assertion error" 
        if "divide by zero" in result_str.lower():
             return "divide by zero" 

        if result_str.isdigit() or (result_str.startswith('-') and result_str[1:].isdigit()):
            return int(result_str)
        if result_str.lower() in ['true', 'false']:
            return result_str.lower() == 'true'
        if result_str.startswith('"') and result_str.endswith('"'):
            return result_str.strip('"')
        return result_str 

    def _get_target_index(self, bytecodes_list: List[Tuple], target_offset: int) -> int:
        for list_index, instruction in enumerate(bytecodes_list):
            bytecode_offset = instruction[0]
            if bytecode_offset == target_offset:
                return list_index
        raise IndexError(f"Jump target offset {target_offset} not found in bytecode list.")

    def _check_stack_size(self, required: int, opcode: str):
        if len(self.operand_stack) < required:
            raise IndexError(f"Opcode {opcode} failed: required {required} items, but stack size is {len(self.operand_stack)}. (pop from empty list)")

    # --- Instruction Execution Core ---

    def _execute_instruction(self, instruction: Tuple, bytecodes_list: List[Tuple], pc: int) -> int:
        
        opcode = instruction[1]
        op_args = instruction[2:]
        
        def get_int_arg(arg):
            if isinstance(arg, tuple):
                arg = arg[0]
            return int(str(arg))

        def safe_int_cast(val):
            if isinstance(val, str) and not val.strip('-').isdigit():
                 raise TypeError(f"Attempted to cast non-numeric string '{val}' to int.")
            if isinstance(val, bool): return int(val) 
            return int(val)

        # --- 1. Load/Store & Constants ---
        
        if opcode.endswith(('load', 'store')) and opcode not in ['aload_0', 'aload_1', 'aload_2', 'aload_3', 'astore_0', 'astore_1', 'astore_2', 'astore_3']:
            local_index = get_int_arg(op_args[0])
            if opcode.endswith('load'):
                self.operand_stack.append(self.local_vars[local_index])
            else:
                self._check_stack_size(1, opcode)
                value = self.operand_stack.pop()
                while len(self.local_vars) <= local_index: self.local_vars.append(None)
                self.local_vars[local_index] = value
            return pc + 1
        
        elif len(opcode) == 7 and opcode.endswith(tuple(map(str, range(4)))):
            index = int(opcode[-1])
            if 'store' in opcode.lower():
                self._check_stack_size(1, opcode)
                value = self.operand_stack.pop()
                while len(self.local_vars) <= index: self.local_vars.append(None)
                self.local_vars[index] = value
            else: # load
                self.operand_stack.append(self.local_vars[index])
            return pc + 1
        
        elif opcode.startswith('iconst_'): 
            const_val_str = opcode.split('_')[1]
            const_val = -1 if const_val_str == 'm1' else int(const_val_str)
            self.operand_stack.append(const_val)
            return pc + 1
            
        elif opcode == 'iconst' and op_args: 
            val = get_int_arg(op_args[0])
            self.operand_stack.append(val)
            return pc + 1

        elif opcode == 'bipush':
            val = get_int_arg(op_args[0])
            self.operand_stack.append(val)
            return pc + 1

        elif opcode == 'ldc':
            raw_val = op_args[0]
            if isinstance(raw_val, tuple): raw_val = raw_val[0]
            try:
                val = int(str(raw_val))
            except ValueError:
                val = str(raw_val).strip('"')
            self.operand_stack.append(val)
            return pc + 1

        # --- 2. Arithmetic/Unary Operations ---
        
        elif opcode.endswith('add'):
            self._check_stack_size(2, opcode); val2 = safe_int_cast(self.operand_stack.pop()); val1 = safe_int_cast(self.operand_stack.pop())
            self.operand_stack.append(val1 + val2)
            return pc + 1
        elif opcode.endswith('sub'):
            self._check_stack_size(2, opcode); val2 = safe_int_cast(self.operand_stack.pop()); val1 = safe_int_cast(self.operand_stack.pop())
            self.operand_stack.append(val1 - val2)
            return pc + 1
        elif opcode.endswith('mul'):
            self._check_stack_size(2, opcode); val2 = safe_int_cast(self.operand_stack.pop()); val1 = safe_int_cast(self.operand_stack.pop())
            self.operand_stack.append(val1 * val2)
            return pc + 1
        elif opcode.endswith('div'):
            self._check_stack_size(2, opcode); val2 = safe_int_cast(self.operand_stack.pop()); val1 = safe_int_cast(self.operand_stack.pop())
            if val2 == 0: raise ArithmeticError("divide by zero")
            self.operand_stack.append(int(val1 / val2)) 
            return pc + 1
        elif opcode.endswith('neg'):
            self._check_stack_size(1, opcode); val = safe_int_cast(self.operand_stack.pop())
            self.operand_stack.append(-val) 
            return pc + 1
        
        # --- 3. Control Flow / Jumps ---
        
        elif opcode == 'goto':
            target_offset = get_int_arg(op_args[0])
            return self._get_target_index(bytecodes_list, target_offset)
            
        elif opcode.startswith('if_icmp'):
            self._check_stack_size(2, opcode); val2 = self.operand_stack.pop(); val1 = self.operand_stack.pop()
            target_offset = get_int_arg(op_args[0])
            jump = False
            if opcode.endswith('eq') and val1 == val2: jump = True
            elif opcode.endswith('ne') and val1 != val2: jump = True
            elif opcode.endswith('lt') and val1 < val2: jump = True
            elif opcode.endswith('ge') and val1 >= val2: jump = True
            elif opcode.endswith('gt') and val1 > val2: jump = True
            elif opcode.endswith('le') and val1 <= val2: jump = True
            return self._get_target_index(bytecodes_list, target_offset) if jump else pc + 1
        
        elif opcode.startswith('if') and len(opcode) <= 4: 
            self._check_stack_size(1, opcode); val = self.operand_stack.pop()
            target_offset = get_int_arg(op_args[0])
            jump = False
            if opcode == 'ifeq' and val == 0: jump = True
            elif opcode == 'ifne' and val != 0: jump = True
            elif opcode == 'iflt' and val < 0: jump = True
            elif opcode == 'ifge' and val >= 0: jump = True
            elif opcode == 'ifgt' and val > 0: jump = True
            elif opcode == 'ifle' and val <= 0: jump = True
            
            return self._get_target_index(bytecodes_list, target_offset) if jump else pc + 1
            
        # --- 4. Stack/Method Operations & Assertions ---
        elif opcode == 'dup':
            self._check_stack_size(1, opcode); val = self.operand_stack[-1]
            self.operand_stack.append(val); return pc + 1
        elif opcode == 'pop': 
            self._check_stack_size(1, opcode); self.operand_stack.pop(); return pc + 1
        
        elif opcode == 'getstatic':
            field_info = op_args[0]
            if isinstance(field_info, tuple):
                field_str = str(field_info[1]) if len(field_info) > 1 else str(field_info[0])
            else:
                field_str = str(field_info)
            if "$assertionsDisabled" in field_str or "assertionsDisabled" in field_str:
                self.operand_stack.append(self.assertions_disabled) # Pushes 0
            else:
                self.operand_stack.append(1) # Push dummy reference
            return pc + 1
        
        elif opcode == 'new':
            self.operand_stack.append(9999) # Push dummy reference
            return pc + 1
        
        elif opcode == 'athrow':
            self._check_stack_size(1, opcode)
            self.operand_stack.pop() # Pop the exception object
            raise AssertionError("assertion error")
        
        elif opcode.endswith('return'):
            if opcode != 'return':
                self._check_stack_size(1, opcode); self.return_value = self.operand_stack.pop()
            else:
                self.return_value = None 
            return pc + 1 

        # --- 5. Complex / Unimplemented (Skip) ---
        elif opcode in ['invokevirtual', 'invokestatic', 'invokespecial', 'throw', 'putfield', 'putstatic']:
            return pc + 1 
        else:
            raise NotImplementedError(f"Interpreter: Unimplemented Java Opcode: {opcode} with args {op_args}")

    # --- Public Execution Methods ---

    def execute_method(self, java_method, inputs: List[str]) -> Any:
        self.operand_stack = []; self.local_vars = []; self.return_value = None
        
        # ** FIX: Check for 'void' AND None **
        method_return_type = java_method.return_type 
        
        parsed_inputs = self._parse_inputs(inputs, java_method.parameters)
        self.local_vars.extend(parsed_inputs)
        bytecodes_list = java_method.bytecodes[1]; pc = 0 
        
        try:
            while pc < len(bytecodes_list):
                instruction = bytecodes_list[pc]
                pc = self._execute_instruction(instruction, bytecodes_list, pc)
                if instruction[1].endswith('return') or instruction[1] == 'athrow':
                    break
        
        except (AssertionError, ArithmeticError) as e:
            raise e # Re-raise intended errors
        except Exception as e:
            raise Exception(f"Runtime Error at offset {instruction[0]}. Original error: {e}")
        
        # ** FIX: Enforce void return by checking if the type is 'void' OR None **
        # This covers both cases: 
        # 1. syntaxer.py explicitly set it to 'void'
        # 2. syntaxer.py didn't set it, so it's the default 'None'
        if method_return_type == 'void' or method_return_type is None or method_return_type == 'void_type':
            return None
            
        return self.return_value

    # This method is not used by static_analyzer.py
    def run_all_tests(self, methods: List):
        pass