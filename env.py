class LexicalEnvironment:
    """
    Class to maintain the Lexical Environment for method calls in Brewin++
    This is just a map between variable / field names and corresponding Value
    objects, which hold their actual value and type
    """

    def __init__(self, env=None):
        self.__environment = env if env is not None else {}
    
    def get(self, symbol):
        if symbol not in self.__environment:
            return None
        
        return self.__environment[symbol]
    
    def set(self, symbol, field):
        self.__environment[symbol] = field
    
    def pop(self, symbol):
        self.__environment.pop(symbol, None)
    
    def copy(self):
        new_env = self.__environment.copy()
        return LexicalEnvironment(new_env)

    
    def __contains__(self, symbol):
        return symbol in self.__environment
    

