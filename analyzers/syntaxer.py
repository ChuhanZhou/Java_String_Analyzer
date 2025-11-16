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
    "String": ("str",False),
    "String[]": ("str",True),
    "char": ("chr",False),
    "char[]": ("chr",True),
}

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
        }

        for value in values:
            value_type = type(value).__name__

            if value_type not in type_values:
                type_values[value_type] = set()

            type_values[value_type].add(value)

            if value_type == "str" and len(value) == 1:
                if "chr" not in type_values:
                    type_values["chr"] = set()

                type_values["chr"].add(value)

        parameter_values = {}
        array_parameter_values = None

        for parameter in self.parameters:

            if parameter["type"][0] in type_values:
                parameter_values[parameter["name"]] = type_values[parameter["type"][0]]
            else:
                parameter_values[parameter["name"]] = set()

            if parameter["type"][1] and array_parameter_values is None: #array
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
                #case "iconst":
                #    if bytecode_info[2] == "m1":
                #        bytecode_values.add(-1)
                #    else:
                #        bytecode_values.add(int(bytecode_info[2]))
        return bytecode_values

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
                                method.cases.append(case)

                                case_info = re.findall(r'(?<=").+?(?=")', case_info)[0]

                                case["inputs"] = []
                                case_inputs = re.findall(r'(?<=\().*?(?=\))', case_info)[0].split(',')
                                for case_input in case_inputs:
                                    case_input = case_input.strip()
                                    if case_input == '':
                                        break
                                    case["inputs"].append(case_input)

                                case["result"] = re.findall(r'(?<=\s->\s).+', case_info)[0]
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

                method_list.append(method)

            for child in node.children:
                check(child)
        else: #check in method
            if node.type == "assert_statement":
                method.has_assert = True

            match node.type:
                case "decimal_integer_literal": #posstive number
                    method.ast_values.add(int(node.text.decode('utf8')))
                case "unary_expression": #negative number
                    negative_number_types = {"-","decimal_integer_literal"}
                    child_types = set()
                    for child in node.children:
                        child_types.add(child.type)
                    if negative_number_types == child_types:
                        method.ast_values.add(int(node.text.decode('utf8')))
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
                case others:
                    for child in node.children:
                        check(child,method)

    check(tree.root_node)
    return method_list

def compile(name):
    subprocess.run([
        "javac",
        "-d","/".join([JAVA_ROOT_PATH, JAVA_CLASS_PATH]),
        "/".join([JAVA_ROOT_PATH, JAVA_MAIN_PATH, JAVA_CASE_PATH, "{}.java".format(name)]),
        "/".join([JAVA_ROOT_PATH, JAVA_MAIN_PATH, "jpamb/utils/Case.java"]),
        "/".join([JAVA_ROOT_PATH, JAVA_MAIN_PATH, "jpamb/utils/Cases.java"]),
        "/".join([JAVA_ROOT_PATH, JAVA_MAIN_PATH, "jpamb/utils/Tag.java"]),
       ], check=True)

def decompile_bytecode(name):
    method_bytecodes = {}

    java_path = "/".join([JAVA_ROOT_PATH, JAVA_MAIN_PATH, JAVA_CASE_PATH, "{}.java".format(name)])
    class_path = "/".join([JAVA_ROOT_PATH, JAVA_CLASS_PATH, JAVA_CASE_PATH, "{}.class".format(name)])
    if not os.path.exists(class_path) or os.path.getmtime(java_path) > os.path.getmtime(class_path):
        compile(name)

    result = subprocess.run(["javap", "-c", "-classpath", "/".join([JAVA_ROOT_PATH, JAVA_CLASS_PATH]), "jpamb.cases.{}".format(name)],capture_output=True, text=True, check=True)
    #print(result.stdout)
    #print(subprocess.run(["javap", "-v", "-classpath", "/".join([JAVA_ROOT_PATH, JAVA_CLASS_PATH]), "jpamb.cases.{}".format(name)],capture_output=True, text=True, check=True).stdout)

    method_bytecode_texts = result.stdout.split("\n\n")[1:]
    for decompiled_text in method_bytecode_texts:
        method_info, codes = decompiled_text.split("Code:")
        method_info = method_info.strip()
        codes = codes.strip()

        method_access = method_info.split(" ")[0:-2]
        if len(method_access) == 0:
            continue

        method_name = re.findall(r'.+?(?=\()', method_info)[0].split(" ")[-1]
        bytecodes = []
        values = []
        for line in codes.split("\n"):
            bytecode_info = decode_bytecode(line)
            if bytecode_info is None:
                continue
            bytecodes.append(bytecode_info)

        method_bytecodes[method_name] = (method_access,bytecodes)
    return method_bytecodes

def decode_bytecode(code_line):
    code_line = code_line.strip()
    index = code_line.split(":")[0]
    if index.isdigit():
        index = int(index)
    else:
        return None

    opcode_info = []
    for info in code_line.split(":")[1].strip().split(" "):
        if info == "":
            continue

        if len(info.split("_")) == 2 and info.split("_")[0] in SUB_OPCODE_LIST:
            opcode_info += info.split("_")
        else:
            opcode_info.append(info.split(",")[0])

    match len(opcode_info):
        case 1:
            return (index,*opcode_info) #(index,opcode)
        case 2:
            return (index,*opcode_info) #(index,opcode,value)
        case 3:
            return (index,*opcode_info) #(index,opcode,value,value)
        case 5:
            if opcode_info[1][0] == "#" and opcode_info[2] == "//":
                return (index,opcode_info[0],(opcode_info[3].lower(),opcode_info[4])) #(index,opcode,value)
        case n:
            #return (index,*opcode_info)
            raise NotImplementedError("Don't know how to decode: {}".format(code_line))

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
    methods = get_simplify_ast("Simple")

    for method in methods:
        print(method.syntactic_report())