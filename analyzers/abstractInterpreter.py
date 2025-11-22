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
            else:
                new_locals[idx] = val1.join(val2)
        
        new_stack = []
        for v1, v2 in zip(self.frame.stack, other.frame.stack):
            if isinstance(v1, IntervalInt) and isinstance(v2, IntervalInt):
                new_stack.append(v1.widen(v2, constants))
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
    def __init__(self, bytecodes_tuple, use_interval=False, use_widening=True):
        modifiers, instructions_list = bytecodes_tuple
        self.bytecodes = instructions_list
        self.use_interval = use_interval
        self.use_widening = use_widening
        
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
    
    def create_top(self):
        if self.use_interval:
            return IntervalInt.top()
        else:
            return AbstractInt.top()
    
    def analyze(self, num_parameters: int, max_iterations=1000):
        initial_locals = {}
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
        elif opcode == "new":
            return self._handle_new(state, instruction)
        elif opcode == "getstatic":
            return self._handle_getstatic(state, instruction)
        elif opcode == "putstatic":
            return self._handle_putstatic(state, instruction)
        elif opcode == "athrow": 
            return self._handle_athrow(state, instruction)
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
    
    def _handle_new(self, state, instr):
        new_state = state.copy()
        new_state.frame.stack.append(self.create_top()) 
        new_state.pc = self._get_next_pc(instr[0])
        return [new_state]
    
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
        



if __name__ == '__main__':
    print("Start prove abstract operation correctly")
    test_values = [-2,-1,0,1,2]

    total_case_num = 0
    true_case_num = 0
    for v1 in test_values:
        for v2 in test_values:
            a1 = AbstractInt(v1)
            a2 = AbstractInt(v2)

            r_l = AbstractInt(v1 + v2)
            r_r = a1 + a2
            r = r_l <= r_r
            total_case_num+=1
            true_case_num+=int(r)
            print("[{}] α({} + {}) <= α({}) + α({}): {} <= {}".format(r, v1, v2, v1, v2, r_l, r_r))

            r_l = AbstractInt(v1 - v2)
            r_r = a1 - a2
            r = r_l <= r_r
            total_case_num += 1
            true_case_num += int(r)
            print("[{}] α({} - {}) <= α({}) - α({}): {} <= {}".format(r, v1, v2, v1, v2, r_l, r_r))

            r_l = AbstractInt(v1 * v2)
            r_r = a1 * a2
            r = r_l <= r_r
            total_case_num += 1
            true_case_num += int(r)
            print("[{}] α({} * {}) <= α({}) * α({}): {} <= {}".format(r, v1, v2, v1, v2, r_l, r_r))

            try:
                r_r = a1 / a2
            except ZeroDivisionError as e:
                r = v2 == 0
                total_case_num += 1
                true_case_num += int(r)
                print("[{}] α({}) / α({}): {}".format(r, v1, v2, e))
            else:
                r_l = AbstractInt(v1 / v2)
                r = r_l <= r_r
                total_case_num += 1
                true_case_num += int(r)
                print("[{}] α({} / {}) <= α({}) / α({}): {} <= {}".format(r, v1, v2, v1, v2, r_l, r_r))

    prove_print = "[Accuracy]: {:.2f}% ({}/{})".format(true_case_num / total_case_num * 10 ** 2, true_case_num,total_case_num)
    print("-"*len(prove_print))
    print(prove_print)
    print("-"*len(prove_print))
    
    print("Start prove abstract operation correctly (IntervalInt)")
    test_values = [-2, -1, 0, 1, 2]

    total_case_num = 0
    true_case_num = 0
    for v1 in test_values:
        for v2 in test_values:
            a1 = IntervalInt.from_concrete(v1)
            a2 = IntervalInt.from_concrete(v2)

            r_l = IntervalInt.from_concrete(v1 + v2)
            r_r = a1 + a2
            r = r_l <= r_r  
            total_case_num += 1
            true_case_num += int(r)
            print("[{}] α({} + {}) <= α({}) + α({}): {} <= {}".format(r, v1, v2, v1, v2, r_l, r_r))


            r_l = IntervalInt.from_concrete(v1 - v2)
            # α(v1) - α(v2)
            r_r = a1 - a2
            r = r_l <= r_r
            total_case_num += 1
            true_case_num += int(r)
            print("[{}] α({} - {}) <= α({}) - α({}): {} <= {}".format(r, v1, v2, v1, v2, r_l, r_r))


            r_l = IntervalInt.from_concrete(v1 * v2)
            # α(v1) * α(v2)
            r_r = a1 * a2
            r = r_l <= r_r
            total_case_num += 1
            true_case_num += int(r)
            print("[{}] α({} * {}) <= α({}) * α({}): {} <= {}".format(r, v1, v2, v1, v2, r_l, r_r))


            try:
                r_r = a1 / a2
            except ZeroDivisionError as e:
                r = (v2 == 0)
                total_case_num += 1
                true_case_num += int(r)
                print("[{}] α({}) / α({}): {} (Correctly caught concrete 0)".format(r, v1, v2, e))
            else:
                concrete_div_result = int(v1 / v2)
                
                # α(v1 / v2)
                r_l = IntervalInt.from_concrete(concrete_div_result)
                r = r_l <= r_r
                total_case_num += 1
                true_case_num += int(r)
                print("[{}] α({} / {}) <= α({}) / α({}): {} <= {}".format(r, v1, v2, v1, v2, r_l, r_r))

    prove_print = "[Accuracy]: {:.2f}% ({}/{})".format(true_case_num / total_case_num * 100.0, true_case_num, total_case_num)
    print("-" * len(prove_print))
    print(prove_print)
    print("-" * len(prove_print))
    