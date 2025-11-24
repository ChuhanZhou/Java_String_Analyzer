import tree_sitter
import tree_sitter_java
import sys
from pathlib import Path
import re
import subprocess
import os

# could not find file, so making the root path absolute (derived from __file__)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
JAVA_ROOT_PATH = str(PROJECT_ROOT)
JAVA_MAIN_PATH = "benchmark_suite/src/main/java"
JAVA_CLASS_PATH = "benchmark_suite/target/classes"
JAVA_CASE_PATH = "jpamb/cases"

SUB_OPCODE_LIST = ["aload","astore","dconst","dload","dstore","dup","dup2","fconst","fload","fstore","iconst","iload","istore","lconst","lload","lstore"]

JAVA_TYPE_MAP = {
    "int": ("int",False), #(type,is_array)
    "int[]": ("int",True),
    "boolean": ("bool",False),
    "boolean[]": ("bool",True),
    "char": ("chr",False),
    "char[]": ("chr",True),
    "String": ("str",False),
    "String[]": ("str",True),
    "java/lang/String": ("str",False),
}

def case_str_2_value(str_value,value_type):
    if str_value == "null":
        return None

    match value_type:
        case "int":
            return int(str_value)
        case "chr":
            return re.findall(r'(?<=\').*?(?=\')', str_value)[0]
        case "str":
            return str_value.encode().decode('unicode_escape')[1:-1]
        case "bool":
            return str_value.lower() == "true"
        case others:
            raise NotImplementedError("Don't know how to handle: {}".format(others))

class JavaMethod(object):
    def __init__(self):
        self.name = None
        self.parameters = []
        self.return_type = None
        self.return_array = False
        self.bytecodes = []
        self.cases = []
        self.has_assert = False
        self.ast_values = set()

    def syntactic_report(self):
        bytecode_values = self.get_bytecode_values()
        fuzzy_values,array_parameter_values = self.parameter_filter(self.ast_values | bytecode_values)
        report = ("[Method]: {}\n"
                  "[has assertion]: {}\n"
                  "[values from AST]: {}\n"
                  "[values from bytecode]: {}\n"
                  "[values for fuzzer]:\n".format(self.name,self.has_assert,list(self.ast_values),list(bytecode_values)))
        if len(fuzzy_values) == 0:
            report += "\tThis method has no parameter.\n"
        else:
            if array_parameter_values is not None:
                report += "\t[parameters of array]: {}\n".format(list(array_parameter_values))
            for parameter in self.parameters:
                type_str = parameter["type"][0]
                if parameter["type"][1]:
                    type_str+="[]"
                report += "\t({} {}): {}\n".format(type_str,parameter["name"],list(fuzzy_values[parameter["name"]]))
        return report

    def parameter_filter(self,values):
        type_values = {
            "bool": {True, False},
            "int": set(),
        }

        for value in values:
            value_type = type(value).__name__

            if value_type not in type_values:
                type_values[value_type] = set()

            type_values[value_type].add(value)

            if value_type == "chr":
                type_values["str"].add(value)

            if value_type == "str":
                if len(value) == 1:
                    if "chr" not in type_values:
                        type_values["chr"] = set()

                    type_values["chr"].add(value)
                type_values["int"].add(len(value))

        parameter_values = {}
        array_parameter_values = None

        for parameter in self.parameters:

            if parameter["type"][0] in type_values:
                parameter_values[parameter["name"]] = type_values[parameter["type"][0]]
            else:
                parameter_values[parameter["name"]] = set()

            if (parameter["type"][1] or parameter["type"][0] == "chr") and array_parameter_values is None: #array
                array_parameter_values = type_values["int"]

        return parameter_values, array_parameter_values

    def get_bytecode_values(self):
        bytecode_values = set()
        for i,bytecode_info in enumerate(self.bytecodes[1]):
            match bytecode_info[1]:
                case "ldc":
                    match bytecode_info[2][0]:
                        case "int":
                            bytecode_values.add(int(bytecode_info[2][1]))
                        case "str":
                            bytecode_values.add(bytecode_info[2][1])
                case "bipush":
                    value = int(bytecode_info[2])
                    match self.bytecodes[1][i-1][1]:
                        #case "iconst":
                        #    bytecode_values.add(value)
                        #case "iload":
                        #    bytecode_values.add(value)
                        case "caload":
                            bytecode_values.add(chr(value))
                        case others:
                            bytecode_values.add(value)
                            #raise NotImplementedError("Don't know how to handle: {}".format(others))
                case "sipush":
                    value = int(bytecode_info[2])
                    bytecode_values.add(value)
                case "iconst":
                    if bytecode_info[2] == "m1":
                        bytecode_values.add(-1)
                    else:
                        bytecode_values.add(int(bytecode_info[2]))
                case "invokedynamic":
                    values = set(bytecode_info[2]["values"])
                    values.remove(None)
                    bytecode_values |= values
        return bytecode_values

