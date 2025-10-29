import tree_sitter
import tree_sitter_java
import sys
from pathlib import Path
import re
import subprocess
import os

JAVA_MAIN_PATH = "../src/main/java"
JAVA_CLASS_PATH = "../target/classes"
JAVA_CASE_PATH = "jpamb/cases"

SUB_OPCODE_LIST = ["aload","astore","dconst","dload","dstore","dup","dup2","fconst","fload","fstore","iconst","iload","istore","lconst","lload","lstore"]

class JavaMethod(object):
    def __init__(self):
        self.name = None
        self.parameters = []
        self.return_type = None
        self.bytecodes = []
        self.cases = []

def analyze_ast(tree):
    method_list = []

    def check(node):
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
                                "type": p_t,
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
                        continue
                    case others:
                        if others not in ["void_type","integral_type","boolean_type","array_type","type_identifier"]:
                            raise NotImplementedError("Don't know how to handle: {}".format(others))
                        method.return_type = text

            method_list.append(method)

        for child in node.children:
            check(child)

    check(tree.root_node)
    return method_list

def compile(name):
    subprocess.run([
        "javac",
        "-d",JAVA_CLASS_PATH,
        "/".join([JAVA_MAIN_PATH, JAVA_CASE_PATH, "{}.java".format(name)]),
        "/".join([JAVA_MAIN_PATH, "jpamb/utils/Cases.java"]),
        "/".join([JAVA_MAIN_PATH, "jpamb/utils/Case.java"]),
       ], check=True)

def decompile_bytecode(name):
    method_opcodes = {}

    java_path = "/".join([JAVA_MAIN_PATH, JAVA_CASE_PATH, "{}.java".format(name)])
    class_path = "/".join([JAVA_CLASS_PATH, JAVA_CASE_PATH, "{}.class".format(name)])
    if not os.path.exists(class_path) or os.path.getmtime(java_path) > os.path.getmtime(class_path):
        compile(name)

    result = subprocess.run(["javap", "-c", "-classpath", JAVA_CLASS_PATH, "jpamb.cases.{}".format(name)],capture_output=True, text=True, check=True)
    #print(result.stdout)
    #print(subprocess.run(["javap", "-v", "-classpath", JAVA_CLASS_PATH, "jpamb.cases.{}".format(name)],capture_output=True, text=True, check=True).stdout)

    method_bytecodes = result.stdout.split("\n\n")[1:]
    for decompiled_info in method_bytecodes:
        method_info, codes = decompiled_info.split("Code:")
        method_info = method_info.strip()
        codes = codes.strip()

        method_access = method_info.split(" ")[0:-2]
        if len(method_access) == 0:
            continue

        method_name = re.findall(r'.+?(?=\()', method_info)[0].split(" ")[-1]
        opcodes = []
        for line in codes.split("\n"):
            opcode_info = decode_bytecode(line)
            if opcode_info is None:
                continue
            opcodes.append(opcode_info)

        method_opcodes[method_name] = (method_access,opcodes)
    return method_opcodes

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
    src_path = "/".join([JAVA_MAIN_PATH, JAVA_CASE_PATH, "{}.java".format(name)])

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