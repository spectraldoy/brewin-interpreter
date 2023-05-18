from value import Value, create_value
from utils import Result
from btypes import str_to_type, is_subclass_of
from intbase import ErrorType

class Field:
    def __init__(self, field_def):
        # indicates whether any error has occurred with this field
        self.status = Result.Ok()
        self.name = field_def.name
        # defines self.value
        self.__set_to_field_def(field_def.type, field_def.value)
  
    def __set_to_field_def(self, field_type, field_value):
        type_res = str_to_type(field_type)
        if not type_res.ok:
            self.status = type_res
            self.status.line_num = field_type.line_num
            return
        
        value_res = create_value(field_value)
        if not value_res.ok:
            self.status = value_res
            self.status.line_num = field_value.line_num
            return
        
        desired_type = type_res.unwrap()
        desired_value = value_res.unwrap()

        # TODO: just an equality check is not enough
        # TODO: we need to do the polymorphism search thing
        # TODO: should create a function for that
        if not is_subclass_of(desired_value.type, desired_type):
            self.status = Result.Err(
                ErrorType.TYPE_ERROR,
                f"Type mismatch in definition of field {self.name}: {field_value} is not of type {field_type}",
                field_value.line_num
            )
            return

        # stores a value along with its type
        self.value = desired_value
    
    def set_to_field(self, other):
        # set this field to be a copy of other, assuming other is a Field
        self.set_to_value(other.value)

    def set_to_value(self, value):
        # set this field to hold value, assuming value is a Value
        if not is_subclass_of(value.type, self.value.type):
            self.status = Result.Err(
                ErrorType.TYPE_ERROR,
                f"Type mismatch while setting {self.name}: {self.value} is not of type {value.type}"
            )
            return
        
        self.value.set(value)


