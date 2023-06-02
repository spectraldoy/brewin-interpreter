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


class TClassRegistry:
    """
    Class for holding templated types defined using tclass
    These aren't actual types; but when instantiated with the correct number
    of type arguments, and with valid type arguments, they become types
    """
    # register: tcls -> number of type parameters to tcls
    __register = {}

    @classmethod
    def defines(cls, tclass_name):
        return tclass_name in cls.__register
    
    @classmethod
    def matches(cls, tclass_string):
        tclass_name, *type_args = tclass_string.split(InterpreterBase.TYPE_CONCAT_CHAR)
        return cls.defines(tclass_name) and cls.get_num_args(tclass_name).unwrap() == len(type_args)

    @classmethod
    def get_num_args(cls, tclass_name):
        if not cls.defines(tclass_name):
            return Result.Err(ErrorType.TYPE_ERROR, f"No templated class named {tclass_name} found")
        
        return Result.Ok(cls.__register[tclass_name])
    
    @classmethod
    def register(cls, tclass_name, num_args):
        if cls.defines(tclass_name):
            return Result.Err(ErrorType.TYPE_ERROR, f"Attempted duplicate definition of templated type {tclass_name}")
        
        cls.__register[tclass_name] = num_args
        return Result.Ok()
    
    @classmethod
    def entries(cls):
        return set(cls.__register.keys())
    
    @classmethod
    def clear(cls):
        cls.__register = {}
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
        case string if TClassRegistry.defines(string.split(InterpreterBase.TYPE_CONCAT_CHAR)[0]):
            name, *type_args = string.split(InterpreterBase.TYPE_CONCAT_CHAR)
            # definition checking is already done
            exp_num_args = TClassRegistry.get_num_args(name).unwrap()

            if len(type_args) != exp_num_args:
                return Result.Err(
                    ErrorType.TYPE_ERROR,
                    f"Expected {exp_num_args} type arguments to templated class {name} but got {len(type_args)}"
                )
            
            # NOTE: with recursion, this currently allows nesting of templated types, i.e.
            # bruh@bruh@int is valid, returning a bruh with a type arg of (bruh@int)
            # possibly problematic
            type_args_as_types = map(str_to_type, type_args)
            for type_arg_res in type_args_as_types:
                if not type_arg_res.ok:
                    return type_arg_res

            out = string

        case _:
            return Result.Err(ErrorType.TYPE_ERROR, f"Invalid type {string}") 
    
    return Result.Ok(out)


def is_subclass_of(typ1, typ2):
    # check if typ1 is a (non-strict) subclass of typ2
    if typ1 == typ2:
        return True
    
    # null is a subclass of all classes, including tclasses, but not primitive Types
    if typ1 == Type.NULL and (typ2 == Type.CLASS or not isinstance(typ2, Type)):
        return True
    
    elif not isinstance(typ1, Type) and TClassRegistry.matches(typ1):
        # no inheritance with templated classes
        supers_of_typ1 = {Type.CLASS}
    else:
        supers_of_typ1_res = TypeRegistry.get_all_supers(typ1)
        if not supers_of_typ1_res.ok:
            return False
        supers_of_typ1 = supers_of_typ1_res.unwrap()
    
    return typ2 in supers_of_typ1
