from enum import Enum
from typing import Dict, List, Set, Tuple, Optional, Union

class Sign(Enum):
    POSITIVE = "+"
    NEGATIVE = "-"
    ZERO = "0"
    
    def __neg__(self):
        match self:
            case Sign.POSITIVE:
                return Sign.NEGATIVE
            case Sign.NEGATIVE:
                return Sign.POSITIVE
            case Sign.ZERO:
                return Sign.ZERO
    
    def __add__(self, other):
        signs = {self, other}
        if len(signs) == 1:
            return signs
        elif Sign.ZERO in signs:
            signs.remove(Sign.ZERO)
            return signs
        else:
            return {Sign.NEGATIVE, Sign.ZERO, Sign.POSITIVE}
    
    def __sub__(self, other):
        if self == Sign.ZERO:
            return {-other}
        elif other == Sign.ZERO:
            return {self}
        elif self == other:
            return {Sign.NEGATIVE, Sign.ZERO, Sign.POSITIVE}
        else:
            return {self}
    
    def __mul__(self, other):
        signs = {self, other}
        if Sign.ZERO in signs:
            return {Sign.ZERO}
        elif len(signs) == 1:
            return {Sign.POSITIVE}
        else:
            return {Sign.NEGATIVE}
    
    def __truediv__(self, other):
        if other == Sign.ZERO:
            raise ZeroDivisionError("Abstract division by zero")
        elif self == Sign.ZERO:
            return {Sign.ZERO}
        elif self == other:
            return {Sign.POSITIVE}
        else:
            return {Sign.NEGATIVE}


class AbstractInt(object):
    def __init__(self, value=None):
        self.state_set = set()
        if value is not None:
            if isinstance(value, int):
                if value < 0:
                    self.state_set.add(Sign.NEGATIVE)
                elif value > 0:
                    self.state_set.add(Sign.POSITIVE)
                else:
                    self.state_set.add(Sign.ZERO)
            elif isinstance(value, set):
                self.state_set = value.copy()
    
    def top():
        result = AbstractInt()
        result.state_set = {Sign.POSITIVE, Sign.NEGATIVE, Sign.ZERO}
        return result
    
    def bottom():
        return AbstractInt()
    
    def is_bottom(self):
        return len(self.state_set) == 0
    
    def is_top(self):
        return self.state_set == {Sign.POSITIVE, Sign.NEGATIVE, Sign.ZERO}
    
    def join(self, other):
        result = AbstractInt()
        result.state_set = self.state_set | other.state_set
        return result
    
    def meet(self, other):
        result = AbstractInt()
        result.state_set = self.state_set & other.state_set
        return result
    
    def __add__(self, other):
        result = AbstractInt()
        for s_state in self.state_set:
            for o_state in other.state_set:
                result.state_set.update(s_state + o_state)
        return result
    
    def __sub__(self, other):
        result = AbstractInt()
        for s_state in self.state_set:
            for o_state in other.state_set:
                result.state_set.update(s_state - o_state)
        return result
    
    def __mul__(self, other):
        result = AbstractInt()
        for s_state in self.state_set:
            for o_state in other.state_set:
                result.state_set.update(s_state * o_state)
        return result
    
    def __truediv__(self, other):
        if Sign.ZERO in other.state_set:
            raise ZeroDivisionError("Abstract division by zero")
        result = AbstractInt()
        for s_state in self.state_set:
            for o_state in other.state_set:
                result.state_set.update(s_state / o_state)
        return result
    
    def __neg__(self):
        result = AbstractInt()
        for s_state in self.state_set:
            result.state_set.add(-s_state)
        return result
    
    def __lt__(self, other):
        return self.state_set < other.state_set

    def __gt__(self, other):
        return self.state_set > other.state_set

    def __eq__(self, other):
        return self.state_set == other.state_set

    def __ne__(self, other):
        return self.state_set != other.state_set

    def __le__(self, other):
        return self.state_set <= other.state_set

    def __ge__(self, other):
        return self.state_set >= other.state_set
    
    def __hash__(self):
        return hash(frozenset(self.state_set))
    
    def __copy__(self):
        copy = AbstractInt()
        copy.state_set = self.state_set.copy()
        return copy
    
    def __str__(self):
        if self.is_bottom():
            return "EMPTY"  
        return "{" + ",".join(sorted([s.value for s in self.state_set])) + "}"
    
    def __repr__(self):
        return self.__str__()



