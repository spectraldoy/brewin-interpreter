from btypes import Type, TypeRegistry
from intbase import InterpreterBase, ErrorType

class FieldDef:
    """
    Stores code definitions of a field member of a class
    Type checking is performed in the Field class, which is used by Object
    These FieldDefs are translated into Fields on instantiation of a class
    """
    def __init__(self, typ, name, value):
        # ex: (field int nah 4)
        self.type = typ
        self.name = name
        self.value = value


class MethodDef:
    """
    Stores code definition of a method to run. 
    Type checking is performed in the Object class, which handles execution
    """
    def __init__(self, return_type, name, formal_params, statement):
        # ex: (method void main () (blah))
        self.return_type = return_type
        self.name = name
        self.formal_params = formal_params
        self.statement = statement


class ClassDef:
    """
    Class to store code definitions of classes used as blueprints to instantiate objects
    The act of defining a class registers a new Type in the type registry
    """
    def __init__(self, class_def, interpreter_ref):
        self.name = class_def[1]
        
        if class_def[2] == InterpreterBase.INHERITS_DEF:
            TypeRegistry.register(self.name, class_def[3])
            body_starts_at = 4
        else:
            TypeRegistry.register(self.name, Type.CLASS)
            body_starts_at = 2

        self.interpreter_ref = interpreter_ref
        self.__field_defs = {}
        self.__method_defs = {}

        self.__extract_field_and_method_defs(class_def[body_starts_at:])
    
    def __extract_field_and_method_defs(self, class_body):
        for member in class_body:
            if member[0] == InterpreterBase.FIELD_DEF:
                field_name = member[1]
                if field_name in self.__field_defs:
                    return self.interpreter_ref.error(
                        ErrorType.NAME_ERROR,
                        f"Two or more definitions of field {field_name}",
                        field_name.line_num
                    )
                
                self.__field_defs[field_name] = FieldDef(*member[1:])

            elif member[0] == InterpreterBase.METHOD_DEF:
                method_name = member[1]
                if method_name in self.__method_defs:
                    return self.interpreter_ref.error(
                        ErrorType.NAME_ERROR,
                        f"Two or more definitions of method {method_name}",
                        method_name.line_num
                    )

                self.__method_defs[method_name] = MethodDef(*member[1:])
            
            else:
                return self.interpreter_ref.error(
                    ErrorType.SYNTAX_ERROR,
                    f"Invalid keyword {member[0]} found in class {self.name}",
                    member[0].line_num
                )

