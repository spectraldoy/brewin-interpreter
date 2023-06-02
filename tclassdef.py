from intbase import InterpreterBase, ErrorType
from btypes import str_to_type, TClassRegistry
from classdef import ClassDef
from bparser import StringWithLineNumber

class TClassDef:
    """
    Class to store definitions of Brewin# templated classes
    """
    # TODO: static class definition cache?

    def __init__(self, tclass_def, interpreter_ref):
        self.name = tclass_def[1]
        self.type_params = tclass_def[2]
        self.tclass_body = tclass_def[3:]
        self.interpreter_ref = interpreter_ref

        # duplicate names
        if len(set(self.type_params)) != len(self.type_params):
            self.interpreter_ref.error(
                ErrorType.NAME_ERROR,
                f"Duplicate type parameter names in definition of templated class {self.name}",
                self.name.line_num
            )
        
        # register this templated class
        res = TClassRegistry.register(self.name, len(self.type_params))
        if not res.ok:
            res.line_num = tclass_def[0].line_num
            self.interpreter_ref.error(*res[1:])
    
    def convert_to_class_def(self, instantiated_type):
        _, *type_arguments = instantiated_type.split(InterpreterBase.TYPE_CONCAT_CHAR)

        if len(type_arguments) != len(self.type_params):
            self.interpreter_ref.error(
                ErrorType.TYPE_ERROR,
                f"Attempted to instantiate templated class {self.name} with wrong number of type arguments"
            )
        
        type_mapping = {}
        for type_param, type_arg_str in zip(self.type_params, type_arguments):
            type_arg_res = str_to_type(type_arg_str)
            if not type_arg_res.ok:
                self.interpreter_ref.error(
                    *type_arg_res[1:]
                )
            
            # from init, there should be no duplicate type_param names
            type_mapping[type_param] = str(type_arg_res.unwrap())

        new_class_def = [InterpreterBase.CLASS_DEF, instantiated_type]

        for member in self.tclass_body:
            match member[0]:
                case InterpreterBase.FIELD_DEF:
                    new_member = self.__concretize_templated_field_def(member, type_mapping)
                case InterpreterBase.METHOD_DEF:
                    new_member = self.__concretize_templated_method_def(member, type_mapping)
                case _:
                    self.interpreter_ref.error(
                        ErrorType.SYNTAX_ERROR,
                        f"Invalid keyword {member[0]} found in templated class {self.name}",
                        member[0].line_num
                    )
            
            new_class_def.append(new_member)
        
        return ClassDef(new_class_def, self.interpreter_ref)
    
    def __concretize_type_string(self, type_string, type_mapping, line_num=None):
        name, *type_args = type_string.split(InterpreterBase.TYPE_CONCAT_CHAR)
        # replace type params with type arguments from type_mapping
        type_args = [type_mapping[ta] if ta in type_mapping else ta for ta in type_args]
        name = type_mapping[name] if name in type_mapping else name
        concretized_type_string = InterpreterBase.TYPE_CONCAT_CHAR.join([name, *type_args])

        # using str_to_type to check validity of the type
        # rather than actually convert to the corresponding Type
        type_res = str_to_type(concretized_type_string)
        
        if not type_res.ok:
            type_res.line_num = line_num
            self.interpreter_ref.error(
                *type_res[1:]
            )
            
        return StringWithLineNumber(concretized_type_string, line_num)
        
    def __concretize_templated_field_def(self, field_def, type_mapping):
        new_typ = self.__concretize_type_string(field_def[1], type_mapping, field_def[0].line_num)

        # (field typ name) or (field typ name val)
        if len(field_def) == 4:
            new_val = self.__concretize_templated_expression(field_def[3], type_mapping)
            return [field_def[0], new_typ, field_def[2], new_val]
        
        return [field_def[0], new_typ, field_def[2]]
    
    def __concretize_templated_method_def(self, method_def, type_mapping):
        # (method type name (parameters) stmt)
        new_typ = self.__concretize_type_string(method_def[1], type_mapping, method_def[0].line_num)
        concretized_formal_params = []
        for formal_param_type, formal_param_name in method_def[3]:
            formal_param_type = self.__concretize_type_string(formal_param_type, type_mapping, method_def[0].line_num)
            concretized_formal_params.append([formal_param_type, formal_param_name])
        
        new_statement = self.__concretize_templated_statement(method_def[4], type_mapping)
        return [method_def[0], new_typ, method_def[2], concretized_formal_params, new_statement]
        

    def __concretize_templated_statement(self, statement, type_mapping):
        name = statement[0]
        match name:
            case InterpreterBase.BEGIN_DEF:
                return [name, *[
                    self.__concretize_templated_statement(stmt, type_mapping)
                    for stmt in statement[1:]
                ]]
            
            case InterpreterBase.SET_DEF:
                statement[2] = self.__concretize_templated_expression(statement[2], type_mapping)
                return statement
            
            case InterpreterBase.IF_DEF:
                cond = self.__concretize_templated_expression(statement[1], type_mapping)
                if_block = self.__concretize_templated_statement(statement[2], type_mapping)
                else_block = None if len(statement) != 4 else \
                    self.__concretize_templated_statement(statement[3], type_mapping)
                
                return [name, cond, if_block, else_block]

            case InterpreterBase.WHILE_DEF:
                return [
                    name,
                    self.__concretize_templated_expression(statement[1], type_mapping),
                    self.__concretize_templated_statement(statement[2], type_mapping)
                ]

            case InterpreterBase.CALL_DEF:
                calling_obj = self.__concretize_templated_expression(statement[1], type_mapping)
                args = [self.__concretize_templated_expression(arg, type_mapping) for arg in statement[3:]]
                return [name, calling_obj, statement[2], *args]

            case InterpreterBase.RETURN_DEF:
                if len(statement) == 1:
                    return statement
                return [name, self.__concretize_templated_expression(statement[1], type_mapping)]
            
            case InterpreterBase.INPUT_INT_DEF | InterpreterBase.INPUT_STRING_DEF:
                return statement
            
            case InterpreterBase.PRINT_DEF:
                return [name, *[
                    self.__concretize_templated_expression(stmt, type_mapping)
                    for stmt in statement[1:]
                ]]
            
            case InterpreterBase.LET_DEF:
                # (let (assignments) stmt1 stmt2)
                name, assignments, *statements = statement[1]
                concretized_assignments = []

                # replace type parameters in the assignments block of the let
                # with the type arguments from type_mapping
                for typ, *name_and_possibly_val in assignments:
                    typ = self.__concretize_type_string(typ, type_mapping, name.line_num)
                    concretized_assignments.append([typ, *name_and_possibly_val])
                
                concretized_statements = [
                    self.__concretize_templated_statement(stmt, type_mapping)
                    for stmt in statements
                ]

                return [name, concretized_assignments, *concretized_statements]

            case _:
                self.interpreter_ref.error(
                    ErrorType.SYNTAX_ERROR,
                    f"Undefined statement {name} in definition of {self.name}",
                    name.line_num
                )

    def __concretize_templated_expression(self, expr, type_mapping):
        if not isinstance(expr, list):
            return expr
        
        # otherwise, it's an operation with arguments
        op, *args = expr

        if op in self.interpreter_ref.binary_op_set | self.interpreter_ref.unary_op_set:
            args = [self.__concretize_templated_expression(arg, type_mapping) for arg in args]
            return [op, *args]

        if op == InterpreterBase.NEW_DEF:
            concretized_new_obj = self.__concretize_type_string(expr[1], type_mapping, op.line_num)
            return [op, concretized_new_obj]
        
        if op == InterpreterBase.CALL_DEF:
            # avoiding redundant code
            return self.__concretize_templated_statement(expr, type_mapping)

        # assume syntax errors will be handled during execution
        return expr
            
