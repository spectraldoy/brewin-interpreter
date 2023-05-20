import copy
from env import LexicalEnvironment
from intbase import ErrorType, InterpreterBase
from value import Value, get_default_value, create_value
from result import Result
from btypes import Type, TypeRegistry, is_subclass_of
from field import Field
from method import Method
from classdef import FieldDef

class Object:
    STATUS_PROCEED = 0
    STATUS_RETURN = 1

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
                return self, method
        
        if self.__super is None:
            self.interpreter_ref.error(
                ErrorType.NAME_ERROR,
                f"No method {method_name} matches the calling signature",
                line_num_of_call
            )
        
        # also returns the super object to call it from
        return self.__super.get_method(method_name, argument_types, line_num_of_call)

    def execute_method(self, method_name, arguments=[], line_num_of_call=None, me_field=None):
        # assume arguments is a list of Value objects
        argument_types = [arg.type for arg in arguments]

        # create a new lexical environment for this method call,
        # when you call a method, it cannot see the variables outside its scope
        env = LexicalEnvironment()

        # me should refer to the same object in derived classes
        if me_field is None:
            obj, method = self.get_method(method_name, argument_types, line_num_of_call)
            env.set(InterpreterBase.ME_DEF, Field(self.name, InterpreterBase.ME_DEF, Value(self.name, self)))
        else:
            obj, method = me_field.value.value.get_method(method_name, argument_types, line_num_of_call)
            env.set(InterpreterBase.ME_DEF, me_field)

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
                formal_param_field = formal_param
            else:
                formal_param_field = copy.deepcopy(formal_param)
            formal_param_field.set_to_value(arg)
            if not formal_param_field.status.ok:
                self.interpreter_ref.error(
                    *formal_param_field.status[1:]
                )
            env.set(formal_param_name, formal_param_field)
        
        status, return_value = obj.__execute_statement(env, method.statement)
        if status == Object.STATUS_RETURN:
            # type check the return values
            if is_subclass_of(return_value.type, method.return_type):
                return return_value
            
            if return_value.type != Type.NOTHING:
                self.interpreter_ref.error(
                    ErrorType.TYPE_ERROR,
                    f"Mismatched types: expected {method.return_type} but got {return_value.type}",
                    line_num_of_call
                )
        
        # return the default value for the return type
        return get_default_value(method.return_type)

    def __execute_statement(self, env, statement):
        name = statement[0]

        match name:
            case InterpreterBase.BEGIN_DEF:
                return self.__execute_begin(env, statement)
            case InterpreterBase.SET_DEF:
                return self.__execute_set(env, statement)
            case InterpreterBase.IF_DEF:
                return self.__execute_if(env, statement)
            case InterpreterBase.WHILE_DEF:
                return self.__execute_while(env, statement)
            case InterpreterBase.CALL_DEF:
                return self.__execute_call(env, statement)
            case InterpreterBase.RETURN_DEF:
                return self.__execute_return(env, statement)
            case InterpreterBase.INPUT_INT_DEF:
                return self.__execute_inputi(env, statement)
            case InterpreterBase.INPUT_STRING_DEF:
                return self.__execute_inputs(env, statement)
            case InterpreterBase.PRINT_DEF:
                return self.__execute_print(env, statement)
            case InterpreterBase.LET_DEF:
                return self.__execute_let(env, statement)
            case _:
                self.interpreter_ref.error(
                    ErrorType.SYNTAX_ERROR,
                    f"Attempt to execute undefined statement {name}",
                    name.line_num
                )

    def __execute_begin(self, env, code):
        for statement in code[1:]:
            status, return_value = self.__execute_statement(env, statement)
            if status == Object.STATUS_RETURN:
                return status, return_value
        
        return Object.STATUS_PROCEED, Value(Type.NOTHING)

    def __execute_set(self, env, code):
        # (set var (expr))
        val = self.__evaluate_expression(env, code[2], code[0].line_num)
        self.__execute_set_aux(env, code[1], val, code[0].line_num)
        return Object.STATUS_PROCEED, Value(Type.NOTHING)

    def __execute_if(self, env, code):
        condition = code[1]
        if_block = code[2]
        else_block = None if len(code) != 4 else code[3]

        evaluated_condition = self.__evaluate_expression(env, condition, code[0].line_num)
        if evaluated_condition.type != Type.BOOL:
            self.interpreter_ref.error(
                ErrorType.TYPE_ERROR,
                f"Condition of {InterpreterBase.IF_DEF} did not evaluate to a {InterpreterBase.BOOL_DEF}",
                code[0].line_num
            )
        
        evaluated_condition = evaluated_condition.value
        if evaluated_condition:
            return self.__execute_statement(env, if_block)
        elif else_block is not None:
            return self.__execute_statement(env, else_block)
        
        return Object.STATUS_PROCEED, Value(Type.NOTHING)
    
    def __execute_while(self, env, code):
        # (while (cond) (statement))
        cond = code[1]
        statement = code[2]

        while True:
            evaluated_condition = self.__evaluate_expression(env, cond, code[0].line_num)
            if evaluated_condition.type != Type.BOOL:
                self.interpreter_ref.error(
                    ErrorType.TYPE_ERROR,
                    f"Condition of {InterpreterBase.WHILE_DEF} did not evaluate to a {InterpreterBase.BOOL_DEF}",
                    code[0].line_num
                )
            
            proceed = evaluated_condition.value
            if not proceed:
                break

            status, return_value = self.__execute_statement(env, statement)
            if status == Object.STATUS_RETURN:
                return status, return_value

        return Object.STATUS_PROCEED, Value(Type.NOTHING)

    def __execute_call(self, env, code):
        return Object.STATUS_PROCEED, self.__execute_call_aux(env, code, code[0].line_num)

    def __execute_return(self, env, code):
        if len(code) == 1:
            # return with no expression
            out = Value(Type.NOTHING)
        else:
            out = self.__evaluate_expression(env, code[1], code[0].line_num)

        return Object.STATUS_RETURN, out

    def __execute_inputi(self, env, code):
        var_name = code[1]
        inp = int(self.interpreter_ref.get_input())
        val = Value(Type.INT, inp)
        self.__execute_set_aux(env, var_name, val, code[0].line_num)
        return Object.STATUS_PROCEED, Value(Type.NOTHING)

    def __execute_inputs(self, env, code):
        var_name = code[1]
        inp = self.interpreter_ref.get_input()
        val = Value(Type.STRING, inp)
        self.__execute_set_aux(env, var_name, val, code[0].line_num)
        return Object.STATUS_PROCEED, Value(Type.NOTHING)

    def __execute_print(self, env, code):
        def convert_to_brewin_literal(val):
            if val.type == Type.BOOL:
                return InterpreterBase.TRUE_DEF if val.value else InterpreterBase.FALSE_DEF
            return str(val.value)

        evald_exprs = [self.__evaluate_expression(env, expr, code[0].line_num) for expr in code[1:]]
        output = "".join(map(convert_to_brewin_literal, evald_exprs))

        self.interpreter_ref.output(output)

        return Object.STATUS_PROCEED, Value(Type.NOTHING)

    def __execute_let(self, env, code):
        # (let ( (t1 p1) (t2 p2) ... )
        #   (stmt1) (stmt2) ... )
        let_kw, local_var_defs, *statements = code
        env = env.copy()

        # initialize all the locals and put them in the new env
        for local_type, local_name, local_initial_value in local_var_defs:
            # locals shadow over env and self.fields
            local_as_field_def = FieldDef(
                local_type,
                local_name,
                local_initial_value
            )

            # local variables must have an initial value specified
            # and in Barista, they cannot be initialized with values of class fields
            local_field = Field.from_field_def(local_as_field_def)
            if not local_field.status.ok:
                local_field.status.line_num = let_kw.line_num
                self.interpreter_ref.error(*local_field.status[1:])
            
            env.set(local_name, local_field)
        
        # execute the statements
        for statement in statements:
            status, return_value = self.__execute_statement(env, statement)
            if status == Object.STATUS_RETURN:
                return status, return_value
        
        return Object.STATUS_PROCEED, Value(Type.NOTHING)

    def __evaluate_expression(self, env, expr, line_num_of_expr):
        # expressions can be brewin literals
        if not isinstance(expr, list):
            # environment shadows over fields
            env_res = env.get(expr)
            if env_res is not None:
                # the env stores field: get the Value out
                return env_res.value
            
            if expr in self.__fields:
                # get the Value object out of the field
                return self.__fields[expr].value
         
            if expr == InterpreterBase.SUPER_DEF:
                if self.__super is not None:
                    return self.__super
                
                self.interpreter_ref.error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid call to {InterpreterBase.SUPER_DEF} object",
                    line_num_of_expr
                )
            
            val_res = create_value(expr)
            if not val_res.ok:
                val_res.line_num = line_num_of_expr
                self.interpreter_ref.error(*val_res[1:])
            
            return val_res.unwrap()
        
        # otherwise an expression is an operator with arguments
        operator, *args = expr

        # evaluate the expression only if the operator expects it
        if operator in self.interpreter_ref.binary_op_set:
            if len(args) != 2:
                self.interpreter_ref.error(
                    ErrorType.SYNTAX_ERROR,
                    f"Invalid number of arguments to binary operator {operator}",
                    line_num_of_expr
                )
            
            operand1, operand2 = [self.__evaluate_expression(env, arg, line_num_of_expr) for arg in args]

            # Object types can only be operated on if they are sub / super classes of each other
            if is_subclass_of(operand1.type, Type.CLASS) and is_subclass_of(operand2.type, Type.CLASS):
                if is_subclass_of(operand1.type, operand2.type) or is_subclass_of(operand2.type, operand1.type):
                    return self.interpreter_ref.binary_ops[Type.CLASS][operator](operand1, operand2)
                else:
                    self.interpreter_ref.error(
                        ErrorType.TYPE_ERROR,
                        f"Cannot perform {operator} on unrelated object types {operand1.type} and {operand2.type}",
                        line_num_of_expr
                    )

            if operand1.type != operand2.type:
                self.interpreter_ref.error(
                    ErrorType.TYPE_ERROR,
                    f"{operator} attempted on incompatible types {operand1.type} and {operand2.type}",
                    line_num_of_expr
                )

            # by this point, operand1.type == operand2.type
            if operand1.type not in self.interpreter_ref.binary_ops:
                self.interpreter_ref.error(
                    ErrorType.TYPE_ERROR,
                    f"binary operator {operator} not defined for type {operand1.type}",
                    line_num_of_expr
                )
            
            return self.interpreter_ref.binary_ops[operand1.type][operator](operand1, operand2)
        
        if operator in self.interpreter_ref.unary_op_set:
            if len(args) != 1:
                self.interpreter_ref.error(
                    ErrorType.SYNTAX_ERROR,
                    f"Invalid number of arguments to unary operator {operator}",
                    line_num_of_expr
                )

            operand = self.__evaluate_expression(env, args[0], line_num_of_expr)
            if operand.type not in self.interpreter_ref.unary_ops:
                self.interpreter_ref.error(
                    ErrorType.TYPE_ERROR,
                    f"unary operator {operator} not defined for type {operand.type}",
                    line_num_of_expr
                )
            
            return self.interpreter_ref.unary_ops[operand.type][operator](operand)

        if operator == InterpreterBase.NEW_DEF:
            if len(args) != 1:
                self.interpreter_ref.error(
                    ErrorType.SYNTAX_ERROR,
                    f"{InterpreterBase.NEW_DEF} expects only 1 argument but {len(args)} were given",
                    line_num_of_expr
                )
            return self.__execute_new_aux(args[0], line_num_of_expr)

        if operator == InterpreterBase.CALL_DEF:
            return self.__execute_call_aux(env, expr)

        self.interpreter_ref.error(
            ErrorType.SYNTAX_ERROR,
            "Something went wrong: probably a statement was used where there should have been an expression",
            line_num_of_expr
        )
    
    def __execute_set_aux(self, env, var_name, val, line_num):
        if val.type == Type.NOTHING:
            self.interpreter_ref.error(
                ErrorType.TYPE_ERROR,
                f"Attempt to assign a field to {InterpreterBase.NOTHING_DEF}",
                line_num
            )

        # env shadows over fields
        if var_name in env:
            field = env.get(var_name)
        elif var_name in self.__fields:
            field = self.__fields[var_name]
        else:
            self.interpreter_ref.error(
                ErrorType.NAME_ERROR,
                f"Attempt to set unknown field {var_name}",
                line_num
            )
        
        field.set_to_value(val)
        if not field.status.ok:
            self.interpreter_ref.error(*field.status[1:])

    def __execute_new_aux(self, class_name, line_num_of_new=None):
        obj = self.interpreter_ref.instantiate_class(class_name, line_num_of_new)
        # the type of this value is the class's name
        return Value(class_name, obj)

    def __execute_call_aux(self, env, expr, line_num_of_call=None):
        # expr is (call obj method arg1 arg2 ...)
        obj_name = expr[1]

        if obj_name == InterpreterBase.ME_DEF:
            obj = self
            me_field = env.get(InterpreterBase.ME_DEF)
        elif obj_name == InterpreterBase.SUPER_DEF:
            if self.__super is None:
                self.interpreter_ref.error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid call to super from class {self.name}",
                    line_num_of_call
                )
            obj = self.__super
            me_field = Field(obj.name, InterpreterBase.ME_DEF, Value(self.__super.name, obj))
        else:
            # evaluate_expression returns a Value object: this gets the actual value out of it
            obj = self.__evaluate_expression(env, obj_name, line_num_of_call)
            if obj.is_null():
                self.interpreter_ref.error(
                    ErrorType.FAULT_ERROR,
                    f"Null dereference",
                    line_num_of_call
                )
            obj = obj.value
            me_field = None
            
        method_name, *args = expr[2:]
        args_as_values = [self.__evaluate_expression(env, arg, line_num_of_call) for arg in args]

        return obj.execute_method(method_name, args_as_values, line_num_of_call, me_field)

    def __instantiate_fields(self):
        for field_name, field_def in self.class_def.get_field_defs().items():
            self.__fields[field_name] = Field.from_field_def(field_def)
        
    def __instantiate_methods(self):
        for method_name, method_def in self.class_def.get_method_defs().items():
            self.__methods[method_name] = Method(method_def)
    
    def __possibly_instantiate_super(self):
        # assume existence checking has already been done
        superclass = TypeRegistry.get_super(self.name).unwrap()

        # if this class does in fact inherit from something
        if superclass != Type.CLASS:
            self.__super = self.interpreter_ref.instantiate_class(superclass)
        
