from env import LexicalEnvironment
from intbase import ErrorType, InterpreterBase
from value import Value
from result import Result
from btypes import TypeRegistry


class Object:
    # TODO: expressions should be static variables of the Interpreter class

    def __init__(self, interpreter_ref, class_def):
        self.interpreter_ref = interpreter_ref
        self.class_def = class_def

        # self.__instantiate_fields()
        # self.__instantiate_methods()
        # self.__possibly_instantiate_super()

    def execute_method(self, *args):
        pass