def str_param_parser(str_param,sub_list = None):
    if sub_list is not None:
        sub_list.reverse()

    pure_str_lists = re.findall(r'(?<=\[)[^\[\]]*(?=\])', str_param)

    if pure_str_lists:
        pure_lists = []
        for pure_str in pure_str_lists:
            pure_str = re.findall(r'(?<=[A-Za-z]:).*',pure_str)[0]
            pure_lists.append(str_param_parser(pure_str))

        next = re.sub(r'\[[^\[\]]*\]', "#LIST#", str_param)
        return str_param_parser(next,pure_lists)
    else:
        str_param_list = []
        for str_v in str_param.split(","):
            str_v = str_v.strip()
            if str_v == '':
                break
            elif str_v == "#LIST#":
                str_param_list.append(sub_list.pop())
            else:
                str_param_list.append(str_v)
        return str_param_list


def analyze_ast(tree):
    method_list = []

    def check(node,method = None):
        if method is None: #find method
            if node.type == "method_declaration":
                method = JavaMethod()

                for child in node.children:
                    text = child.text.decode('utf8')

                    match child.type:
                        case "identifier":
                            method.name = text
                        case "formal_parameters":
                            parameters = re.findall(r'(?<=\().*?(?=\))', text)[0].split(',')
                            for p in parameters:
                                p = p.strip()
                                if p == "":
                                    break
                                p_t, p_n = p.split(" ")
                                method.parameters.append({
                                    "name": p_n,
                                    "type": JAVA_TYPE_MAP[p_t],
                                })
                        case "modifiers":
                            case_info_list = re.findall(r'(?<=@Case).+?(?=\n)', text)
                            for case_info in case_info_list:
                                case = {}
                                case_info = re.findall(r'(?<=").+?(?=(?<!\\)")', case_info)[0]

                                case["inputs"] = str_param_parser(re.findall(r'(?<=\().*?(?=\))', case_info)[0])
                                case["result"] = re.findall(r'(?<=\s->\s).+', case_info)[0]
                                method.cases.append(case)
                        case "block":
                            check(child,method)
                        case "array_type":
                            for cc in child.children:
                                if cc.type == "dimensions":
                                    method.return_array = True
                                elif cc.type not in ["integral_type", "boolean_type", "type_identifier"]:
                                    raise NotImplementedError("Don't know how to handle: {}".format(cc.type))
                                else:
                                    method.return_type = str(cc.text.decode('utf8'))
                        case others:
                            if others not in ["void_type", "integral_type", "boolean_type", "type_identifier"]:
                                raise NotImplementedError("Don't know how to handle: {}".format(others))
                            method.return_type = text

                #Convert cases input data type from str to real value
                for case in method.cases:
                    for v_i in range(len(case["inputs"])):
                        v_type = method.parameters[v_i]["type"]

                        if v_type[1]:
                            for l_i,str_v in enumerate(case["inputs"][v_i]):
                                case["inputs"][v_i][l_i] = case_str_2_value(str_v,v_type[0])
                        else:
                            case["inputs"][v_i] = case_str_2_value(case["inputs"][v_i],v_type[0])

                method_list.append(method)

            for child in node.children:
                check(child)
        else: #check in method
            if node.type == "assert_statement":
                method.has_assert = True

            match node.type:
                case "decimal_integer_literal": #posstive number
                    method.ast_values.add(int(node.text.decode('utf8')))
                case "unary_expression": #may found negative number
                    negative_number_types = {"-","decimal_integer_literal"}
                    child_types = set()
                    for child in node.children:
                        child_types.add(child.type)
                    if negative_number_types == child_types: #found negative number
                        method.ast_values.add(int(node.text.decode('utf8')))
                    else:
                        for child in node.children:
                            check(child, method)
                case "/":
                    method.ast_values.add(0)
                case "true":
                    method.ast_values.add(True)
                case "false":
                    method.ast_values.add(False)
                case "string_literal":
                    method.ast_values.add(node.text.decode('utf8')[1:-1])
                case "character_literal":
                    method.ast_values.add(node.text.decode('utf8')[1:-1])
                case "string_fragment":
                    method.ast_values.add(node.text.decode('utf8')[1:-1])
                case others:
                    for child in node.children:
                        check(child,method)

    check(tree.root_node)
    return method_list

