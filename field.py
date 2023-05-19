from value import create_value
from result import Result
from btypes import str_to_type, is_subclass_of, Type
from intbase import ErrorType

class Field:
    def __init__(self, field_def):
        # indicates whether any error has occurred with this field
        self.status = Result.Ok()
        self.name = field_def.name
        # defines self.value and self.type
        self.__set_to_field_def(field_def.type, field_def.value)

    def __set_to_field_def(self, field_type, field_value):
        if not self.status.ok:
            return

        type_res = str_to_type(field_type)
        if not type_res.ok:
            self.status = type_res
            self.status.line_num = getattr(field_type, "line_num", None)
            return
        
        value_res = create_value(field_value)
        if not value_res.ok:
            self.status = value_res
            self.status.line_num = getattr(field_value, "line_num", None)
            return
        
        desired_type = type_res.unwrap()
        desired_value = value_res.unwrap()

        if not is_subclass_of(desired_value.type, desired_type):
            self.status = Result.Err(
                ErrorType.TYPE_ERROR,
                f"Type mismatch in definition of field {self.name}: {field_value} is not of type {field_type}",
                field_value.line_num
            )
            return

        # stores a value along with its type
        self.value = desired_value
        # but the type of a value can change so for static typing
        # we also need to store the desired_type of this field
        self.type = desired_type
    
    def set_to_field(self, other):
        # set this field to be a copy of other, assuming other is a Field
        self.set_to_value(other.value)

    def set_to_value(self, value):
        if not self.status.ok:
            return
        # set this field to hold value, assuming value is a Value
        if not is_subclass_of(value.type, self.type):
            self.status = Result.Err(
                ErrorType.TYPE_ERROR,
                f"Type mismatch while setting {self.name}: {self.value} is not of type {value.type}"
            )
            return
        
        # self.type does not change
        self.value.set(value)
    
    def can_be_set_to(self, typ):
        # whether or not this field can be set to a Value of type typ
        return is_subclass_of(typ, self.value.type)


