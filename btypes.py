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
    NULL = auto()
    NOTHING = auto()
    CLASS = auto()

    def __str__(self):
        match self:
            case Type.INT:
                return InterpreterBase.INT_DEF
            case Type.STRING:
                return InterpreterBase.STRING_DEF
            case Type.BOOL:
                return InterpreterBase.BOOL_DEF
            case Type.NULL:
                return InterpreterBase.NULL_DEF
            case Type.NOTHING:
                return InterpreterBase.NOTHING_DEF
            case Type.CLASS:
                return InterpreterBase.CLASS_DEF
            case _:
                return "unknown"

    def __repr__(self):
        return str(self)


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
    def get_super(cls, class_name):
        if not cls.defines(class_name):
            return Result.Err(ErrorType.TYPE_ERROR, f"No class named {class_name} found")
        
        return Result.Ok(cls.__register[class_name])

    @classmethod
    def get_all_supers(cls, class_name):
        if class_name == Type.NULL:
            return Result.Ok(cls.entries())

        res = cls.get_super(class_name)
        if not res.ok:
            return res
        
        if res.unwrap() is None:
            return Result.Ok(set())
        else:
            super_sups_res = cls.get_all_supers(res.unwrap())
            if not super_sups_res.ok:
                return super_sups_res
            
            return Result.Ok(set([res.unwrap()]) | super_sups_res.unwrap())
            
    @classmethod
    def register(cls, class_name, inherits):
        if cls.defines(class_name):
            return Result.Err(ErrorType.TYPE_ERROR, f"Attempted duplicate definition of type {class_name}")
        
        if not cls.defines(inherits):
            return Result.Err(ErrorType.TYPE_ERROR, f"Attempt to inherit from unknown type {inherits}")
        
        cls.__register[class_name] = inherits
        return Result.Ok()
    
    @classmethod
    def entries(cls):
        return set(cls.__register.keys())
    
    @classmethod
    def clear(cls):
        cls.__register = {
            Type.CLASS: None
        }
        return Result.Ok()



def str_to_type(string):
    match string:
        case InterpreterBase.INT_DEF:
            out = Type.INT
        case InterpreterBase.STRING_DEF:
            out = Type.STRING
        case InterpreterBase.BOOL_DEF:
            out = Type.BOOL
        case InterpreterBase.NULL_DEF:
            out = Type.NULL
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
