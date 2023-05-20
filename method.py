from field import Field
from classdef import FieldDef
from btypes import str_to_type
from value import get_default_value_as_brewin_literal
from result import Result

class Method:
    def __init__(self, method_def):
        # indicates whether any error has occurred in defining this method
        self.status = Result.Ok()
        self.name = method_def.name
        self.statement = method_def.statement
        self.return_type = None
        self.params_as_fields = []

        # defines self.return_type
        self.__extract_return_type(method_def.return_type)
        # defines self.formal_param_fields, which define the function prototype / signature
        self.__extract_params_as_fields(method_def.formal_params)
    
    def matches_signature(self, argument_types):
        # whether or not this function can be called with the specified argument types
        if len(self.params_as_fields) != len(argument_types):
            return False

        for formal_param, arg_type in zip(self.params_as_fields, argument_types):
            if not formal_param.can_be_set_to(arg_type):
                return False

        return True

    def __extract_return_type(self, return_type):
        if not self.status.ok:
            return
        
        ret_type_res = str_to_type(return_type)
        if not ret_type_res.ok:
            self.status = ret_type_res
            self.status.line_num = return_type.line_num
            return
        
        self.return_type = ret_type_res.unwrap()
    
    def __extract_params_as_fields(self, formal_params):
        if not self.status.ok:
            return
        
        params_as_fields = []
        for param_type, param_name in formal_params:
            param_as_field_def = FieldDef(
                param_type,
                param_name,
                get_default_value_as_brewin_literal(param_type)
            )
            param_as_field = Field.from_field_def(param_as_field_def)
            if not param_as_field.status.ok:
                self.status = param_as_field.status
                return
            
            params_as_fields.append(param_as_field)
            
        
        self.params_as_fields = params_as_fields

