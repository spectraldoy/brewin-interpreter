from result import Result
from intbase import ErrorType

class LexicalEnvironment:
    """
    Class to maintain the Lexical Environment for method calls in Brewin++
    This is just a map between variable / field names and corresponding Value
    objects, which hold their actual value and type
    """

    def __init__(self):
        self.__environment = {}
    
    def get(self, symbol):
        if symbol not in self.__environment:
            return Result.Err(
                ErrorType.NAME_ERROR,
                f"Symbol {symbol} not found"
            )
        
        return Result.Ok(self.__environment[symbol])
    
    def set(self, symbol, field):
        # TODO: type checking on field
        self.__environment[symbol] = field
    
    def __contains__(self, symbol):
        return symbol in self.__environment
    

