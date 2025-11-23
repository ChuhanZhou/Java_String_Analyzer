from typing import Dict, List, Set, Tuple, Optional, Union
from collections import Counter
from .sign import Sign, AbstractInt
from .intervalInt import IntervalInt
from .finite_height_string import StringAbstraction

class AbstractFrame(object):  
    def __init__(self, locals, stack):
        self.locals = locals
        self.stack = stack
    
    def copy(self):
        return AbstractFrame(
            locals=self.locals.copy(),
            stack=self.stack.copy()
        )
    
    def join(self, other):
        new_locals = {}
        all_indices = set(self.locals.keys()) | set(other.locals.keys())
        for idx in all_indices:
            val1 = self.locals.get(idx)
            val2 = other.locals.get(idx)
            
            if val1 is None and val2 is None:
                continue
            elif val1 is None:
                new_locals[idx] = val2
            elif val2 is None:
                new_locals[idx] = val1
            else:
                new_locals[idx] = val1.join(val2)
        
        assert len(self.stack) == len(other.stack), f"Stack size mismatch: {len(self.stack)} vs {len(other.stack)}"
        new_stack = [v1.join(v2) for v1, v2 in zip(self.stack, other.stack)]
        
        return AbstractFrame(locals=new_locals, stack=new_stack)
    
    def __eq__(self, other):
        if not isinstance(other, AbstractFrame):
            return False
        return self.locals == other.locals and self.stack == other.stack
    
    def __str__(self):
        return f"Frame(locals={self.locals}, stack={self.stack})"


class AbstractState(object):
    def __init__(self, pc, frame):
        self.pc = pc
        self.frame = frame
    
    def copy(self):
        return AbstractState(pc=self.pc, frame=self.frame.copy())
    
    def join(self, other):
        assert self.pc == other.pc, "Can only join states at same location"
        return AbstractState(pc=self.pc, frame=self.frame.join(other.frame))
    
    def widen(self, other, constants):
        assert self.pc == other.pc
        
        new_locals = {}
        for idx in set(self.frame.locals.keys()) | set(other.frame.locals.keys()):
            val1 = self.frame.locals.get(idx)
            val2 = other.frame.locals.get(idx)
            
            if val1 is None and val2 is None:
                continue
            elif val1 is None:
                new_locals[idx] = val2
            elif val2 is None:
                new_locals[idx] = val1
            elif isinstance(val1, IntervalInt) and isinstance(val2, IntervalInt):
                new_locals[idx] = val1.widen(val2, constants)
            elif isinstance(val1, StringAbstraction) and isinstance(val2, StringAbstraction):
                new_locals[idx] = val1.widen(val2)
            else:
                new_locals[idx] = val1.join(val2)
        
        new_stack = []
        for v1, v2 in zip(self.frame.stack, other.frame.stack):
            if isinstance(v1, IntervalInt) and isinstance(v2, IntervalInt):
                new_stack.append(v1.widen(v2, constants))
            elif isinstance(v1, StringAbstraction) and isinstance(v2, StringAbstraction):
                new_stack.append(v1.widen(v2))
            else:
                new_stack.append(v1.join(v2))
        
        return AbstractState(pc=self.pc, frame=AbstractFrame(locals=new_locals, stack=new_stack))
    
    def __eq__(self, other):
        if not isinstance(other, AbstractState):
            return False
        return self.pc == other.pc and self.frame == other.frame
    
    def __hash__(self):
        return hash(self.pc)
    
    def __str__(self):
        return f"State(pc={self.pc}, {self.frame})"



class StateSet(object):
    def __init__(self):
        self.per_inst = {}
        self.needswork = set()
    
    def add_initial(self, state):
        self.per_inst[state.pc] = state
        self.needswork.add(state.pc)
    
    def per_instruction(self):
        while self.needswork:
            pc = self.needswork.pop()
            if pc in self.per_inst:
                yield (pc, self.per_inst[pc])
    
    def update(self, new_state, use_widening=False, loop_heads=None, constants=None):
        pc = new_state.pc
        
        if pc not in self.per_inst:
            self.per_inst[pc] = new_state
            self.needswork.add(pc)
            return True
        else:
            old_state = self.per_inst[pc]
            
            if use_widening and loop_heads and pc in loop_heads and constants:
                merged = old_state.widen(new_state, constants)
            else:
                merged = old_state.join(new_state)
            
            if merged != old_state:
                self.per_inst[pc] = merged
                self.needswork.add(pc)
                return True
            
            return False
    
    def __ior__(self, new_state):
        self.update(new_state)
        return self
    
    def get_state(self, pc):
        return self.per_inst.get(pc)
    
    def __str__(self):
        return f"StateSet(states={len(self.per_inst)}, needswork={len(self.needswork)})"



