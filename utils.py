
class Result:
    def __init__(self, value=None, error=None, message=None, line_num=None):
        self.value = value
        # should be an instance of InterpreterBase.ErrorType or None
        self.error = error
        self.message = message
        self.line_num = line_num

    @classmethod
    def Ok(cls, value=None):
        return cls(value=value)
    
    @classmethod
    def Err(cls, error, message=None, line_num=None):
        return cls(error=error, message=message, line_num=line_num)
    
    @property
    def ok(self):
        return self.error is None
    
    def unwrap(self):
        # because I use the word value a lot everywhere this is
        return self.value
    
    def __getitem__(self, idx):
        # allow unpacking of result objects
        return [self.value, self.error, self.message, self.line_num][idx]
        
    def __str__(self):
        if self.error is None:
            return str(self.value)
        else:
            return str(self.error) + ": " + (str(self.message) if self.message else "")
    
    def __repr__(self):
        return str(self)

