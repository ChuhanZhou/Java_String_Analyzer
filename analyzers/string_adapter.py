from typing import Optional, Union, Tuple
from .finite_height_string import StringAbstraction
from .bricks_string_analysis import BricksAbstractValue, BricksAnalysis
from .integrated_string import IntegratedStringValue

class StringOperations:
    MAX_LENGTH = 1000
    
    @staticmethod
    def length(val) -> Tuple[int, int]:
        if isinstance(val, IntegratedStringValue):
            return val.length()
        elif isinstance(val, BricksAbstractValue):
            min_len, max_len = val.length()
            if max_len is None:
                max_len = StringOperations.MAX_LENGTH
            return (min_len, max_len)
        elif isinstance(val, StringAbstraction):
            return val.length()
        else:
            return (0, StringOperations.MAX_LENGTH)
    
    @staticmethod
    def concat(val1, val2):
        if isinstance(val1, IntegratedStringValue) and isinstance(val2, IntegratedStringValue):
            return val1.concat(val2)
        elif isinstance(val1, IntegratedStringValue):
            # Type mismatch
            return IntegratedStringValue.top()
        elif isinstance(val1, BricksAbstractValue):
            if not isinstance(val2, BricksAbstractValue):
                return BricksAbstractValue.top()
            return BricksAnalysis.concat(val1, val2)
        elif isinstance(val1, StringAbstraction):
            if not isinstance(val2, StringAbstraction):
                return StringAbstraction.top()
            return val1.concat(val2)
        else:
            return StringAbstraction.top()
    
    @staticmethod
    def substring(val, start: int, end: Optional[int] = None):
        if isinstance(val, IntegratedStringValue):
            return val.substring(start, end)
        elif isinstance(val, BricksAbstractValue):
            if end is None:
                return BricksAbstractValue.top()
            return BricksAnalysis.substring(val, start, end)
        elif isinstance(val, StringAbstraction):
            return val.substring(start, end)
        else:
            return StringAbstraction.top()
    
    @staticmethod
    def startsWith(val, prefix: str) -> Optional[bool]:
        if isinstance(val, (StringAbstraction, BricksAbstractValue, IntegratedStringValue)):
            return val.startsWith(prefix)
        return None
    
    @staticmethod
    def endsWith(val, suffix: str) -> Optional[bool]:
        if isinstance(val, (StringAbstraction, BricksAbstractValue, IntegratedStringValue)):
            return val.endsWith(suffix)
        return None
    
    @staticmethod
    def equals(val1, val2) -> Optional[bool]:
        if isinstance(val1, IntegratedStringValue) and isinstance(val2, IntegratedStringValue):
            return val1.equals(val2)
        elif isinstance(val1, (StringAbstraction, BricksAbstractValue)):
            if isinstance(val2, (StringAbstraction, BricksAbstractValue)):
                if type(val1) == type(val2):
                    return val1.equals(val2)
        return None
    
    @staticmethod
    def isEmpty(val) -> Optional[bool]:
        if isinstance(val, (StringAbstraction, BricksAbstractValue, IntegratedStringValue)):
            return val.isEmpty()
        return None
    
    @staticmethod
    def contains(val, substring: str) -> Optional[bool]:
        if isinstance(val, IntegratedStringValue):
            return val.contains(substring)
        elif isinstance(val, BricksAbstractValue):
            return val.contains(substring)
        return None
    
    @staticmethod
    def is_definitely_null(val) -> bool:
        if isinstance(val, (StringAbstraction, BricksAbstractValue, IntegratedStringValue)):
            return val.is_definitely_null()
        return False
    
    @staticmethod
    def is_possibly_null(val) -> bool:
        if isinstance(val, (StringAbstraction, BricksAbstractValue, IntegratedStringValue)):
            return val.is_possibly_null()
        return False
    
    @staticmethod
    def is_definitely_not_null(val) -> bool:
        if isinstance(val, (StringAbstraction, BricksAbstractValue, IntegratedStringValue)):
            return val.is_definitely_not_null()
        return True
    
    @staticmethod
    def create_null(val):
        if isinstance(val, IntegratedStringValue):
            return IntegratedStringValue.null()
        elif isinstance(val, BricksAbstractValue):
            return BricksAbstractValue.null()
        else:
            return StringAbstraction.null()
    
    @staticmethod
    def set_not_null(val):
        if isinstance(val, IntegratedStringValue):
            return IntegratedStringValue(
                StringOperations.set_not_null(val.prefix),
                StringOperations.set_not_null(val.bricks)
            )
        elif isinstance(val, BricksAbstractValue):
            return BricksAbstractValue(val.bricks, can_be_null=False)
        elif isinstance(val, StringAbstraction):
            return StringAbstraction(
                val.prefixes, val.suffixes, val.min_len, val.max_len,
                can_be_null=False,
                max_prefix_depth=val.max_prefix_depth,
                max_length=val.max_length
            )
        return val
    
    @staticmethod
    def join(val1, val2):
        if isinstance(val1, IntegratedStringValue) and isinstance(val2, IntegratedStringValue):
            return val1.join(val2)
        elif isinstance(val1, BricksAbstractValue):
            if not isinstance(val2, BricksAbstractValue):
                return BricksAbstractValue.top()
            return BricksAnalysis.lub(val1, val2)
        elif isinstance(val1, StringAbstraction):
            if not isinstance(val2, StringAbstraction):
                return StringAbstraction.top()
            return val1.join(val2)
        return val2
    
    @staticmethod
    def widen(val_old, val_new):
        if isinstance(val_old, IntegratedStringValue) and isinstance(val_new, IntegratedStringValue):
            return val_old.widen(val_new)
        elif isinstance(val_old, BricksAbstractValue):
            if not isinstance(val_new, BricksAbstractValue):
                return BricksAbstractValue.top()
            return BricksAnalysis.widening(val_old, val_new)
        elif isinstance(val_old, StringAbstraction):
            if not isinstance(val_new, StringAbstraction):
                return StringAbstraction.top()
            return val_old.widen(val_new)
        return val_old