def compile(name):
    subprocess.run([
        "javac",
        "-d","/".join([JAVA_ROOT_PATH, JAVA_CLASS_PATH]),
        "/".join([JAVA_ROOT_PATH, JAVA_MAIN_PATH, "jpamb/utils/Case.java"]),
        "/".join([JAVA_ROOT_PATH, JAVA_MAIN_PATH, "jpamb/utils/Cases.java"]),
        "/".join([JAVA_ROOT_PATH, JAVA_MAIN_PATH, "jpamb/utils/Tag.java"]),
        "/".join([JAVA_ROOT_PATH, JAVA_MAIN_PATH, JAVA_CASE_PATH, "{}.java".format(name)]),
    ], check=True)

def get_bootstrap_arguments(name):
    result = subprocess.run(["javap", "-v", "-classpath", "/".join([JAVA_ROOT_PATH, JAVA_CLASS_PATH]),"jpamb.cases.{}".format(name)], capture_output=True, text=True, check=True)
    #print(result.stdout)
    bootstrap_argument_info = re.findall(r'BootstrapMethods:.*?(?=\n\S)', result.stdout, re.S)

    if len(bootstrap_argument_info)==1:
        bootstrap_argument_info = bootstrap_argument_info[0]
        bootstrap_args = {}

        for i,arg_info in re.findall(r'^\s*(\d+):.*?Method arguments:\s*#\d+\s([^\n]+)', bootstrap_argument_info, re.M | re.S):
            args = []
            for v in arg_info.split('\\u0001'):
                if v != "":
                    args.append(v)
                args.append(None)
            bootstrap_args[i] = args[0:-1]
        return bootstrap_args
    else:
        return None

