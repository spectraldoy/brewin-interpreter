from enum import Enum, auto
from result import Result
from intbase import InterpreterBase, ErrorType

class Type(Enum):
    """
    Enum for possible Brewin++ types
    """
    INT = auto()
    STRING = auto()
    BOOL = auto()
    NOTHING = auto()
    CLASS = auto()


class TypeRegistry:
    """
    Class for holding types defined by creating custom Brewin classes
    """
    # register: subcls -> direct superclass of subcls
    # Brewin++ does not support multiple inheritance
    __register = {
        Type.CLASS: None
    }

    @classmethod
    def defines(cls, class_name):
        return class_name in cls.__register
    
    @classmethod
    def get(cls, class_name):
        if not cls.defines(class_name):
            return Result.Err(ErrorType.TYPE_ERROR, f"No class named {class_name} found")
        
        return Result.Ok(cls.__register[class_name])

    @classmethod
    def get_all_supers(cls, class_name):
        res = cls.get(class_name)
        if not res.ok:
            return res
        
        if res.unwrap() is None:
            return Result.Ok(set())
        else:
            super_sups_res = cls.get_all_supers(res.unwrap())
            if not super_sups_res.ok:
                return super_sups_res
            
            return Result.Ok(set([res]) | super_sups_res.unwrap())
            
    @classmethod
    def register(cls, class_name, inherits):
        if cls.defines(class_name):
            return Result.Err(ErrorType.TYPE_ERROR, f"Attempted duplicate definition of class {class_name}")
        
        cls.__register[class_name] = inherits
        return Result.Ok()


def str_to_type(string):
    match string:
        case InterpreterBase.INT_DEF:
            out = Type.INT
        case InterpreterBase.STRING_DEF:
            out = Type.STRING
        case InterpreterBase.BOOL_DEF:
            out = Type.BOOL
        case InterpreterBase.VOID_DEF:
            out = Type.NOTHING
        case string if TypeRegistry.defines(string):
            out = string
        case _:
            return Result.Err(ErrorType.TYPE_ERROR, f"Invalid type {string}") 
    
    return Result.Ok(out)


def is_subclass_of(typ1, typ2):
    # check if typ1 is a (non-strict) subclass of typ2
    if typ1 == typ2:
        return True
    
    supers_of_typ1_res = TypeRegistry.get_all_supers(typ1)
    if not supers_of_typ1_res.ok:
        return False
    
    return typ2 in supers_of_typ1_res.unwrap()
