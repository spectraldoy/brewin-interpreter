from bparser import BParser
from intbase import InterpreterBase, ErrorType
from brewin_object import Object
from classdef import ClassDef

class Interpreter(InterpreterBase):
    
    def define_operations(self):
        # Valid Assumption: There will only be one instance of the Interpreter Class
        # any time this Brewin++ interpreter is run
        # don't make it more complicated than it needs to be
        pass

    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
        self.trace_output = trace_output
        self.main_object = None
        self.__class_definitions = {}
    
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
        self.main_object.execute_method(InterpreterBase.MAIN_FUNC_DEF)
        
    def get_class_def(self, class_name):
        if class_name not in self.__class_definitions:
            super().error(
                ErrorType.NAME_ERROR,
                f"No class named {class_name} found"
            )
        
        return self.__class_definitions[class_name]

    def instantiate_class(self, class_name):
        class_def = self.get_class_def(class_name)
        ret = Object(self, class_def)
        if not ret.status.ok:
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