class IntervalInt(object):
    def __init__(self, low, high, exclude_zero=False):
        # Validate interval
        if low == float('inf') or high == float('-inf'):
            self.low = float('inf')
            self.high = float('-inf')
            self.exclude_zero = False
        elif low > high:
            self.low = float('inf')
            self.high = float('-inf')
            self.exclude_zero = False
        else:
            self.low = low
            self.high = high
            self.exclude_zero = exclude_zero if (low <= 0 <= high) else False
    
    
    def from_concrete(value):
        return IntervalInt(value, value, exclude_zero=False)
    
    def top():
        return IntervalInt(float('-inf'), float('inf'), exclude_zero=False)
    
    def bottom():
        return IntervalInt(float('inf'), float('-inf'), exclude_zero=False)
    
    def is_bottom(self):
        return self.low == float('inf') and self.high == float('-inf')
    
    def is_top(self):
        return self.low == float('-inf') and self.high == float('inf')
    
    def contains(self, value):
        if self.is_bottom():
            return False
        in_range = self.low <= value <= self.high
        if in_range and value == 0 and self.exclude_zero:
            return False
        return in_range
    
    def definitely_not_zero(self):
        if self.low > 0 or self.high < 0:
            return True
        if self.exclude_zero and self.low <= 0 <= self.high:
            return True
        return False
    
    def join(self, other):
        if self.is_bottom():
            return other
        if other.is_bottom():
            return self
        
        new_low = min(self.low, other.low)
        new_high = max(self.high, other.high)
        new_exclude_zero = self.exclude_zero and other.exclude_zero
        return IntervalInt(new_low, new_high, exclude_zero=new_exclude_zero)
    
    def meet(self, other):
        if self.is_bottom() or other.is_bottom():
            return IntervalInt.bottom()
        
        new_low = max(self.low, other.low)
        new_high = min(self.high, other.high)
        
        if new_low > new_high:
            return IntervalInt.bottom()
        
        new_exclude_zero = self.exclude_zero or other.exclude_zero
        return IntervalInt(new_low, new_high, exclude_zero=new_exclude_zero)
    
    def widen(self, other, constants):
        if self.is_bottom():
            return other
        if other.is_bottom():
            return self
        
        sorted_constants = sorted(constants | {int(self.low), int(self.high)} 
                                 if not (isinstance(self.low, float) or isinstance(self.high, float))
                                 else constants)
        
        if other.low < self.low:
            # Lower bound decreased, jump to previous constant or -inf
            new_low = float('-inf')
            for c in reversed(sorted_constants):
                if c <= other.low:
                    new_low = c
                    break
        else:
            new_low = self.low
        
        if other.high > self.high:
            # Upper bound increased, jump to next constant or +inf
            new_high = float('inf')
            for c in sorted_constants:
                if c >= other.high:
                    new_high = c
                    break
        else:
            new_high = self.high
        
        return IntervalInt(new_low, new_high, exclude_zero=False)
    
    def __add__(self, other):
        if self.is_bottom() or other.is_bottom():
            return IntervalInt.bottom()
        return IntervalInt(self.low + other.low, self.high + other.high)
    
    def __sub__(self, other):
        if self.is_bottom() or other.is_bottom():
            return IntervalInt.bottom()
        return IntervalInt(self.low - other.high, self.high - other.low)
    
    def __mul__(self, other):
        if self.is_bottom() or other.is_bottom():
            return IntervalInt.bottom()
        
        products = [
            self.low * other.low,
            self.low * other.high,
            self.high * other.low,
            self.high * other.high
        ]
        return IntervalInt(min(products), max(products))
    
    def __truediv__(self, other):
        if self.is_bottom() or other.is_bottom():
            return IntervalInt.bottom()
        
        if other.low <= 0 <= other.high and not other.exclude_zero:
            raise ZeroDivisionError("Abstract division by zero")
        
        if other.exclude_zero and other.low <= 0 <= other.high:
            return IntervalInt.top()
        
        quotients = [
            self.low / other.low,
            self.low / other.high,
            self.high / other.low,
            self.high / other.high
        ]
        return IntervalInt(int(min(quotients)), int(max(quotients)))
    
    def __neg__(self):
        if self.is_bottom():
            return IntervalInt.bottom()
        return IntervalInt(-self.high, -self.low)
    
    def __le__(self, other):
        if self.is_bottom():
            return True
        if other.is_bottom():
            return False
        return other.low <= self.low and self.high <= other.high
    
    def __lt__(self, other):
        return self <= other and self != other
    
    def __ge__(self, other):
        return other <= self
    
    def __gt__(self, other):
        return other < self
    
    def __eq__(self, other):
        if not isinstance(other, IntervalInt):
            return False
        return self.low == other.low and self.high == other.high
    
    def __hash__(self):
        return hash((self.low, self.high))
    
    def __str__(self):
        if self.is_bottom():
            return "EMPTY"
        
        low_str = "-inf" if self.low == float('-inf') else str(int(self.low) if isinstance(self.low, float) else self.low)
        high_str = "+inf" if self.high == float('inf') else str(int(self.high) if isinstance(self.high, float) else self.high)
        
        result = f"[{low_str},{high_str}]"
        if self.exclude_zero:
            result += "\\{0}"
        return result
    
    def __repr__(self):
        return self.__str__()



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
                    # True branch
                    if local_idx is not None:
                        true_state.frame.locals[local_idx] = IntervalInt(0, 0)
                    successors.append(true_state)
                if can_be_nonzero:
                    # False branch
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
                    # False branch
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
                        # True branch
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
                        # True branch
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
                    # True: val1 == 0, False: val1 != 0
                    can_be_equal = not (val1.high < 0 or val1.low > 0)
                    can_be_not_equal = not (val1.low == 0 and val1.high == 0)
                    
                    if can_be_equal:
                        true_state.frame.locals[local_idx] = IntervalInt(0, 0)
                        successors.append(true_state)
                    
                    if can_be_not_equal:
                        if val1.low < 0 and val1.high > 0:
                             false_state.frame.locals[local_idx] = IntervalInt(
                                val1.low, val1.high, exclude_zero=True
                            )
                        elif val1.low == 0:
                            false_state.frame.locals[local_idx] = IntervalInt(max(1, val1.low), val1.high)
                        elif val1.high == 0:
                            false_state.frame.locals[local_idx] = IntervalInt(val1.low, min(-1, val1.high))
                        else:
                            false_state.frame.locals[local_idx] = val1
                        successors.append(false_state)
                    
                elif opcode == "if_icmpne":
                    # True: val1 != 0, False: val1 == 0
                    can_be_not_equal = not (val1.low == 0 and val1.high == 0)
                    can_be_equal = not (val1.high < 0 or val1.low > 0)
                    
                    if can_be_not_equal:
                        # True branch: val1 != 0
                        if val1.low < 0 and val1.high > 0:
                            true_state.frame.locals[local_idx] = IntervalInt(
                                val1.low, val1.high, exclude_zero=True
                            )
                        elif val1.low == 0:
                            true_state.frame.locals[local_idx] = IntervalInt(max(1, val1.low), val1.high)
                        elif val1.high == 0:
                            true_state.frame.locals[local_idx] = IntervalInt(val1.low, min(-1, val1.high))
                        else:
                            true_state.frame.locals[local_idx] = val1
                        successors.append(true_state)
                    
                    if can_be_equal:
                        # False branch: val1 == 0
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
        else:
            self.errors.append(f"PC {state.pc}: Exception thrown")
        
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
        print(f"  Constants: {sorted(self.constants)}")
        print(f"  Loop heads: {sorted(self.loop_heads) if self.loop_heads else 'None'}")
        print(f"  Iterations: {self.iteration_count}, Joins: {self.join_count}, Widenings: {self.widen_count}")
        
        if self.errors:
            print(f"  ⚠ Found {len(self.errors)} potential error(s):")
            for err in self.errors:
                print(f"    • {err}")
        else:
            print(f"  ✓ No errors detected")
        



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
    