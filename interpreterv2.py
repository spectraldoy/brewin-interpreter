from bparser import BParser
from intbase import InterpreterBase, ErrorType
from brewin_object import Object
from classdef import ClassDef
from btypes import Type, TypeRegistry
from value import Value

class Interpreter(InterpreterBase):
    # define builtin operations
    binary_ops = {}
    binary_ops[Type.INT] = {
        "+": lambda a, b: Value(Type.INT, a.value + b.value),
        "-": lambda a, b: Value(Type.INT, a.value - b.value),
        "*": lambda a, b: Value(Type.INT, a.value * b.value),
        "/": lambda a, b: Value(Type.INT, a.value // b.value),
        "%": lambda a, b: Value(Type.INT, a.value % b.value),
        "==": lambda a, b: Value(Type.BOOL, a.value == b.value),
        "!=": lambda a, b: Value(Type.BOOL, a.value != b.value),
        ">": lambda a, b: Value(Type.BOOL, a.value > b.value),
        "<": lambda a, b: Value(Type.BOOL, a.value < b.value),
        ">=": lambda a, b: Value(Type.BOOL, a.value >= b.value),
        "<=": lambda a, b: Value(Type.BOOL, a.value <= b.value),
    }

    binary_ops[Type.STRING] = {
        "+": lambda a, b: Value(Type.STRING, a.value + b.value),
        "==": lambda a, b: Value(Type.BOOL, a.value == b.value),
        "!=": lambda a, b: Value(Type.BOOL, a.value != b.value),
        ">": lambda a, b: Value(Type.BOOL, a.value > b.value),
        "<": lambda a, b: Value(Type.BOOL, a.value < b.value),
        ">=": lambda a, b: Value(Type.BOOL, a.value >= b.value),
        "<=": lambda a, b: Value(Type.BOOL, a.value <= b.value),
    }

    binary_ops[Type.BOOL] = {
        "&": lambda a, b: Value(Type.BOOL, a.value and b.value),
        "|": lambda a, b: Value(Type.BOOL, a.value or b.value),
        "==": lambda a, b: Value(Type.BOOL, a.value == b.value),
        "!=": lambda a, b: Value(Type.BOOL, a.value != b.value)
    }

    # check equality of identity for objects
    binary_ops[Type.CLASS] = {
        "==": lambda a, b: Value(Type.BOOL, a.value is b.value),
        "!=": lambda a, b: Value(Type.BOOL, a.value is not b.value)
    }

    unary_ops = {}
    unary_ops[Type.BOOL] = {
        "!": lambda a: Value(Type.BOOL, not a.value)
    }

    binary_op_set = set.union(*[set(ops_for_type.keys()) for ops_for_type in binary_ops.values()])
    unary_op_set = set.union(*[set(ops_for_type.keys()) for ops_for_type in unary_ops.values()])

    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
        self.trace_output = trace_output
        self.main_object = None
        self.__class_definitions = {}

        # reinitialize the TypeRegistry
        TypeRegistry.clear()
    
    def run(self, program):
        status, parsed_program = BParser.parse(program)

        if not status:
            super().error(
                ErrorType.SYNTAX_ERROR, f"Parse error: {parsed_program}"
            )
        
        # first pass: define all classes, their fields and methods
        for parsed_class in parsed_program:
            self.__define_class(parsed_class)
        
        # second pass: instantiate and run main
        self.main_object = self.instantiate_class(InterpreterBase.MAIN_CLASS_DEF)
        # according to Barista, main doesn't have to have void return type I guess
        self.main_object.execute_method(InterpreterBase.MAIN_FUNC_DEF)
        
    def get_class_def(self, class_name):
        if class_name not in self.__class_definitions:
            super().error(
                ErrorType.TYPE_ERROR,
                f"No class named {class_name} found"
            )
        
        return self.__class_definitions[class_name]

    def instantiate_class(self, class_name, line_num=None):
        class_def = self.get_class_def(class_name)
        ret = Object(self, class_def)
        if not ret.status.ok:
            ret.status.line_num = line_num
            super().error(*ret.status[1:])
        
        return ret

    def __define_class(self, parsed_class):
        if parsed_class[0] != InterpreterBase.CLASS_DEF:
            super().error(
                ErrorType.SYNTAX_ERROR,
                f"Brewin++ expects only classes to be defined at the outermost level",
                parsed_class[0].line_num
            )
        
        name = parsed_class[1]
        if name in self.__class_definitions:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Two or more definitions of class {name}",
                name.line_num
            )
        
        self.__class_definitions[name] = ClassDef(parsed_class, self)