def fit_env_ver(name):
    try:
        result = subprocess.run(["javap", "-v", "-classpath", "/".join([JAVA_ROOT_PATH, JAVA_CLASS_PATH]), "jpamb.cases.{}".format(name)],capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e: # use low version to decompile
        return False
    major_ver = int(re.findall(r'(?<=major version: )\d*?(?=\n)',result.stdout)[0])
    java_ver = major_ver - 44
    if java_ver <= 8:
        java_ver = "1.{}".format(java_ver)
        match_re = r'(?<=javac )\d+?\.\d+?(?=\.)'
    else:
        java_ver = str(java_ver)
        match_re = r'(?<=javac )\d+?(?=\.)'
    env_ver = re.findall(match_re,subprocess.run(["javac", "-version"],capture_output=True, text=True).stdout)[0]
    return env_ver == java_ver

def decompile_bytecode(name):
    method_bytecodes = {}

    java_path = "/".join([JAVA_ROOT_PATH, JAVA_MAIN_PATH, JAVA_CASE_PATH, "{}.java".format(name)])
    class_path = "/".join([JAVA_ROOT_PATH, JAVA_CLASS_PATH, JAVA_CASE_PATH, "{}.class".format(name)])
    if not os.path.exists(class_path) or os.path.getmtime(java_path) > os.path.getmtime(class_path) or not fit_env_ver(name):
        compile(name)

    result = subprocess.run(["javap", "-c", "-classpath", "/".join([JAVA_ROOT_PATH, JAVA_CLASS_PATH]), "jpamb.cases.{}".format(name)],capture_output=True, text=True, check=True)

    method_bytecode_texts = result.stdout.split("\n\n")[1:]
    bootstrap_args = get_bootstrap_arguments(name)

    for decompiled_text in method_bytecode_texts:
        method_info, codes = decompiled_text.split("Code:")
        method_info = method_info.strip()
        codes = codes.strip()

        method_access = method_info.split(" ")[0:-2]
        if len(method_access) == 0:
            continue

        method_name = re.findall(r'.+?(?=\()', method_info)[0].split(" ")[-1]
        bytecodes = []
        for line in codes.split("\n"):
            bytecode_info = decode_bytecode(line,bootstrap_args)
            if bytecode_info is None:
                continue
            bytecodes.append(bytecode_info)

        method_bytecodes[method_name] = (method_access,bytecodes)
    return method_bytecodes

def decode_bytecode(code_line,bootstrap_args):
    code_line = code_line.strip()
    index = code_line.split(":")[0]
    if index.isdigit():
        index = int(index)
    else:
        return None

    opcode_info = []
    constant_info = None
    info_list = opcode_info
    for info in code_line.split(": ")[1].strip().split(" "):
        if info == "" and constant_info is None:
            continue
        elif info == "//":
            constant_info = []
            info_list = constant_info
            continue

        if constant_info is None:
            if len(info.split("_")) == 2 and info.split("_")[0] in SUB_OPCODE_LIST:
                info_list += info.split("_")
            else:
                info_list.append(info.split(",")[0])
        else:
            info_list.append(info)

    decode_info = [index,*opcode_info]
    if len(opcode_info)>3:
        raise NotImplementedError("Don't know how to decode: {}".format(code_line))

    if constant_info is not None:
        decode_info = decode_info[0:2]#remove constant index
        constant_type = constant_info[0]
        if constant_type in JAVA_TYPE_MAP:
            constant_type = JAVA_TYPE_MAP[constant_type][0]
        elif constant_type.lower() != decode_info[1]:
            constant_type = constant_type.lower()

        if len(constant_info)>2: #reconstruct constant info
            constant_value = " ".join(constant_info[1:])
        elif len(constant_info) == 1:
            constant_value = ""
        else:
            constant_value = constant_info[1]

        match constant_type:
            case "InvokeDynamic":
                dynamic_method = {
                    "name": constant_value.split(":")[1],
                    "parameters": [JAVA_TYPE_MAP[v][0] for v in re.findall(r'(?<=L).*?(?=;)',re.findall(r'(?<=\().*?(?=\))', constant_value)[0])],
                    "values": bootstrap_args[re.findall(r'(?<=#)\d+(?=:)',constant_value)[0]], # None means it's a parameter, otherwise it's a constant
                    "return": [JAVA_TYPE_MAP[v][0] for v in re.findall(r'(?<=L).*?(?=;)',re.findall(r'(?<=\)).*', constant_value)[0])],
                }
                decode_info.append(dynamic_method)
            case others:
                decode_info.append((constant_type,constant_value))

    return tuple(decode_info)

def get_simplify_ast(name):
    src_path = "/".join([JAVA_ROOT_PATH, JAVA_MAIN_PATH, JAVA_CASE_PATH, "{}.java".format(name)])

    JAVA_LANGUAGE = tree_sitter.Language(tree_sitter_java.language())
    parser = tree_sitter.Parser(JAVA_LANGUAGE)

    with open(src_path, "rb") as f:
        tree = parser.parse(f.read())

    methods = analyze_ast(tree)

    opcodes = decompile_bytecode(name)
    for method in methods:
        method.bytecodes = opcodes[method.name]

    return methods

if __name__ == '__main__':
    methods = get_simplify_ast("Strings")

    for method in methods:
        print(method.syntactic_report())