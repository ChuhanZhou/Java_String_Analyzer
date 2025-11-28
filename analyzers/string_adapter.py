from typing import Optional, Union, Tuple
from .finite_height_string import StringAbstraction
from .bricks_string_analysis import BricksAbstractValue, BricksAnalysis

class StringOperations:
    MAX_LENGTH = 1000
    
    @staticmethod
    def length(val) -> Tuple[int, int]:
        if not isinstance(val, (StringAbstraction, BricksAbstractValue)):
            return (0, StringOperations.MAX_LENGTH)
        
        min_len, max_len = val.length()
        
        if max_len is None:
            max_len = StringOperations.MAX_LENGTH
        
        return (min_len, max_len)
    
    @staticmethod
    def concat(val1, val2):
        if not isinstance(val1, (StringAbstraction, BricksAbstractValue)):
            if isinstance(val2, BricksAbstractValue):
                return BricksAbstractValue.top()
            return StringAbstraction.top()
        
        if not isinstance(val2, (StringAbstraction, BricksAbstractValue)):
            if isinstance(val1, BricksAbstractValue):
                return BricksAbstractValue.top()
            return StringAbstraction.top()
        
        if isinstance(val1, BricksAbstractValue):
            return BricksAnalysis.concat(val1, val2)
        return val1.concat(val2)
    
    @staticmethod
    def substring(val, start: int, end: Optional[int] = None):
        if not isinstance(val, (StringAbstraction, BricksAbstractValue)):
            return StringAbstraction.top()
        
        if isinstance(val, BricksAbstractValue):
            if end is None:
                return BricksAbstractValue.top()
            return BricksAnalysis.substring(val, start, end)
        return val.substring(start, end)
    
    @staticmethod
    def startsWith(val, prefix: str) -> Optional[bool]:
        if not isinstance(val, (StringAbstraction, BricksAbstractValue)):
            return None
        return val.startsWith(prefix)
    
    @staticmethod
    def endsWith(val, suffix: str) -> Optional[bool]:
        if not isinstance(val, (StringAbstraction, BricksAbstractValue)):
            return None
        return val.endsWith(suffix)
    
    @staticmethod
    def equals(val1, val2) -> Optional[bool]:
        if not isinstance(val1, (StringAbstraction, BricksAbstractValue)):
            return None
        if not isinstance(val2, (StringAbstraction, BricksAbstractValue)):
            return None
        
        if isinstance(val1, BricksAbstractValue):
            return val1.equals(val2)
        return val1.equals(val2)
    
    @staticmethod
    def isEmpty(val) -> Optional[bool]:
        if not isinstance(val, (StringAbstraction, BricksAbstractValue)):
            return None
        return val.isEmpty()
    
    @staticmethod
    def contains(val, substring: str) -> Optional[bool]:
        if not isinstance(val, (StringAbstraction, BricksAbstractValue)):
            return None
        
        if isinstance(val, BricksAbstractValue):
            return val.contains(substring)
        return None
    
    @staticmethod
    def is_definitely_null(val) -> bool:
        if not isinstance(val, (StringAbstraction, BricksAbstractValue)):
            return False
        return val.is_definitely_null()
    
    @staticmethod
    def is_possibly_null(val) -> bool:
        if not isinstance(val, (StringAbstraction, BricksAbstractValue)):
            return False
        return val.is_possibly_null()
    
    @staticmethod
    def is_definitely_not_null(val) -> bool:
        if not isinstance(val, (StringAbstraction, BricksAbstractValue)):
            return True  # 非字符串类型不会是 null
        return val.is_definitely_not_null()
    
    @staticmethod
    def create_null(val):
        if isinstance(val, BricksAbstractValue):
            return BricksAbstractValue.null()
        else:
            return StringAbstraction.null()
    
    @staticmethod
    def set_not_null(val):
        if isinstance(val, BricksAbstractValue):
            return BricksAbstractValue(
                val.bricks,
                can_be_null=False
            )
        elif isinstance(val, StringAbstraction):
            return StringAbstraction(
                val.prefixes, 
                val.suffixes,
                val.min_len, 
                val.max_len,
                can_be_null=False,
                max_prefix_depth=val.max_prefix_depth,
                max_length=val.max_length
            )
        else:
            return val
    
    @staticmethod
    def join(val1, val2):
        if not isinstance(val1, (StringAbstraction, BricksAbstractValue)):
            return val2
        if not isinstance(val2, (StringAbstraction, BricksAbstractValue)):
            return val1
        
        if isinstance(val1, BricksAbstractValue):
            return BricksAnalysis.lub(val1, val2)
        return val1.join(val2)
    
    @staticmethod
    def widen(val_old, val_new):
        if not isinstance(val_old, (StringAbstraction, BricksAbstractValue)):
            return val_new
        if not isinstance(val_new, (StringAbstraction, BricksAbstractValue)):
            return val_old
        
        if isinstance(val_old, BricksAbstractValue):
            return BricksAnalysis.widening(val_old, val_new)
        return val_old.widen(val_new)