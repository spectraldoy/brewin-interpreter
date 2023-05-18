from intbase import InterpreterBase, ErrorType
from utils import Result
from btypes import Type, TypeRegistry


class Value:
    """
    Class to store a value and its type. Type checking is not performed
    here as it is trivial that values are, semantically speaking, statically typed.
    To implement the static typing requirements of Brewin++, Fields must do some
    type checking.
    """
    def __init__(self, value_type, initial_value=None):
        # self.__type is either in the Type enum, or in the TypeRegistry
        self.__type = value_type
        self.__value = initial_value
    
    @property
    def type(self):
        return self.__type
    
    @property
    def value(self):
        return self.__value
    
    def __repr__(self):
        return str(self.__value)

    def set(self, new_value):
        self.__type = new_value.type
        self.__value = new_value.value


def create_value(val):
    if val == "true":
        out = Value(Type.BOOL, True)
    elif val == "false":
        out = Value(Type.BOOL, False)
    elif isinstance(val, str) and val[0] == '"':
        out = Value(Type.STRING, val.strip('"'))
    elif isinstance(val, str) and val.lstrip("-").isnumeric():
        out = Value(Type.INT, int(val))
    elif val == InterpreterBase.NULL_DEF:
        out = Value(Type.CLASS, None)
    elif val == InterpreterBase.NOTHING_DEF:
        out = Value(Type.NOTHING)
    else:
        return Result.Err(ErrorType.NAME_ERROR, f"Invalid value {val}")
    
    return Result.Ok(out)


def get_default_value(typ):
    match typ:
        case Type.INT:
            out = Value(Type.INT, 0)
        case Type.STRING:
            out = Value(Type.STRING, "")
        case Type.BOOL:
            out = Value(Type.BOOL, False)
        case Type.NOTHING:
            out = Value(Type.NOTHING, None)
        case typ if TypeRegistry.defines(typ):
            out = Value(Type.CLASS, None) # null by default for Type.CLASS and all classes
        case _:
            return Result.Err(ErrorType.TYPE_ERROR, f"No class named {typ} found")
    
    return Result.Ok(out)

