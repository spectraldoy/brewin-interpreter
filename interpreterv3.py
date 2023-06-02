from bparser import BParser
from intbase import InterpreterBase, ErrorType
from brewin_object import Object, BrewinException
from classdef import ClassDef
from tclassdef import TClassDef
from btypes import Type, TypeRegistry, TClassRegistry
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
        self.__tclass_definitions = {}

        # reinitialize the TypeRegistry
        TypeRegistry.clear()
        # reinitialize the TClassRegistry
        TClassRegistry.clear()
    
    def run(self, program):
        status, parsed_program = BParser.parse(program)

        if not status:
            super().error(
                ErrorType.SYNTAX_ERROR, f"Parse error: {parsed_program}"
            )
        
        # first pass: define all tclasses
        for parsed_class_or_tclass in parsed_program:
            self.__define_tclass(parsed_class_or_tclass)
        
        # second pass: define all classes
        for parsed_class_or_tclass in parsed_program:
            self.__define_class(parsed_class_or_tclass)
        
        # once all classes are defined, extract field and method defs for each class
        for class_def in self.__class_definitions.values():
            class_def.extract_field_and_method_defs()
        
        # third pass: instantiate and run main
        self.main_object = self.instantiate_class(InterpreterBase.MAIN_CLASS_DEF)

        # we should just terminate if we get a BrewinException, shouldn't crash
        try:
            # according to Barista, main doesn't have to have void return type I guess
            self.main_object.execute_method(InterpreterBase.MAIN_FUNC_DEF)
        except BrewinException:
            pass
        
    def get_class_def(self, class_name):
        if class_name not in self.__class_definitions:
            super().error(
                ErrorType.TYPE_ERROR,
                f"No class named {class_name} found"
            )
        
        return self.__class_definitions[class_name]

    def get_tclass_def(self, tclass_string):
        name, *type_args = tclass_string.split(InterpreterBase.TYPE_CONCAT_CHAR)

        if name not in self.__tclass_definitions:
            super().error(
                ErrorType.TYPE_ERROR,
                f"No template class named {name} found"
            )
        
        if tclass_string in self.__class_definitions:
            return self.__class_definitions[tclass_string]
        
        tclass_def = self.__tclass_definitions[name]
        tclass_instance_def = tclass_def.convert_to_class_def(tclass_string)
        tclass_instance_def.extract_field_and_method_defs()
        self.__class_definitions[tclass_string] = tclass_instance_def
        return tclass_instance_def

    def instantiate_class(self, class_name, line_num=None):
        # TODO: instantiate templated classes
        if InterpreterBase.TYPE_CONCAT_CHAR in class_name:
            class_def = self.get_tclass_def(class_name)
        else:
            class_def = self.get_class_def(class_name)
        
        ret = Object(self, class_def)
        if not ret.status.ok:
            ret.status.line_num = line_num
            super().error(*ret.status[1:])
        
        return ret

    def __define_class(self, parsed_class):
        if parsed_class[0] == InterpreterBase.TEMPLATE_CLASS_DEF:
            return

        if parsed_class[0] == InterpreterBase.CLASS_DEF:
            name = parsed_class[1]
            if name in self.__class_definitions:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Two or more definitions of class {name}",
                    parsed_class[0].line_num
                )
            
            self.__class_definitions[name] = ClassDef(parsed_class, self)

    def __define_tclass(self, parsed_tclass):
        if parsed_tclass[0] == InterpreterBase.CLASS_DEF:
            return

        if parsed_tclass[0] == InterpreterBase.TEMPLATE_CLASS_DEF:
            name = parsed_tclass[1]
            if name in self.__tclass_definitions:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Two or more definitions of template class {name}",
                    parsed_tclass[0].line_num
                )
            
            self.__tclass_definitions[name] = TClassDef(parsed_tclass, self)
            return
                
        super().error(
            ErrorType.SYNTAX_ERROR,
            f"Brewin++ expects only classes or templated classes to be defined at the outermost level, got {parsed_tclass[0]}",
            parsed_tclass[0].line_num
        )
