
from dataclasses import dataclass
from pathlib import Path
import sys
from loguru import logger
jpamb_path = Path(__file__).parent / "benchmark_suite"
sys.path.insert(0, str(jpamb_path))

logger.remove()
logger.add(sys.stderr, format="[{level}] {message}")

import jpamb
from jpamb import jvm
suite = jpamb.Suite()


@dataclass
class PC:
    method: jvm.AbsMethodID
    offset: int

    def __iadd__(self, delta):
        self.offset += delta
        return self

    def __add__(self, delta):
        return PC(self.method, self.offset + delta)

    def __str__(self):
        return f"{self.method}:{self.offset}"


@dataclass
class Bytecode:
    suite: jpamb.Suite
    methods: dict[jvm.AbsMethodID, list[jvm.Opcode]]

    def __getitem__(self, pc: PC) -> jvm.Opcode:
        try:
            opcodes = self.methods[pc.method]
        except KeyError:
            opcodes = list(self.suite.method_opcodes(pc.method))
            self.methods[pc.method] = opcodes

        return opcodes[pc.offset]


@dataclass
class Stack[T]:
    items: list[T]

    def __bool__(self) -> bool:
        return len(self.items) > 0

    @classmethod
    def empty(cls):
        return cls([])

    def peek(self) -> T:
        return self.items[-1]

    def pop(self) -> T:
        return self.items.pop(-1)

    def push(self, value):
        self.items.append(value)
        return self

    def __str__(self):
        if not self:
            return "ϵ"
        return "".join(f"{v}" for v in self.items)


suite = jpamb.Suite()
bc = Bytecode(suite, dict())


@dataclass
class Frame:
    locals: dict[int, jvm.Value]
    stack: Stack[jvm.Value]
    pc: PC

    def __str__(self):
        locals = ", ".join(f"{k}:{v}" for k, v in sorted(self.locals.items()))
        return f"<{{{locals}}}, {self.stack}, {self.pc}>"

    def from_method(method: jvm.AbsMethodID) -> "Frame":
        return Frame({}, Stack.empty(), PC(method, 0))


@dataclass
class State:
    heap: dict[int, jvm.Value]
    frames: Stack[Frame]

    def __str__(self):
        return f"{self.heap} {self.frames}"


