from analyzers import syntaxer
from analyzers import interpreter

import itertools

class ParamLoader(object):

    def __init__(self,params, values):

        def generate_str(str_list):
            full_list = []
            for i in range(len(str_list)):
                full_list += itertools.product(str_list,repeat=i+1)
            return ["".join(group) for group in full_list]

        self.params = params
        self.values = {p["name"]:list(values[p["name"]]) if p["type"][0] != "str" else generate_str(values[p["name"]]) for p in self.params}

        self.param_indexes = []
        init_values = []
        self.now_index = 0
        self.total = None
        for i,param_info in enumerate(self.params):
            self.param_indexes.append(0)
            match param_info["type"][0]:
                case "int":
                    init_values.append(0)
                case "bool":
                    init_values.append(True)
                case "chr":
                    init_values.append("")
                case "str":
                    init_values.append("")
                case others:
                    raise NotImplementedError("Don't know how to handle: {}".format(others))
        self.init_values = tuple(init_values)

    def __len__(self):
        if self.total is not None:
            return self.total

        self.total = int(len(self.params)>0)
        for param_info in self.params:
            self.total *= len(self.values[param_info["name"]])
        return self.total

    def has_next(self):
        return self.now_index < len(self)

    def next(self):

        def next_state(now_state,index=0):
            next_value = now_state[index] + 1
            if next_value == len(self.values[self.params[index]["name"]]) and index + 1 < len(now_state):
                now_state[index] = 0
                next_state(now_state, index + 1)
            else:
                now_state[index] = next_value
                self.now_index += 1

        param_values = []

        for i,param_info in enumerate(self.params):
            value = self.values[param_info["name"]][self.param_indexes[i]]
            param_values.append(value)

        next_state(self.param_indexes)

        return tuple(param_values)

def coverage_guided_fuzzing(method,tab = "\t"):
    param_values, array_values = method.parameter_filter(method.ast_values | method.get_bytecode_values())

    param_loader = ParamLoader(method.parameters, param_values)

    need_init = True
    total_pc_set = set()
    total_coverage = 0

    interest = []
    histories = set()

    while (param_loader.has_next() or need_init):
        if need_init:
            need_init = False
            case_parameters = param_loader.init_values
        else:
            case_parameters = param_loader.next()

        if case_parameters in histories:
            continue
        else:
            histories.add(case_parameters)

        case_result, pc_set = interpreter.run_test_case(
            method.bytecodes,
            case_parameters,
            method.parameters
        )

        coverage = len(pc_set) / len(method.bytecodes[1])
        total_pc_set |= pc_set
        new_total_coverage = len(total_pc_set) / len(method.bytecodes[1])

        if new_total_coverage > total_coverage:
            total_coverage = new_total_coverage

            for i in range(len(case_parameters)):
                if i >= len(interest):
                    interest.append(set())
                interest[i].add(case_parameters[i])

            print("{}[{:5.1f}%|{:5.1f}%] ({}) -> {}".format(
                tab,
                total_coverage * 100,
                coverage * 100,
                ", ".join(str(param) if type(param).__name__ != "str" else "'{}'".format(param) for param in case_parameters),
                case_result))

    return interest, total_pc_set

if __name__ == '__main__':
    methods = syntaxer.get_simplify_ast("Strings")

    for method in methods:
        print("[Method] {}:".format(method.name))
        interest, total_pc_set = coverage_guided_fuzzing(method)
        print("")