class AbstractInterpreter(object):
    def __init__(self, bytecodes_tuple, use_interval=False, use_widening=True, use_string=False):
        modifiers, instructions_list = bytecodes_tuple
        self.bytecodes = instructions_list
        self.use_interval = use_interval
        self.use_widening = use_widening
        self.use_string = use_string
        
        self.instructions = {}
        for bc in self.bytecodes:
            self.instructions[bc[0]] = bc
        
        self.constants = self._extract_constants()
        self.loop_heads = self._detect_loop_heads()
        
        self.state_set = StateSet()
        self.final_states = set()
        self.errors = []

        self.path_results = []
        
        self.iteration_count = 0
        self.join_count = 0
        self.widen_count = 0
    
    def _extract_constants(self):
        constants = {0}
        
        for bc in self.bytecodes:
            opcode = bc[1]
            
            if opcode == "ldc" and len(bc) > 2:
                if isinstance(bc[2], tuple) and bc[2][0] == "int":
                    constants.add(int(bc[2][1]))
            elif opcode in ["bipush", "sipush"] and len(bc) > 2:
                constants.add(int(bc[2]))
            elif opcode.startswith("iconst"):
                if len(bc) > 2:
                    if bc[2] == "m1":
                        constants.add(-1)
                    else:
                        try:
                            constants.add(int(bc[2]))
                        except ValueError:
                            pass
        
        return constants
    
    def _detect_loop_heads(self):
        loop_heads = set()
        
        for bc in self.bytecodes:
            pc = bc[0]
            opcode = bc[1]
            
            if opcode in ["goto", "if_icmpeq", "if_icmpne", "if_icmplt", 
                          "if_icmpge", "if_icmpgt", "if_icmple",
                          "ifeq", "ifne", "iflt", "ifge", "ifgt", "ifle"]:
                if len(bc) > 2:
                    target = int(bc[2])
                    if target <= pc:
                        loop_heads.add(target)
        
        return loop_heads
    
    def create_abstract_value(self, concrete_value):
        if self.use_interval:
            return IntervalInt.from_concrete(concrete_value)
        else:
            return AbstractInt(concrete_value)
        
    def create_abstract_string(self, concrete_string):
        if self.use_string:
            return StringAbstraction.from_string(concrete_string)
        else:
            return StringAbstraction.top()
    
    def create_top(self):
        if self.use_interval:
            return IntervalInt.top()
        else:
            return AbstractInt.top()
    
    def create_string_top(self):
        return StringAbstraction.top()
    
    def analyze(self, num_parameters: int, param_types: list[str] = None, max_iterations=1000):
        initial_locals = {}
        if param_types:
            for i, param_type in enumerate(param_types):
                if param_type in ['String', 'str', 'string']:
                    initial_locals[i] = self.create_string_top()
                elif param_type in ['int', 'integer', 'Integer', 'java.lang.Integer']:
                    initial_locals[i] = self.create_top()
                elif param_type in ['boolean', 'Boolean', 'java.lang.Boolean']:
                    if self.use_interval:
                        initial_locals[i] = IntervalInt(0, 1)
                    else:
                        initial_locals[i] = AbstractInt({Sign.ZERO, Sign.POSITIVE})
                else:
                    initial_locals[i] = self.create_top()
        else:
            for i in range(num_parameters):
                initial_locals[i] = self.create_top()
        
        initial_frame = AbstractFrame(locals=initial_locals, stack=[])   
        initial_state = AbstractState(pc=0, frame=initial_frame)

        self.state_set.add_initial(initial_state)
        self.iteration_count = 0
        
        for pc, state in self.state_set.per_instruction():
            self.iteration_count += 1
            
            if self.iteration_count >= max_iterations:
                print(f"  Warning: reached max iterations {max_iterations}")
                break
            
            if pc not in self.instructions:
                continue
            
            instruction = self.instructions[pc]
            successors = self.step(state, instruction)
            
            for next_state in successors:
                changed = self.state_set.update(
                    next_state,
                    use_widening=self.use_widening,
                    loop_heads=self.loop_heads,
                    constants=self.constants
                )
                
                if changed:
                    if self.use_widening and next_state.pc in self.loop_heads:
                        self.widen_count += 1
                    else:
                        self.join_count += 1
        
        return self.state_set.per_inst
    
    def step(self, state, instruction):
        pc = instruction[0]
        opcode = instruction[1]
        
        if opcode == "iconst":
            return self._handle_iconst(state, instruction)
        elif opcode in ["bipush", "sipush"]:
            return self._handle_push(state, instruction)
        elif opcode == "ldc":
            return self._handle_ldc(state, instruction)
        elif opcode == "iload":
            return self._handle_iload(state, instruction)
        elif opcode == "istore":
            return self._handle_istore(state, instruction)
        elif opcode == "aload":
            return self._handle_aload(state, instruction)
        elif opcode == "astore":
            return self._handle_astore(state, instruction)
        elif opcode == "new":
            return self._handle_new(state, instruction)
        elif opcode == "dup":
            return self._handle_dup(state, instruction)
        elif opcode == "pop":
            return self._handle_pop(state, instruction)
        elif opcode == "iadd":
            return self._handle_iadd(state, instruction)
        elif opcode == "isub":
            return self._handle_isub(state, instruction)
        elif opcode == "imul":
            return self._handle_imul(state, instruction)
        elif opcode == "idiv":
            return self._handle_idiv(state, instruction)
        elif opcode == "irem":
            return self._handle_irem(state, instruction)
        elif opcode == "ineg":
            return self._handle_ineg(state, instruction)
        elif opcode in ["ifeq", "ifne", "iflt", "ifge", "ifgt", "ifle"]:
            return self._handle_ifz(state, instruction)
        elif opcode in ["if_icmpeq", "if_icmpne", "if_icmplt", 
                       "if_icmpge", "if_icmpgt", "if_icmple"]:
            return self._handle_if_icmp(state, instruction)
        elif opcode == "goto":
            return self._handle_goto(state, instruction)
        elif opcode == "getstatic":
            return self._handle_getstatic(state, instruction)
        elif opcode == "putstatic":
            return self._handle_putstatic(state, instruction)
        elif opcode == "athrow": 
            return self._handle_athrow(state, instruction)
        elif opcode == "invokevirtual":
            return self._handle_invokevirtual(state, instruction)
        elif opcode == "invokedynamic":
            return self._handle_invokedynamic(state, instruction)
        elif opcode == "invokespecial":
            return self._handle_invokespecial(state, instruction)
        elif opcode in ["ireturn", "return"]:
            self.path_results.append("ok")
            return []
        else:
            new_state = state.copy()
            new_state.pc = pc + 1
            return [new_state]

    
    def _handle_iconst(self, state, instr):
        new_state = state.copy()
        if len(instr) > 2:
            value = -1 if instr[2] == "m1" else int(instr[2])
        else:
            value = 0
        new_state.frame.stack.append(self.create_abstract_value(value))
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def _handle_push(self, state, instr):
        new_state = state.copy()
        value = int(instr[2])
        new_state.frame.stack.append(self.create_abstract_value(value))
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def _handle_ldc(self, state, instr):
        new_state = state.copy()
        if len(instr) > 2 and isinstance(instr[2], tuple):
            const_type, const_value = instr[2]
            if const_type == "int":
                new_state.frame.stack.append(self.create_abstract_value(int(const_value)))
            elif const_type in ["string", "str", "String"]:
                new_state.frame.stack.append(StringAbstraction.from_string(str(const_value)))
            else:
                new_state.frame.stack.append(self.create_top())
        else:
            new_state.frame.stack.append(self.create_top())
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def _handle_iload(self, state, instr):
        new_state = state.copy()
        idx = int(instr[2])
        if idx in new_state.frame.locals:
            new_state.frame.stack.append(new_state.frame.locals[idx])
        else:
            new_state.frame.stack.append(self.create_top())
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def _handle_istore(self, state, instr):
        if not state.frame.stack:
            return []
        new_state = state.copy()
        idx = int(instr[2])
        new_state.frame.locals[idx] = new_state.frame.stack.pop()
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def _handle_aload(self, state, instr):
        new_state = state.copy()
        idx = int(instr[2]) if len(instr) > 2 else 0
        if idx in new_state.frame.locals:
            new_state.frame.stack.append(new_state.frame.locals[idx])
        else:
            new_state.frame.stack.append(self.create_string_top())
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]

    def _handle_astore(self, state, instr):
        if not state.frame.stack:
            return []
        new_state = state.copy()
        idx = int(instr[2]) if len(instr) > 2 else 0
        new_state.frame.locals[idx] = new_state.frame.stack.pop()
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def _handle_new(self, state, instr):
        new_state = state.copy()
        
        new_state.frame.stack.append(self.create_string_top())
        
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def _handle_dup(self, state, instr):
        if not state.frame.stack:
            return []
        new_state = state.copy()
        new_state.frame.stack.append(new_state.frame.stack[-1])
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def _handle_pop(self, state, instr):
        if not state.frame.stack:
            return []
        new_state = state.copy()
        new_state.frame.stack.pop()
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def _handle_iadd(self, state, instr):
        if len(state.frame.stack) < 2:
            return []
        new_state = state.copy()
        b = new_state.frame.stack.pop()
        a = new_state.frame.stack.pop()
        new_state.frame.stack.append(a + b)
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def _handle_isub(self, state, instr):
        if len(state.frame.stack) < 2:
            return []
        new_state = state.copy()
        b = new_state.frame.stack.pop()
        a = new_state.frame.stack.pop()
        new_state.frame.stack.append(a - b)
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def _handle_imul(self, state, instr):
        if len(state.frame.stack) < 2:
            return []
        new_state = state.copy()
        b = new_state.frame.stack.pop()
        a = new_state.frame.stack.pop()
        new_state.frame.stack.append(a * b)
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def _handle_idiv(self, state, instr):
        if len(state.frame.stack) < 2:
            return []
        new_state = state.copy()
        b = new_state.frame.stack.pop()  
        a = new_state.frame.stack.pop()  
        
        if self.use_interval and isinstance(b, IntervalInt):
            definitely_zero = (b.low == 0 and b.high == 0)
            definitely_not_zero = b.definitely_not_zero()
            possibly_zero = b.contains(0)
        else:  # Sign domain
            definitely_zero = (b.state_set == {Sign.ZERO})
            possibly_zero = (Sign.ZERO in b.state_set)
            definitely_not_zero = not possibly_zero
        
        if definitely_zero:
            self.errors.append(f"PC {state.pc}: Definite division by zero")
            self.path_results.append("divide by zero")
            return []
        
        if definitely_not_zero:
            result = a / b
            new_state.frame.stack.append(result)
            new_state.pc = self._get_next_pc(instr[0])
            return [new_state]
        
        if possibly_zero:
            self.errors.append(f"PC {state.pc}: Possible division by zero")
            if self.use_interval:
                result = IntervalInt.top()
            else:
                result = AbstractInt({Sign.POSITIVE, Sign.NEGATIVE, Sign.ZERO})
            new_state.frame.stack.append(result)
            new_state.pc = self._get_next_pc(instr[0])
            return [new_state]
        
        result = a / b
        new_state.frame.stack.append(result)
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def _handle_irem(self, state, instr):
        if len(state.frame.stack) < 2:
            return []
        new_state = state.copy()
        b = new_state.frame.stack.pop()  
        a = new_state.frame.stack.pop() 
        
        if self.use_interval and isinstance(b, IntervalInt):
            possibly_zero = (b.low <= 0 <= b.high)
        else:  # Sign domain
            possibly_zero = (Sign.ZERO in b.state_set)
        
        if possibly_zero:
            self.errors.append(f"PC {state.pc}: Possible division by zero (remainder)")
            if self.use_interval:
                result = IntervalInt.top()
            else:
                result = AbstractInt({Sign.POSITIVE, Sign.NEGATIVE, Sign.ZERO})
            new_state.frame.stack.append(result)
            new_state.pc = self._get_next_pc(instr[0])
            return [new_state]
        
        if self.use_interval:
            max_divisor = max(abs(b.low), abs(b.high))
            result = IntervalInt(-max_divisor + 1 if a.low < 0 else 0, max_divisor - 1)
        else:
            result = AbstractInt(a.state_set.copy())
        
        new_state.frame.stack.append(result)
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def _handle_ineg(self, state, instr):
        if not state.frame.stack:
            return []
        new_state = state.copy()
        a = new_state.frame.stack.pop()
        new_state.frame.stack.append(-a)
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def _get_next_pc(self, current_pc):
        for bc in self.bytecodes:
            if bc[0] > current_pc:
                return bc[0]
        return current_pc + 1 
    
    def _target_throws_assertion(self, pc):
        instructions_ahead = [instr for instr in self.bytecodes if instr[0] >= pc]
        
        for i, instr in enumerate(instructions_ahead[:10]):
            if instr[1] == "new" and len(instr) > 2:
                class_name = str(instr[2])
                if "AssertionError" in class_name:
                    for j in range(i+1, min(i+6, len(instructions_ahead))):
                        if instructions_ahead[j][1] == "athrow":
                            return True
        return False 
    
    def _handle_ifz(self, state, instr):
        if not state.frame.stack:
            return []
        target = int(instr[2])
        opcode = instr[1]
        
        condition_val = state.frame.stack[-1]
        
        successors = []
        
        # True branch
        true_state = state.copy()
        true_state.frame.stack.pop()
        true_state.pc = target
        
        # False branch 
        false_state = state.copy()
        false_state.frame.stack.pop()
        false_state.pc = self._get_next_pc(instr[0])

        if self._target_throws_assertion(target):
            if isinstance(condition_val, (IntervalInt, AbstractInt)):
                condition_might_be_true = False
                
                if isinstance(condition_val, IntervalInt):
                    if opcode == "ifeq":
                        condition_might_be_true = condition_val.contains(0)
                    elif opcode == "ifne":
                        condition_might_be_true = (condition_val.low < 0 or condition_val.high > 0)
                    elif opcode == "iflt":
                        condition_might_be_true = condition_val.low < 0
                    elif opcode == "ifle":
                        condition_might_be_true = condition_val.low <= 0
                    elif opcode == "ifgt":
                        condition_might_be_true = condition_val.high > 0
                    elif opcode == "ifge":
                        condition_might_be_true = condition_val.high >= 0
                else:  # AbstractInt
                    if opcode == "ifeq":
                        condition_might_be_true = Sign.ZERO in condition_val.state_set
                    elif opcode == "ifne":
                        condition_might_be_true = (Sign.POSITIVE in condition_val.state_set or 
                                                  Sign.NEGATIVE in condition_val.state_set)
                    else:
                        condition_might_be_true = True
                
                if condition_might_be_true:
                    self.errors.append(f"PC {state.pc}: Possible assertion error")
        
        # local variable
        local_idx = None
        for idx, local_val in state.frame.locals.items():
            if local_val == condition_val:
                local_idx = idx
                break
        
        if self.use_interval and isinstance(condition_val, IntervalInt):
            can_be_zero = condition_val.contains(0)
            can_be_nonzero = condition_val.low < 0 or condition_val.high > 0
            
            if opcode == "ifeq":
                if can_be_zero:
                    if local_idx is not None:
                        true_state.frame.locals[local_idx] = IntervalInt(0, 0)
                    successors.append(true_state)
                if can_be_nonzero:
                    if local_idx is not None:
                        if condition_val.low < 0 and condition_val.high > 0:
                            false_state.frame.locals[local_idx] = IntervalInt(
                                condition_val.low, condition_val.high, exclude_zero=True
                            )
                        elif condition_val.low == 0:
                            false_state.frame.locals[local_idx] = IntervalInt(1, condition_val.high)
                        elif condition_val.high == 0:
                            false_state.frame.locals[local_idx] = IntervalInt(condition_val.low, -1)
                        else:
                            false_state.frame.locals[local_idx] = condition_val
                    successors.append(false_state)
            elif opcode == "ifne":
                if can_be_nonzero:
                    # True branch
                    if local_idx is not None:
                        if condition_val.low < 0 and condition_val.high > 0:
                            true_state.frame.locals[local_idx] = IntervalInt(
                                condition_val.low, condition_val.high, exclude_zero=True
                            )
                        elif condition_val.low == 0:
                            true_state.frame.locals[local_idx] = IntervalInt(1, condition_val.high)
                        elif condition_val.high == 0:
                            true_state.frame.locals[local_idx] = IntervalInt(condition_val.low, -1)
                        else:
                            true_state.frame.locals[local_idx] = condition_val
                    successors.append(true_state)
                if can_be_zero:
                    if local_idx is not None:
                        false_state.frame.locals[local_idx] = IntervalInt(0, 0)
                    successors.append(false_state)
            else:
                successors.append(true_state)
                successors.append(false_state)
        else:
            # Sign domain
            if isinstance(condition_val, AbstractInt):
                can_be_zero = Sign.ZERO in condition_val.state_set
                can_be_nonzero = (Sign.POSITIVE in condition_val.state_set or 
                                 Sign.NEGATIVE in condition_val.state_set)
                
                if opcode == "ifeq":
                    if can_be_zero:
                        if local_idx is not None:
                            true_state.frame.locals[local_idx] = AbstractInt({Sign.ZERO})
                        successors.append(true_state)
                    if can_be_nonzero:
                        if local_idx is not None:
                            new_signs = condition_val.state_set - {Sign.ZERO}
                            false_state.frame.locals[local_idx] = AbstractInt(new_signs)
                        successors.append(false_state)
                elif opcode == "ifne":
                    if can_be_nonzero:
                        if local_idx is not None:
                            new_signs = condition_val.state_set - {Sign.ZERO}
                            true_state.frame.locals[local_idx] = AbstractInt(new_signs)
                        successors.append(true_state)
                    if can_be_zero:
                        if local_idx is not None:
                            false_state.frame.locals[local_idx] = AbstractInt({Sign.ZERO})
                        successors.append(false_state)
                else:
                    successors.append(true_state)
                    successors.append(false_state)
            else:
                successors.append(true_state)
                successors.append(false_state)
        
        return successors
    
    def _handle_if_icmp(self, state, instr):
        if len(state.frame.stack) < 2:
            return []
        target = int(instr[2])
        opcode = instr[1]
        
        val2 = state.frame.stack[-1]
        val1 = state.frame.stack[-2]
        
        successors = []
        
        # True branch
        true_state = state.copy()
        true_state.frame.stack.pop()
        true_state.frame.stack.pop()
        true_state.pc = target
        
        # False branch
        false_state = state.copy()
        false_state.frame.stack.pop()
        false_state.frame.stack.pop()
        false_state.pc = self._get_next_pc(instr[0])
        
        if self.use_interval and isinstance(val1, IntervalInt) and isinstance(val2, IntervalInt):
            local_idx = None
            for idx, local_val in state.frame.locals.items():
                if local_val == val1:
                    local_idx = idx
                    break
            
            is_comparing_with_zero = (val2.low == 0 and val2.high == 0)
            
            if local_idx is not None and is_comparing_with_zero:
                if opcode == "if_icmpeq":
                    can_be_equal = not (val1.high < 0 or val1.low > 0)
                    can_be_not_equal = not (val1.low == 0 and val1.high == 0)
                    
                    if can_be_equal:
                        # True branch
                        true_state.frame.locals[local_idx] = IntervalInt(0, 0)
                        successors.append(true_state)
                    
                    if can_be_not_equal:
                        # False branch
                        if val1.low < 0 and val1.high > 0:
                            false_state.frame.locals[local_idx] = IntervalInt(
                                val1.low, val1.high, exclude_zero=True
                            )
                        elif val1.low == 0:
                            false_state.frame.locals[local_idx] = IntervalInt(1, val1.high)
                        elif val1.high == 0:
                            false_state.frame.locals[local_idx] = IntervalInt(val1.low, -1)
                        else:
                            false_state.frame.locals[local_idx] = val1
                        successors.append(false_state)
                    
                elif opcode == "if_icmpne":
                    # True: val1 != 0, False: val1 == 0
                    can_be_not_equal = not (val1.low == 0 and val1.high == 0)
                    can_be_equal = not (val1.high < 0 or val1.low > 0)
                    
                    if can_be_not_equal:
                        if val1.low < 0 and val1.high > 0:
                            true_state.frame.locals[local_idx] = IntervalInt(
                                val1.low, val1.high, exclude_zero=True
                            )
                        elif val1.low == 0:
                            true_state.frame.locals[local_idx] = IntervalInt(1, val1.high)
                        elif val1.high == 0:
                            true_state.frame.locals[local_idx] = IntervalInt(val1.low, -1)
                        else:
                            true_state.frame.locals[local_idx] = val1
                        successors.append(true_state)
                    
                    if can_be_equal:
                        false_state.frame.locals[local_idx] = IntervalInt(0, 0)
                        successors.append(false_state)
                    
                else:
                    successors.append(true_state)
                    successors.append(false_state)
            else:
                can_be_equal = not (val1.high < val2.low or val1.low > val2.high)
                can_be_not_equal = not (val1.low == val1.high == val2.low == val2.high)
                
                if opcode == "if_icmpeq":
                    if can_be_equal:
                        successors.append(true_state)
                    if can_be_not_equal:
                        successors.append(false_state)
                elif opcode == "if_icmpne":
                    if can_be_not_equal:
                        successors.append(true_state)
                    if can_be_equal:
                        successors.append(false_state)
                else:
                    successors.append(true_state)
                    successors.append(false_state)
        else:
            # Sign domain
            if isinstance(val1, AbstractInt) and isinstance(val2, AbstractInt):
                #  local variable
                local_idx = None
                for idx, local_val in state.frame.locals.items():
                    if local_val == val1:
                        local_idx = idx
                        break
                
                is_comparing_with_zero = (val2.state_set == {Sign.ZERO})
                
                if local_idx is not None and is_comparing_with_zero:
                    can_be_zero = Sign.ZERO in val1.state_set
                    can_be_nonzero = (Sign.POSITIVE in val1.state_set or 
                                     Sign.NEGATIVE in val1.state_set)
                    
                    if opcode == "if_icmpeq":
                        # True: val1 == 0, False: val1 != 0
                        if can_be_zero:
                            # True branch
                            true_state.frame.locals[local_idx] = AbstractInt({Sign.ZERO})
                            successors.append(true_state)
                        if can_be_nonzero:
                            # False branch
                            new_signs = val1.state_set - {Sign.ZERO}
                            false_state.frame.locals[local_idx] = AbstractInt(new_signs)
                            successors.append(false_state)
                    elif opcode == "if_icmpne":
                        # True: val1 != 0, False: val1 == 0
                        if can_be_nonzero:
                            # True branch
                            new_signs = val1.state_set - {Sign.ZERO}
                            true_state.frame.locals[local_idx] = AbstractInt(new_signs)
                            successors.append(true_state)
                        if can_be_zero:
                            # False branch
                            false_state.frame.locals[local_idx] = AbstractInt({Sign.ZERO})
                            successors.append(false_state)
                    else:
                        successors.append(true_state)
                        successors.append(false_state)
                else:
                    successors.append(true_state)
                    successors.append(false_state)
            else:
                successors.append(true_state)
                successors.append(false_state)
        
        return successors
    
    def _handle_goto(self, state, instr):
        target = int(instr[2])
        new_state = state.copy()
        new_state.pc = target
        return [new_state]
    
    def _handle_getstatic(self, state, instr):
        new_state = state.copy()   
        new_state.frame.stack.append(self.create_top())        
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def _handle_putstatic(self, state, instr):
        new_state = state.copy()
        if new_state.frame.stack:
            new_state.frame.stack.pop()
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def _handle_athrow(self, state, instr):
        if not state.frame.stack:
            return []

        is_assertion_error = False
        for i in range(len(self.bytecodes) - 1, -1, -1):
            bc = self.bytecodes[i]
            if bc[0] >= state.pc:
                continue
            if bc[1] == "new" and len(bc) > 2:
                class_name = str(bc[2])
                if "AssertionError" in class_name:
                    is_assertion_error = True
                break
            if bc[1] == "new":
                break
        
        if is_assertion_error:
            self.errors.append(f"PC {state.pc}: Assertion error")
            self.path_results.append("assertion error")
        else:
            self.errors.append(f"PC {state.pc}: Exception thrown")
            self.path_results.append("error")
        
        return []
    
    def _handle_invokedynamic(self, state, instr):
        if len(instr) < 3:
            new_state = state.copy()
            new_state.pc = self._get_next_pc(instr[0])
            return [new_state]
        
        dynamic_info = instr[2]
        
        is_string_concat = False
        param_count = 0
        values = []
        
        if isinstance(dynamic_info, dict):
            method_name = dynamic_info.get("name", "")
            if "makeConcat" in method_name or "Concat" in str(method_name):
                is_string_concat = True
                parameters = dynamic_info.get("parameters", [])
                values = dynamic_info.get("values", [])
                param_count = len(parameters)
        
        elif isinstance(dynamic_info, str):
            if "makeConcat" in dynamic_info or "Concat" in dynamic_info:
                is_string_concat = True
                import re
                match = re.search(r'\((.*?)\)', dynamic_info)
                if match:
                    params_str = match.group(1)
                    param_count = params_str.count(';') if params_str else 0
                    values = [None] * param_count
        
        elif isinstance(dynamic_info, (tuple, list)) and len(dynamic_info) >= 2:
            method_name = str(dynamic_info[0])
            if "makeConcat" in method_name or "Concat" in method_name:
                is_string_concat = True
                param_count = len(dynamic_info[1]) if len(dynamic_info) > 1 else 0
                values = dynamic_info[2] if len(dynamic_info) > 2 else [None] * param_count
        
        if is_string_concat:
            new_state = state.copy()
            
            if len(new_state.frame.stack) < param_count:
                new_state.frame.stack.append(StringAbstraction.top())
                new_state.pc = self._get_next_pc(instr[0])
                return [new_state]
            
            stack_values = []
            for _ in range(param_count):
                stack_values.append(new_state.frame.stack.pop())
            stack_values.reverse() 
            
            result = StringAbstraction.from_string("")
            stack_idx = 0
            
            if values:
                for val in values:
                    if val is None:
                        if stack_idx < len(stack_values):
                            operand = stack_values[stack_idx]
                            result = self._concat_operand(result, operand)
                            stack_idx += 1
                    else:
                        const_str = StringAbstraction.from_string(str(val))
                        result = result.concat(const_str)
            else:
                for operand in stack_values:
                    result = self._concat_operand(result, operand)
            
            new_state.frame.stack.append(result)
            new_state.pc = self._get_next_pc(instr[0])
            return [new_state]
        
        new_state = state.copy()
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def _concat_operand(self, result, operand):
        if isinstance(operand, StringAbstraction):
            return result.concat(operand)
        elif isinstance(operand, (IntervalInt, AbstractInt)):
            return result.concat(StringAbstraction.top())
        else:
            return result.concat(StringAbstraction.top())
    
    def _handle_invokevirtual(self, state, instr):
        if len(instr) < 3:
            new_state = state.copy()
            new_state.pc = self._get_next_pc(instr[0])
            return [new_state]
        
        method_info = instr[2]
        method_desc = str(method_info).lower()

        if not state.frame.stack:
            return []
        
        # String.length()
        elif "length" in method_desc and "string" in method_desc:
            return self._handle_string_length(state, instr)
        
        # String.charAt()
        elif "charat" in method_desc:
            return self._handle_string_charat(state, instr)
        
        # String.substring
        elif "substring" in method_desc:
            return self._handle_string_substring(state, instr)
        
        # String.startsWith
        elif "startswith" in method_desc:
            return self._handle_string_startswith(state, instr)
        
        # String.equals
        elif "equals" in method_desc:
            return self._handle_string_equals(state, instr)
        
        # String.concat
        elif "concat" in method_desc:
            return self._handle_string_concat(state, instr)
        
        # String.contains
        elif "contains" in method_desc:
            return self._handle_string_contains(state, instr)
        
        # Integer.parseInt
        elif "parseint" in method_desc:
            return self._handle_integer_parseint(state, instr)
        
        # String.compareTo
        elif "compareto" in method_desc:
            return self._handle_string_compareto(state, instr)
        
        # String.split
        elif "split" in method_desc:
            return self._handle_string_split(state, instr)
        
        # String.toLowerCase / toUpperCase
        elif "tolowercase" in method_desc or "touppercase" in method_desc:
            return self._handle_string_case_conversion(state, instr)
        
        # String.replace
        elif "replace" in method_desc:
            return self._handle_string_replace(state, instr)
        
        # String.trim
        elif "trim" in method_desc:
            return self._handle_string_trim(state, instr)
        
        else:
            new_state = state.copy()
            if new_state.frame.stack:
                new_state.frame.stack.pop() 
            for _ in range(min(2, len(new_state.frame.stack))):
                new_state.frame.stack.pop()
            new_state.pc = self._get_next_pc(instr[0])
            return [new_state]
    
    def _handle_string_length(self, state, instr):
        if not state.frame.stack:
            return []
        
        new_state = state.copy()
        string_val = new_state.frame.stack.pop()
        
        if isinstance(string_val, StringAbstraction):
            min_len, max_len = string_val.length()
            if self.use_interval:
                length_val = IntervalInt(min_len, max_len)
            else:
                if min_len == max_len == 0:
                    length_val = AbstractInt({Sign.ZERO})
                elif min_len > 0:
                    length_val = AbstractInt({Sign.POSITIVE})
                elif max_len == 0:
                    length_val = AbstractInt({Sign.ZERO})
                else:
                    length_val = AbstractInt({Sign.ZERO, Sign.POSITIVE})
        else:
            length_val = self.create_top()
        
        new_state.frame.stack.append(length_val)
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def _handle_string_charat(self, state, instr):
        if len(state.frame.stack) < 2:
            return []
        
        new_state = state.copy()
        index_val = new_state.frame.stack.pop()
        string_val = new_state.frame.stack.pop()
        
        # Check for potential index out of bounds
        if isinstance(string_val, StringAbstraction) and isinstance(index_val, IntervalInt):
            min_len, max_len = string_val.length()
            
            # Check if index could be negative
            if index_val.low < 0:
                self.errors.append(f"PC {state.pc}: Possible index out of bounds (negative index)")
                self.path_results.append("index out of bounds")
                return []
            
            if index_val.low >= max_len:
                self.errors.append(f"PC {state.pc}: Possible index out of bounds (index >= length)")
                self.path_results.append("index out of bounds")
                return []
            
            if index_val.high >= max_len or (min_len == 0 and index_val.high >= 0):
                self.errors.append(f"PC {state.pc}: Possible index out of bounds")
                self.path_results.append("index out of bounds")
                return []
        
        if self.use_interval:
            new_state.frame.stack.append(IntervalInt(0, 65535))  # char range
        else:
            new_state.frame.stack.append(AbstractInt({Sign.ZERO, Sign.POSITIVE}))
        
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def _handle_string_substring(self, state, instr):
        if len(state.frame.stack) < 2:
            return []
        
        new_state = state.copy()
        
        method_desc = str(instr[2]) if len(instr) > 2 else ""
        
        if "(II)" in method_desc:  # substring(int, int)
            if len(new_state.frame.stack) < 3:
                return []
            end_val = new_state.frame.stack.pop()
            start_val = new_state.frame.stack.pop()
            string_val = new_state.frame.stack.pop()
            
            # Check for index errors
            if isinstance(string_val, StringAbstraction):
                min_len, max_len = string_val.length()
                
                if isinstance(start_val, IntervalInt):
                    if start_val.low < 0:
                        self.errors.append(f"PC {state.pc}: Possible index out of bounds (negative start)")
                        self.path_results.append("index out of bounds")
                        return []
                    
                    if start_val.low > max_len:
                        self.errors.append(f"PC {state.pc}: Possible index out of bounds (start > length)")
                        self.path_results.append("index out of bounds")
                        return []
                
                if isinstance(end_val, IntervalInt):
                    if end_val.low < 0:
                        self.errors.append(f"PC {state.pc}: Possible index out of bounds (negative end)")
                        self.path_results.append("index out of bounds")
                        return []
                    
                    if end_val.low > max_len:
                        self.errors.append(f"PC {state.pc}: Possible index out of bounds (end > length)")
                        self.path_results.append("index out of bounds")
                        return []
                
                # Check if start > end
                if isinstance(start_val, IntervalInt) and isinstance(end_val, IntervalInt):
                    if start_val.low > end_val.high:
                        self.errors.append(f"PC {state.pc}: Possible index range exception (start > end)")
                        self.path_results.append("index range exception")
                        return []
            
            if isinstance(start_val, IntervalInt) and isinstance(end_val, IntervalInt):
                start = start_val.low
                end = end_val.low
            else:
                start, end = 0, None
                
            if isinstance(string_val, StringAbstraction):
                result = string_val.substring(start, end)
            else:
                result = StringAbstraction.top()
                
        else:  # substring(int)
            start_val = new_state.frame.stack.pop()
            string_val = new_state.frame.stack.pop()
            
            # Check for index errors
            if isinstance(string_val, StringAbstraction):
                min_len, max_len = string_val.length()
                
                if isinstance(start_val, IntervalInt):
                    if start_val.low < 0:
                        self.errors.append(f"PC {state.pc}: Possible index out of bounds (negative start)")
                        self.path_results.append("index out of bounds")
                        return []
                    
                    if start_val.low > max_len:
                        self.errors.append(f"PC {state.pc}: Possible index out of bounds (start > length)")
                        self.path_results.append("index out of bounds")
                        return []
            
            if isinstance(start_val, IntervalInt):
                start = start_val.low
            else:
                start = 0
                
            if isinstance(string_val, StringAbstraction):
                result = string_val.substring(start)
            else:
                result = StringAbstraction.top()
        
        new_state.frame.stack.append(result)
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def _handle_string_startswith(self, state, instr):
        if len(state.frame.stack) < 2:
            return []
        
        new_state = state.copy()
        prefix_val = new_state.frame.stack.pop()
        string_val = new_state.frame.stack.pop()
        
        result_bool = None
        if isinstance(string_val, StringAbstraction) and isinstance(prefix_val, StringAbstraction):
            if len(prefix_val.prefixes) == 1 and prefix_val.min_len == prefix_val.max_len:
                prefix_str = list(prefix_val.prefixes)[0]
                result_bool = string_val.startsWith(prefix_str)
        
        if result_bool is True:
            bool_val = self.create_abstract_value(1)
        elif result_bool is False:
            bool_val = self.create_abstract_value(0)
        else:
            if self.use_interval:
                bool_val = IntervalInt(0, 1)
            else:
                bool_val = AbstractInt({Sign.ZERO, Sign.POSITIVE})
        
        new_state.frame.stack.append(bool_val)
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def _handle_string_equals(self, state, instr):
        if len(state.frame.stack) < 2:
            return []
        
        new_state = state.copy()
        other_val = new_state.frame.stack.pop()
        string_val = new_state.frame.stack.pop()
        
        result_bool = None
        if isinstance(string_val, StringAbstraction) and isinstance(other_val, StringAbstraction):
            result_bool = string_val.equals(other_val)
        
        if result_bool is True:
            bool_val = self.create_abstract_value(1)
        elif result_bool is False:
            bool_val = self.create_abstract_value(0)
        else:
            if self.use_interval:
                bool_val = IntervalInt(0, 1)
            else:
                bool_val = AbstractInt({Sign.ZERO, Sign.POSITIVE})
        
        new_state.frame.stack.append(bool_val)
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def _handle_string_concat(self, state, instr):
        if len(state.frame.stack) < 2:
            return []
        
        new_state = state.copy()
        other_val = new_state.frame.stack.pop()
        string_val = new_state.frame.stack.pop()
        
        if isinstance(string_val, StringAbstraction) and isinstance(other_val, StringAbstraction):
            result = string_val.concat(other_val)
        else:
            result = StringAbstraction.top()
        
        new_state.frame.stack.append(result)
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def _handle_string_contains(self, state, instr):
        """Handle String.contains(CharSequence)"""
        if len(state.frame.stack) < 2:
            return []
        
        new_state = state.copy()
        search_val = new_state.frame.stack.pop()
        string_val = new_state.frame.stack.pop()
        
        # Return unknown boolean (could be true or false)
        if self.use_interval:
            bool_val = IntervalInt(0, 1)
        else:
            bool_val = AbstractInt({Sign.ZERO, Sign.POSITIVE})
        
        new_state.frame.stack.append(bool_val)
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def _handle_integer_parseint(self, state, instr):
        """Handle Integer.parseInt(String) - can throw NumberFormatException"""
        if not state.frame.stack:
            return []
        
        new_state = state.copy()
        string_val = new_state.frame.stack.pop()
        
        # Check if string could be empty or non-numeric
        if isinstance(string_val, StringAbstraction):
            min_len, max_len = string_val.length()
            
            # If string could be empty or TOP (unknown content)
            if min_len == 0 or string_val.is_top():
                self.errors.append(f"PC {state.pc}: Possible number format exception")
                self.path_results.append("number format exception")
                return []
        
        # If parsing succeeds, push an integer
        new_state.frame.stack.append(self.create_top())
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def _handle_string_compareto(self, state, instr):
        """Handle String.compareTo(String)"""
        if len(state.frame.stack) < 2:
            return []
        
        new_state = state.copy()
        other_val = new_state.frame.stack.pop()
        string_val = new_state.frame.stack.pop()
        
        # Returns an integer (negative, zero, or positive)
        if self.use_interval:
            result_val = IntervalInt.top()
        else:
            result_val = AbstractInt({Sign.NEGATIVE, Sign.ZERO, Sign.POSITIVE})
        
        new_state.frame.stack.append(result_val)
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def _handle_string_split(self, state, instr):
        """Handle String.split(String) - returns String[]"""
        if len(state.frame.stack) < 2:
            return []
        
        new_state = state.copy()
        regex_val = new_state.frame.stack.pop()
        string_val = new_state.frame.stack.pop()
        
        # Push an array reference (represented as TOP for now)
        new_state.frame.stack.append(self.create_string_top())
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def _handle_string_case_conversion(self, state, instr):
        """Handle String.toLowerCase() and String.toUpperCase()"""
        if not state.frame.stack:
            return []
        
        new_state = state.copy()
        string_val = new_state.frame.stack.pop()
        
        # Case conversion preserves length
        if isinstance(string_val, StringAbstraction):
            new_state.frame.stack.append(string_val)
        else:
            new_state.frame.stack.append(StringAbstraction.top())
        
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def _handle_string_replace(self, state, instr):
        """Handle String.replace(CharSequence, CharSequence)"""
        if len(state.frame.stack) < 3:
            return []
        
        new_state = state.copy()
        replacement_val = new_state.frame.stack.pop()
        target_val = new_state.frame.stack.pop()
        string_val = new_state.frame.stack.pop()
        
        # Result is a string (unknown length and content)
        new_state.frame.stack.append(StringAbstraction.top())
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def _handle_string_trim(self, state, instr):
        """Handle String.trim()"""
        if not state.frame.stack:
            return []
        
        new_state = state.copy()
        string_val = new_state.frame.stack.pop()
        
        # Trim can reduce length but maintains type
        if isinstance(string_val, StringAbstraction):
            min_len, max_len = string_val.length()
            # After trim, min_len could be 0
            result = StringAbstraction.top()
        else:
            result = StringAbstraction.top()
        
        new_state.frame.stack.append(result)
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def _handle_invokespecial(self, state, instr):
        new_state = state.copy()
        args_str = str(instr[2:]) if len(instr) > 2 else ""

        if "AssertionError" in args_str and "<init>" in args_str:
            if len(new_state.frame.stack) > 0: 
                new_state.frame.stack.pop()
        else:
            if len(new_state.frame.stack) > 0: 
                new_state.frame.stack.pop()
        
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
    def get_result_string(self):
        if self.errors:
            error_types = set()
            
            for err in self.errors:
                err_lower = err.lower()
                if "assertion" in err_lower:
                    error_types.add("assertion error")
                elif "division by zero" in err_lower or "divide by zero" in err_lower:
                    error_types.add("divide by zero")
                else:
                    error_types.add("error")
            
            if len(error_types) == 0:
                return "error"
            elif len(error_types) == 1:
                return error_types.pop()
            else:
                priority = {"assertion error": 1, "divide by zero": 2, "error": 3}
                sorted_errors = sorted(error_types, key=lambda x: priority.get(x, 99))
                return " and ".join(sorted_errors)
            
        else:
            return "ok"
        
        
    
    def print_analysis_result(self):
        # Print basic stats inline
        print(f"  Constants: {sorted(self.constants)}")
        print(f"  Loop heads: {sorted(self.loop_heads) if self.loop_heads else 'None'}")
        print(f"  Iterations: {self.iteration_count}, Joins: {self.join_count}, Widenings: {self.widen_count}")
        
        # Print errors or success
        if self.path_results:
            path_counter = Counter(self.path_results)
            print(f"  Total paths: {len(self.path_results)}")
            for result, count in sorted(path_counter.items()):
                percentage = (count / len(self.path_results)) * 100
                print(f"    - {result}: {count} ({percentage:.1f}%)") 

        if self.errors:
            print(f"  ⚠ Found {len(self.errors)} potential error(s):")
            for err in self.errors:
                print(f"    • {err}")
        else:
            print(f"  ✓ No errors detected")

    def get_error_probabilities(self):
        error_counts = {
            "ok": 0,
            "divide by zero": 0,
            "assertion error": 0,
            "out of bounds": 0,
            "null pointer": 0,
            "*": 0
        }

        for result in self.path_results:
            if result in error_counts:
                error_counts[result] += 1
            elif "assertion" in result.lower():
                error_counts["assertion error"] += 1
            elif "divide" in result.lower():
                error_counts["divide by zero"] += 1
            else:
                error_counts["*"] += 1

        if len(self.path_results) == 0:
            if len(self.errors) == 0:
                error_counts["ok"] = 1
            else:
                for err in self.errors:
                    err_lower = err.lower()
                    if "assertion" in err_lower:
                        error_counts["assertion error"] += 1
                    elif "division by zero" in err_lower or "divide by zero" in err_lower:
                        error_counts["divide by zero"] += 1

        total = sum(error_counts.values())

        probabilities = {}
        if total > 0:
            for error_type, count in error_counts.items():
                percentage = int((count / total) * 100)
                probabilities[error_type] = f"{percentage}%"
        else:
            probabilities = {
                "ok": "100%",
                "divide by zero": "0%",
                "assertion error": "0%",
                "out of bounds": "0%",
                "null pointer": "0%",
                "*": "0%"
            }

        return probabilities
        

    def get_string_analysis_summary(self):
        if self.errors:
            error_types = set()
            
            for err in self.errors:
                err_lower = err.lower()
                
                if "assertion" in err_lower:
                    error_types.add("assertion error")
                elif "null" in err_lower or "pointer" in err_lower:
                    error_types.add("null pointer exception")
                elif "index out of bounds" in err_lower or "out of bounds" in err_lower:
                    error_types.add("index out of bounds")
                elif "index range" in err_lower:
                    error_types.add("index range exception")
                elif "number format" in err_lower or "parse" in err_lower:
                    error_types.add("number format exception")
                elif "division by zero" in err_lower or "divide by zero" in err_lower:
                    error_types.add("divide by zero")
                else:
                    error_types.add("error")
            
            if len(error_types) == 0:
                return "error"
            elif len(error_types) == 1:
                return error_types.pop()
            else:
                priority = {
                    "null pointer exception": 1,
                    "assertion error": 2,
                    "index out of bounds": 3,
                    "index range exception": 4,
                    "number format exception": 5,
                    "divide by zero": 6,
                    "error": 99
                }
                sorted_errors = sorted(error_types, key=lambda x: priority.get(x, 99))
                return " and ".join(sorted_errors)
        else:
            return "ok"
        
    
    def print_string_analysis_summary(self):
        print(f"\n  [String Analysis Summary]")
        
        string_vars = {}
        for pc, state in self.state_set.per_inst.items():
            for idx, val in state.frame.locals.items():
                if isinstance(val, StringAbstraction):
                    if idx not in string_vars:
                        string_vars[idx] = []
                    string_vars[idx].append((pc, val))
        
        if string_vars:
            print(f"  String variables tracked: {len(string_vars)}")
            for idx, states in string_vars.items():
                print(f"    Variable {idx}:")
                for pc, val in states[:3]:
                    print(f"      PC {pc}: {val}")
                if len(states) > 3:
                    print(f"      ... and {len(states) - 3} more states")
        else:
            print(f"  No string variables tracked")

    def get_final_string_states(self):
        final_strings = {}
        
        all_pcs = set(self.state_set.per_inst.keys())
        has_successor = set()
        
        for bc in self.bytecodes:
            pc = bc[0]
            opcode = bc[1]
            
            if opcode in ["goto", "if_icmpeq", "if_icmpne", "if_icmplt", 
                          "if_icmpge", "if_icmpgt", "if_icmple",
                          "ifeq", "ifne", "iflt", "ifge", "ifgt", "ifle"]:
                if len(bc) > 2:
                    has_successor.add(pc)
            elif opcode not in ["ireturn", "return", "athrow"]:
                has_successor.add(pc)
        
        final_pcs = all_pcs - has_successor
        
        for pc in final_pcs:
            if pc in self.state_set.per_inst:
                state = self.state_set.per_inst[pc]
                for idx, val in state.frame.locals.items():
                    if isinstance(val, StringAbstraction):
                        if idx not in final_strings:
                            final_strings[idx] = []
                        final_strings[idx].append(val)
        
        return final_strings
    
    def get_predicted_errors(self):
        error_set = set()
        if not self.path_results and not self.errors:
            return error_set

        errors_to_check = self.path_results if self.path_results else [err.lower() for err in self.errors]
        
        for err in errors_to_check:
            err_lower = str(err).lower()
            if "null pointer" in err_lower:
                continue
            elif "divide by zero" in err_lower or "divide" in err_lower:
                error_set.add("DIV_ZERO")
            elif "assertion" in err_lower:
                error_set.add("ASSERT")
            elif "out of bounds" in err_lower or "range exception" in err_lower:
                error_set.add("BOUNDS")
            elif "number format" in err_lower:
                error_set.add("NFE")
            elif err_lower not in ["ok", "*", "error"]:
                error_set.add(err)

        return error_set