import copy
from env import LexicalEnvironment
from intbase import ErrorType, InterpreterBase
from value import Value, get_default_value
from result import Result
from btypes import Type, TypeRegistry, is_subclass_of
from field import Field
from method import Method


class Object:
    STATUS_PROCEED = 0
    STATUS_RETURN = 1
    STATUS_ERR = 2

    def __init__(self, interpreter_ref, class_def):
        self.interpreter_ref = interpreter_ref
        self.class_def = class_def
        self.name = class_def.name
        self.__fields = {}
        self.__methods = {}
        self.__super = None

        # populates self.__fields
        self.__instantiate_fields()
        # populates self.__methods
        self.__instantiate_methods()
        # defines self.__super to be an Object or leaves it as None
        self.__possibly_instantiate_super()
    
    @property
    def status(self):
        # a result indicating whether or not the fields and methods are instantiated / set correctly
        for field in self.__fields.values():
            if not field.status.ok:
                return field.status
        
        for method in self.__methods.values():
            if not method.status.ok:
                return method.status
        
        return Result.Ok()

    def get_method(self, method_name, argument_types, line_num_of_call=None):
        # search for 
        if method_name in self.__methods:
            method = self.__methods[method_name]
            if method.matches_signature(argument_types):
                return method
        elif self.__super is None:
            self.interpreter_ref.error(
                ErrorType.NAME_ERROR,
                f"Unknown method {method_name}",
                line_num_of_call
            )
        else:
            return self.__super.get_method(method_name, argument_types, line_num_of_call)

    def execute_method(self, method_name, arguments=[], line_num_of_call=None):
        # assume arguments is a list of Value objects
        argument_types = [arg.type for arg in arguments]
        method = self.get_method(method_name, argument_types, line_num_of_call)

        # create a new lexical environment for this method call
        # when you call a method, it cannot see the variables outside its scope
        env = LexicalEnvironment()

        for formal_param, arg in zip(method.params_as_fields, arguments):
            formal_param_name = formal_param.name
            if formal_param_name in env:
                self.interpreter_ref.error(
                    ErrorType.NAME_ERROR,
                    f"Duplicate formal parameter name {formal_param_name}",
                    formal_param_name.line_num
                )

            # create a copy of the method's field
            if is_subclass_of(formal_param.type, Type.CLASS):
                # pass objects by reference, not by value
                # TODO: check this works
                formal_param_field = formal_param
            else:
                formal_param_field = copy.deepcopy(formal_param)
            formal_param_field.set(arg)
            env.set(formal_param_name, formal_param_field)
        
        status, return_value = self.__execute_statement(env, method.statement)
        if status == Object.STATUS_RETURN:
            # type check the return values
            if is_subclass_of(return_value.type, method.return_type):
                return return_value
            
            self.interpreter_ref.error(
                ErrorType.TYPE_ERROR,
                f"Mismatched types: expected {method.return_type} but got {return_value.type}",
                line_num_of_call
            )
        
        # return the default value for the return type
        return get_default_value(method.return_type)

    def __execute_statement(self, env, statement):
        return Object.STATUS_PROCEED, get_default_value(Type.NOTHING)

    # TODO: call statement takes in a token specifying a name and uses an actual Object reference to call the method

    def __instantiate_fields(self):
        for field_name, field_def in self.class_def.get_field_defs().items():
            self.__fields[field_name] = Field(field_def)
        
    def __instantiate_methods(self):
        for method_name, method_def in self.class_def.get_method_defs().items():
            self.__methods[method_name] = Method(method_def)
    
    def __possibly_instantiate_super(self):
        # assume existence checking has already been done
        superclass = TypeRegistry.get_super(self.name).unwrap()

        # if this class does in fact inherit from something
        if superclass != Type.CLASS:
            self.__super = self.interpreter_ref.instantiate_class(superclass)
        
