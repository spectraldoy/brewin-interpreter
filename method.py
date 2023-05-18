from field import Field
from classdef import FieldDef
from btypes import str_to_type
from value import get_default_value
from result import Result

class Method:
    def __init__(self, return_type, name, formal_params, statement):
        # indicates whether any error has occurred in defining this method
        # TODO: issue, I seriously dislike this
        self.status = Result.Ok()
        self.name = name
        self.statement = statement

        # defines self.return_type
        self.__extract_return_type(return_type)
        #defines self.formal_param_fields
        self.__extract_params_as_fields(formal_params)

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
                get_default_value(param_type)
            )
            param_as_field = Field(param_as_field_def)
            if not param_as_field.status.ok:
                self.status = param_as_field.status
                return
            
            params_as_fields.append(param_as_field)
            
        
        self.params_as_fields = params_as_fields
    
    # TODO: no need to implement a call method
    # TODO: handle that all in the object class - just get the statement out of the Method object
    # TODO: but still get an environment out of the Method class by copying and setting its params_as_fields
    # TODO: and then use that in the call function

