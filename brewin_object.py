import copy
from env import LexicalEnvironment
from intbase import ErrorType, InterpreterBase
from value import Value, get_default_value_as_brewin_literal, create_value
from result import Result
from btypes import Type, TypeRegistry, is_subclass_of
from field import Field
from method import Method
from classdef import FieldDef
from bparser import StringWithLineNumber



class Object:
    STATUS_PROCEED = 0
    STATUS_RETURN = 1
    STATUS_EXCEPTION = 2

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
        # search for method in self; if not there, search super
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
        # create a new lexical environment for this method call,
        # when you call a method, it cannot see the variables outside its scope
        env = LexicalEnvironment()

        # assume arguments is a list of Field objects
        # also, when working with function params, need to perform type checking with the Values
        # the arguments hold, rather than the actual fields
        # NOTE: should I be using arg.value.type?
        argument_types = [arg.type for arg in arguments]

        # me should refer to the same object in derived classes
        if me_field is None:
            obj, method = self.get_method(method_name, argument_types, line_num_of_call)
            env.set(InterpreterBase.ME_DEF, Field.from_value(Value(self.name, self)))
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
                # pass everything else by value
                formal_param_field = copy.deepcopy(formal_param)
            
            # when working with function params, need to perform type checking with the Values
            # the arguments hold, rather than the actual fields
            # NOTE: should I be using set_to_value?
            formal_param_field.set_to_field(arg)
            if not formal_param_field.status.ok:
                self.interpreter_ref.error(
                    *formal_param_field.status[1:]
                )
            env.set(formal_param_name, formal_param_field)
        
        status, return_field = obj.__execute_statement(env, method.statement)

        # by default, return the default value for the return type
        ret = Field(method.return_type)

        # TODO: propagating exceptions upwards outside method calls?
        if status == Object.STATUS_EXCEPTION:
            return status, return_field

        if return_field.type == Type.NOTHING:
            return Object.STATUS_PROCEED, ret

        if status == Object.STATUS_RETURN:
            ret.set_to_field(return_field)
            # type check the return values
            if not is_subclass_of(return_field.type, method.return_type):
                self.interpreter_ref.error(
                    ErrorType.TYPE_ERROR,
                    f"Mismatched types: expected {method.return_type} but got {return_field.type}",
                    line_num_of_call
                )
            
            if not ret.status.ok:
                self.interpreter_ref.error(*ret.status[1:])
        
        return Object.STATUS_PROCEED, ret
    
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
            case InterpreterBase.THROW_DEF:
                return self.__execute_throw(env, statement)
            case InterpreterBase.TRY_DEF:
                return self.__execute_try(env, statement)
            case _:
                self.interpreter_ref.error(
                    ErrorType.SYNTAX_ERROR,
                    f"Attempt to execute undefined statement {name}",
                    name.line_num
                )

    def __execute_begin(self, env, code):
        for statement in code[1:]:
            status, return_field = self.__execute_statement(env, statement)
            if status == Object.STATUS_RETURN or status == Object.STATUS_EXCEPTION:
                return status, return_field
        
        return Object.STATUS_PROCEED, Field(Type.NOTHING)

    def __execute_set(self, env, code):
        # (set var expr)
        status, field = self.__evaluate_expression(env, code[2], code[0].line_num)

        if status == Object.STATUS_EXCEPTION:
            return status, field

        self.__execute_set_aux(env, code[1], field, code[0].line_num)
        return Object.STATUS_PROCEED, Field(Type.NOTHING)

    def __execute_if(self, env, code):
        condition = code[1]
        if_block = code[2]
        else_block = None if len(code) != 4 else code[3]

        status, evaluated_condition = self.__evaluate_expression(env, condition, code[0].line_num)

        if status == Object.STATUS_EXCEPTION:
            return status, evaluated_condition

        if evaluated_condition.type != Type.BOOL:
            self.interpreter_ref.error(
                ErrorType.TYPE_ERROR,
                f"Condition of {InterpreterBase.IF_DEF} did not evaluate to a {InterpreterBase.BOOL_DEF}",
                code[0].line_num
            )
        
        evaluated_condition = evaluated_condition.value.value
        if evaluated_condition:
            return self.__execute_statement(env, if_block)
        elif else_block is not None:
            return self.__execute_statement(env, else_block)
        
        return Object.STATUS_PROCEED, Field(Type.NOTHING)
    
    def __execute_while(self, env, code):
        # (while (cond) (statement))
        cond = code[1]
        statement = code[2]

        while True:
            status, evaluated_condition = self.__evaluate_expression(env, cond, code[0].line_num)

            if status == Object.STATUS_EXCEPTION:
                return status, evaluated_condition

            if evaluated_condition.type != Type.BOOL:
                self.interpreter_ref.error(
                    ErrorType.TYPE_ERROR,
                    f"Condition of {InterpreterBase.WHILE_DEF} did not evaluate to a {InterpreterBase.BOOL_DEF}",
                    code[0].line_num
                )
            
            # extract Value from Field, and value from Value
            proceed = evaluated_condition.value.value
            if not proceed:
                break

            status, return_field = self.__execute_statement(env, statement)
            if status == Object.STATUS_RETURN or status == Object.STATUS_EXCEPTION:
                return status, return_field

        return Object.STATUS_PROCEED, Field(Type.NOTHING)

    def __execute_call(self, env, code):
        return self.__execute_call_aux(env, code, code[0].line_num)

    def __execute_return(self, env, code):
        if len(code) == 1:
            # return with no expression
            out = Field(Type.NOTHING)
        else:
            status, out = self.__evaluate_expression(env, code[1], code[0].line_num)

            if status == Object.STATUS_EXCEPTION:
                return status, out

        return Object.STATUS_RETURN, out

    def __execute_inputi(self, env, code):
        var_name = code[1]
        inp = int(self.interpreter_ref.get_input())
        field = Field.from_value(Value(Type.INT, inp))
        self.__execute_set_aux(env, var_name, field, code[0].line_num)
        return Object.STATUS_PROCEED, Field(Type.NOTHING)
    
    def __execute_inputs(self, env, code):
        var_name = code[1]
        inp = self.interpreter_ref.get_input()
        field = Field.from_value(Value(Type.STRING, inp))
        self.__execute_set_aux(env, var_name, field, code[0].line_num)
        return Object.STATUS_PROCEED, Field(Type.NOTHING)

    def __execute_print(self, env, code):
        def convert_to_brewin_literal(val):
            if val.type == Type.BOOL:
                return InterpreterBase.TRUE_DEF if val.value.value else InterpreterBase.FALSE_DEF
            return str(val.value.value)

        evald_exprs = []
        for expr in code[1:]:
            status, evald_expr = self.__evaluate_expression(env, expr, code[0].line_num)

            if status == Object.STATUS_EXCEPTION:
                return status, evald_expr

            evald_exprs.append(evald_expr)

        output = "".join(map(convert_to_brewin_literal, evald_exprs))

        self.interpreter_ref.output(output)

        return Object.STATUS_PROCEED, Field(Type.NOTHING)

    def __execute_let(self, env, code):
        # (let ( (t1 p1) (t2 p2) ... )
        #   (stmt1) (stmt2) ... )
        let_kw, local_var_defs, *statements = code
        env = env.copy()

        # keep track of all the locals added
        # but don't use the env to allow shadowing
        new_local_names = set()

        # initialize all the locals and put them in the new env
        for local_var_def in local_var_defs:
            match local_var_def:
                case local_type, local_name:
                    local_type = local_var_def[0]
                    local_name = local_var_def[1]
                    local_initial_value = StringWithLineNumber(
                        get_default_value_as_brewin_literal(local_type), local_type.line_num)
                case _:
                    local_type, local_name, local_initial_value = local_var_def

            # check for duplicate definition of locals in the env
            if local_name in new_local_names:
                self.interpreter_ref.error(
                    ErrorType.NAME_ERROR,
                    f"Duplicate definition of local {local_name}",
                    let_kw.line_num
                )
            
            new_local_names.add(local_name)

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
            status, return_field = self.__execute_statement(env, statement)
            if status == Object.STATUS_RETURN or status == Object.STATUS_EXCEPTION:
                return status, return_field
        
        return Object.STATUS_PROCEED, Field(Type.NOTHING)

    def __execute_throw(self, env, code):
        message = code[1]

        status, evaluated_message = self.__evaluate_expression(env, message, code[0].line_num)

        if evaluated_message.type != Type.STRING:
            self.interpreter_ref.error(
                ErrorType.TYPE_ERROR,
                f"Message of {InterpreterBase.THROW_DEF} did not evaluate to a {InterpreterBase.STRING_DEF}",
                code[0].line_num
            )

        if status == Object.STATUS_EXCEPTION:
            return status, evaluated_message
        
        return Object.STATUS_EXCEPTION, evaluated_message

    def __execute_try(self, env, code):
        try_block = code[1]
        catch_block = code[2]

        # try the try block
        status, return_field = self.__execute_statement(env, try_block)
        
        # except a STATUS_EXCEPTION
        if status == Object.STATUS_EXCEPTION:
            env = env.copy()
            env.set(InterpreterBase.EXCEPTION_VARIABLE_DEF, return_field)
            status, return_field = self.__execute_statement(env, catch_block)
            
            if status == Object.STATUS_RETURN or status == Object.STATUS_EXCEPTION:
                return status, return_field

        elif status == Object.STATUS_RETURN:
            return status, return_field
        
        return Object.STATUS_PROCEED, Field(Type.NOTHING)

    def __evaluate_expression(self, env, expr, line_num_of_expr):
        # returns a status and Field
        # expressions can be brewin literals
        if not isinstance(expr, list):
            # environment shadows over fields
            env_res = env.get(expr)
            if env_res is not None:
                # note: env stores fields
                return Object.STATUS_PROCEED, env_res
            
            if expr in self.__fields:
                return Object.STATUS_PROCEED, self.__fields[expr]
         
            if expr == InterpreterBase.SUPER_DEF:
                if self.__super is not None:
                    return Object.STATUS_PROCEED, Field.from_value(Value(self.__super.name, self.__super), InterpreterBase.SUPER_DEF)
                
                self.interpreter_ref.error(
                    ErrorType.TYPE_ERROR,
                    f"Invalid call to {InterpreterBase.SUPER_DEF} object",
                    line_num_of_expr
                )
            
            val_res = create_value(expr)
            if not val_res.ok:
                val_res.line_num = line_num_of_expr
                self.interpreter_ref.error(*val_res[1:])
            
            val = val_res.unwrap()
            return Object.STATUS_PROCEED, Field.from_value(val)
        
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

            # check for errors in order of expressions evaluated
            # don't want to evaluate all expressions and *then* propagate errors
            stat1, operand1 = self.__evaluate_expression(env, args[0], line_num_of_expr)
            if stat1 == Object.STATUS_EXCEPTION:
                return stat1, operand1

            stat2, operand2 = self.__evaluate_expression(env, args[1], line_num_of_expr)
            if stat2 == Object.STATUS_EXCEPTION:
                return stat2, operand2

            # Object types can only be operated on if they are sub / super classes of each other
            if is_subclass_of(operand1.type, Type.CLASS) and is_subclass_of(operand2.type, Type.CLASS):
                if (is_subclass_of(operand1.value.type, operand2.value.type) or is_subclass_of(operand2.value.type, operand1.value.type)) and \
                    (is_subclass_of(operand1.type, operand2.type) or is_subclass_of(operand2.type, operand1.type)):
                    ret = self.interpreter_ref.binary_ops[Type.CLASS][operator](operand1.value, operand2.value)
                    return Object.STATUS_PROCEED, Field.from_value(ret)
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
            if operand1.type not in self.interpreter_ref.binary_ops or \
                operator not in self.interpreter_ref.binary_ops[operand1.type]:
                self.interpreter_ref.error(
                    ErrorType.TYPE_ERROR,
                    f"binary operator {operator} not defined for type {operand1.type}",
                    line_num_of_expr
                )
            
            ret = self.interpreter_ref.binary_ops[operand1.type][operator](operand1.value, operand2.value)
            return Object.STATUS_PROCEED, Field.from_value(ret)
        
        if operator in self.interpreter_ref.unary_op_set:
            if len(args) != 1:
                self.interpreter_ref.error(
                    ErrorType.SYNTAX_ERROR,
                    f"Invalid number of arguments to unary operator {operator}",
                    line_num_of_expr
                )

            status, operand = self.__evaluate_expression(env, args[0], line_num_of_expr)

            if status == Object.STATUS_EXCEPTION:
                return status, operand

            if operand.type not in self.interpreter_ref.unary_ops or \
                operator not in self.interpreter_ref.unary_ops[operand.type]:
                self.interpreter_ref.error(
                    ErrorType.TYPE_ERROR,
                    f"unary operator {operator} not defined for type {operand.type}",
                    line_num_of_expr
                )
            
            ret = self.interpreter_ref.unary_ops[operand.type][operator](operand.value)
            return Object.STATUS_PROCEED, Field.from_value(ret)

        if operator == InterpreterBase.NEW_DEF:
            if len(args) != 1:
                self.interpreter_ref.error(
                    ErrorType.SYNTAX_ERROR,
                    f"{InterpreterBase.NEW_DEF} expects only 1 argument but {len(args)} were given",
                    line_num_of_expr
                )
            # should also return a status and Field
            return Object.STATUS_PROCEED, self.__execute_new_aux(args[0], line_num_of_expr)

        if operator == InterpreterBase.CALL_DEF:
            # should also return a status and Field
            return self.__execute_call_aux(env, expr)

        self.interpreter_ref.error(
            ErrorType.SYNTAX_ERROR,
            "Something went wrong: probably a statement was used where there should have been an expression",
            line_num_of_expr
        )
    
    def __execute_set_aux(self, env, var_name, new_field, line_num):
        if new_field.type == Type.NOTHING or new_field.value.type == Type.NOTHING:
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
        
        field.set_to_field(new_field)
        if not field.status.ok:
            self.interpreter_ref.error(*field.status[1:])

    def __execute_new_aux(self, class_name, line_num_of_new=None):
        obj = self.interpreter_ref.instantiate_class(class_name, line_num_of_new)
        # the type of this value is the class's name
        return Field.from_value(Value(class_name, obj))

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
            me_field = Field.from_value(Value(obj.name, obj))
        else:
            # evaluate_expression returns a Value object: this gets the actual value out of it
            status, obj_field = self.__evaluate_expression(env, obj_name, line_num_of_call)

            if status == Object.STATUS_EXCEPTION:
                return status, obj_field

            if obj_field.value.is_null():
                self.interpreter_ref.error(
                    ErrorType.FAULT_ERROR,
                    f"Null dereference",
                    line_num_of_call
                )
            obj = obj_field.value.value
            me_field = None
            
        method_name, *args = expr[2:]
        args_as_fields = []
        for arg in args:
            status, evald_arg = self.__evaluate_expression(env, arg, line_num_of_call)

            if status == Object.STATUS_EXCEPTION:
                return status, evald_arg

            args_as_fields.append(evald_arg)

        return obj.execute_method(method_name, args_as_fields, line_num_of_call, me_field)

    def __instantiate_fields(self):
        for field_name, field_def in self.class_def.get_field_defs().items():
            self.__fields[field_name] = Field.from_field_def(field_def)
        
    def __instantiate_methods(self):
        for method_name, method_def in self.class_def.get_method_defs().items():
            self.__methods[method_name] = Method(method_def)
    
    def __possibly_instantiate_super(self):
        # assume existence checking has already been done in ClassDef
        superclass = TypeRegistry.get_super(self.name).unwrap()

        # if this class does in fact inherit from something
        if superclass != Type.CLASS:
            self.__super = self.interpreter_ref.instantiate_class(superclass)
        