def step(state: State) -> State | str:
    assert isinstance(state, State), f"expected frame but got {state}"
    frame = state.frames.peek()
    opr = bc[frame.pc]
    logger.debug(f"STEP {opr}\n{state}")
    match opr:
        case jvm.Push(value=v):
            frame.stack.push(v)
            frame.pc += 1
            return state
        
        case jvm.Pop():
            frame.stack.pop()
            frame.pc += 1
            return state
        
        case jvm.Dup():
            frame.stack.push(frame.stack.peek)
            frame.pc += 1
            return state
        
        case jvm.Load(type=jvm.Int(), index=i):
            frame.stack.push(frame.locals[i])
            frame.pc += 1
            return state
        
        case jvm.Load(type=jvm.Bool(), index=i):
            frame.stack.push(frame.locals[i])
            frame.pc += 1
            return state
        
        case jvm.Store(type=t, index=i):
            v = frame.stack.pop()
            frame.locals[i] = v
            frame.pc += 1
            return state
        
        case jvm.Binary(type=jvm.Int(), operant=jvm.BinaryOpr.Add):
            v2, v1 = frame.stack.pop(), frame.stack.pop()
            assert v1.type is jvm.Int(), f"expected int, but got {v1}"
            assert v2.type is jvm.Int(), f"expected int, but got {v2}"
            frame.stack.push(jvm.Value.int(v1.value + v2.value))
            frame.pc += 1
            return state

        case jvm.Binary(type=jvm.Int(), operant=jvm.BinaryOpr.Sub):
            v2, v1 = frame.stack.pop(), frame.stack.pop()
            assert v1.type is jvm.Int(), f"expected int, but got {v1}"
            assert v2.type is jvm.Int(), f"expected int, but got {v2}"
            frame.stack.push(jvm.Value.int(v1.value - v2.value))
            frame.pc += 1
            return state

        case jvm.Binary(type=jvm.Int(), operant=jvm.BinaryOpr.Mul):
            v2, v1 = frame.stack.pop(), frame.stack.pop()
            assert v1.type is jvm.Int(), f"expected int, but got {v1}"
            assert v2.type is jvm.Int(), f"expected int, but got {v2}"
            frame.stack.push(jvm.Value.int(v1.value * v2.value))
            frame.pc += 1
            return state
        
        case jvm.Binary(type=jvm.Int(), operant=jvm.BinaryOpr.Div):
            v2, v1 = frame.stack.pop(), frame.stack.pop()
            assert v1.type is jvm.Int(), f"expected int, but got {v1}"
            assert v2.type is jvm.Int(), f"expected int, but got {v2}"
            if v2.value == 0:
                return "divide by zero"

            frame.stack.push(jvm.Value.int(v1.value // v2.value))
            frame.pc += 1
            return state
        
        case jvm.If(condition=cond, target=target):
            v = frame.stack.pop()
            should_jump = False
            match cond:
                case jvm.Condition.EQ:
                    should_jump = (v.value == 0)
                case jvm.Condition.NE:
                    should_jump = (v.value != 0)
                case jvm.Condition.LT:
                    should_jump = (v.value < 0)
                case jvm.Condition.GE:
                    should_jump = (v.value >= 0)
                case jvm.Condition.GT:
                    should_jump = (v.value > 0)
                case jvm.Condition.LE:
                    should_jump = (v.value <= 0)
            
            if should_jump:
                frame.pc.offset = target
            else:
                frame.pc += 1
            return state
        
        case jvm.IfCmp(type=t, condition=cond, target=target):
            v2, v1 = frame.stack.pop(), frame.stack.pop()
            should_jump = False
            match cond:
                case jvm.Condition.EQ:
                    should_jump = (v1.value == v2.value)
                case jvm.Condition.NE:
                    should_jump = (v1.value != v2.value)
                case jvm.Condition.LT:
                    should_jump = (v1.value < v2.value)
                case jvm.Condition.GE:
                    should_jump = (v1.value >= v2.value)
                case jvm.Condition.GT:
                    should_jump = (v1.value > v2.value)
                case jvm.Condition.LE:
                    should_jump = (v1.value <= v2.value)
            
            if should_jump:
                frame.pc.offset = target
            else:
                frame.pc += 1
            return state
        
        case jvm.Invoke(method=method):
            if "AssertionError" in str(method):
                return "assertion error"
            frame.pc += 1
            return state
        
        case jvm.New(type=t):
            frame.pc += 1
            return state
        
        case jvm.Throw():
            return "assertion error"
        
        case jvm.Return(type=jvm.Void()):
            state.frames.pop()
            if state.frames:
                frame = state.frames.peek()
                frame.pc += 1
                return state
            else:
                return "ok"

        
        case jvm.Return(type=jvm.Int()):
            v1 = frame.stack.pop()
            state.frames.pop()
            if state.frames:
                frame = state.frames.peek()
                frame.stack.push(v1)
                frame.pc += 1
                return state
            else:
                return "ok"
        case a:
            raise NotImplementedError(f"Don't know how to handle: {a!r}")

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
                    stack.append(jvm.Value.int(-1))
                else:
                    stack.append(jvm.Value.int(int(args[0])))
                pc += 1
                
            elif opcode == "bipush" or opcode == "sipush":
                stack.append(jvm.Value.int(int(args[0])))
                pc += 1
                
            elif opcode == "ldc":
                if args[0][0] == "int":
                    stack.append(jvm.Value.int(int(args[0][1])))
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
                stack.append(jvm.Value.int(v1.value + v2.value))
                pc += 1
                
            elif opcode == "isub":
                v2, v1 = stack.pop(), stack.pop()
                stack.append(jvm.Value.int(v1.value - v2.value))
                pc += 1
                
            elif opcode == "imul":
                v2, v1 = stack.pop(), stack.pop()
                stack.append(jvm.Value.int(v1.value * v2.value))
                pc += 1
                
            elif opcode == "idiv":
                v2, v1 = stack.pop(), stack.pop()
                if v2.value == 0:
                    return "divide by zero"
                stack.append(jvm.Value.int(v1.value // v2.value))
                pc += 1
                
            elif opcode in ["if_icmpeq", "if_icmpne", "if_icmplt", "if_icmple", "if_icmpgt", "if_icmpge"]:
                target = int(args[0])
                v2, v1 = stack.pop(), stack.pop()
                
                should_jump = False
                if opcode == "if_icmpeq":
                    should_jump = (v1.value == v2.value)
                elif opcode == "if_icmpne":
                    should_jump = (v1.value != v2.value)
                elif opcode == "if_icmplt":
                    should_jump = (v1.value < v2.value)
                elif opcode == "if_icmple":
                    should_jump = (v1.value <= v2.value)
                elif opcode == "if_icmpgt":
                    should_jump = (v1.value > v2.value)
                elif opcode == "if_icmpge":
                    should_jump = (v1.value >= v2.value)
                
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
                    should_jump = (v.value == 0)
                elif opcode == "ifne":
                    should_jump = (v.value != 0)
                elif opcode == "iflt":
                    should_jump = (v.value < 0)
                elif opcode == "ifle":
                    should_jump = (v.value <= 0)
                elif opcode == "ifgt":
                    should_jump = (v.value > 0)
                elif opcode == "ifge":
                    should_jump = (v.value >= 0)
                
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
                pc += 1
                
            elif opcode == "dup":
                stack.append(stack[-1])
                pc += 1
                
            elif opcode == "athrow":
                return "assertion error"
                
            elif opcode == "getstatic":
                # $assertionsDisabled = false (
                stack.append(jvm.Value.int(0))
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
                input_values.append(jvm.Value.int(1 if param == 'true' else 0))
            else:
                input_values.append(jvm.Value.int(int(param)))
        else:
            input_values.append(jvm.Value.int(int(param)))
    
    return input_values

def run_test_case(bytecodes, case_parameters, method_parameters):
    input_values = convert_parameters(case_parameters, method_parameters)
    return run_bytecodes(bytecodes, input_values)

if __name__ == '__main__':
    methodid, input = jpamb.getcase()
    suite = jpamb.Suite()
    opcodes = list(suite.method_opcodes(methodid))

    frame = Frame.from_method(methodid)
    for i, v in enumerate(input.values):
        frame.locals[i] = v

    state = State({}, Stack.empty().push(frame))

    for x in range(1000):
        state = step(state)
        if isinstance(state, str):
            print(state)
            break
    else:
        print("*")
