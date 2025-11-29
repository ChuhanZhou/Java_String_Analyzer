from typing import Tuple, Optional
from .finite_height_string import StringAbstraction
from .bricks_string_analysis import BricksAbstractValue, BricksAnalysis


class IntegratedStringValue:  
    def __init__(self, prefix_val: StringAbstraction, bricks_val: BricksAbstractValue):
        self.prefix = prefix_val
        self.bricks = bricks_val
    
    @staticmethod
    def top():
        return IntegratedStringValue(
            StringAbstraction.top(),
            BricksAbstractValue.top()
        )
    
    @staticmethod
    def from_string(s: str):
        return IntegratedStringValue(
            StringAbstraction.from_string(s),
            BricksAbstractValue.from_string(s)
        )
    
    @staticmethod
    def null():
        return IntegratedStringValue(
            StringAbstraction.null(),
            BricksAbstractValue.null()
        )
    
    def length(self) -> Tuple[int, int]:
        prefix_min, prefix_max = self.prefix.length()
        bricks_min, bricks_max_opt = self.bricks.length()
        bricks_max = bricks_max_opt if bricks_max_opt is not None else 1000
        
        min_len = min(prefix_min, bricks_min)
        max_len = max(prefix_max, bricks_max)
        
        return (min_len, max_len)
    
    def concat(self, other: 'IntegratedStringValue') -> 'IntegratedStringValue':
        return IntegratedStringValue(
            self.prefix.concat(other.prefix),
            BricksAnalysis.concat(self.bricks, other.bricks)
        )
    
    def substring(self, start: int, end: Optional[int] = None) -> 'IntegratedStringValue':
        if end is None:
            prefix_result = self.prefix.substring(start, end)
            # Bricks doesn't support single parameter well, use TOP
            bricks_result = BricksAbstractValue([
                BricksAbstractValue.Brick(frozenset(['.*']), 0, -1)
            ], can_be_null=False)
        else:
            prefix_result = self.prefix.substring(start, end)
            bricks_result = BricksAnalysis.substring(self.bricks, start, end)
        
        return IntegratedStringValue(prefix_result, bricks_result)
    
    def startsWith(self, prefix_str: str) -> Optional[bool]:
        prefix_result = self.prefix.startsWith(prefix_str)
        bricks_result = self.bricks.startsWith(prefix_str)
        
        # Both agree on True
        if prefix_result is True and bricks_result is True:
            return True
        
        # Both agree on False
        if prefix_result is False and bricks_result is False:
            return False
        
        if prefix_result == bricks_result:
            return prefix_result
        if prefix_result is None:
            return bricks_result
        if bricks_result is None:
            return prefix_result
        
        # Disagreement or uncertainty
        return None
    
    def endsWith(self, suffix_str: str) -> Optional[bool]:
        prefix_result = self.prefix.endsWith(suffix_str)
        bricks_result = self.bricks.endsWith(suffix_str)
        
        if prefix_result is True and bricks_result is True:
            return True
        if prefix_result is False and bricks_result is False:
            return False
        
        if prefix_result == bricks_result:
            return prefix_result
        if prefix_result is None:
            return bricks_result
        if bricks_result is None:
            return prefix_result
        return None
    
    def equals(self, other: 'IntegratedStringValue') -> Optional[bool]:
        prefix_result = self.prefix.equals(other.prefix)
        bricks_result = self.bricks.equals(other.bricks)

        if prefix_result == bricks_result:
            return prefix_result
        if prefix_result is None:
            return bricks_result
        if bricks_result is None:
            return prefix_result
        
        if prefix_result is True and bricks_result is True:
            return True
        if prefix_result is False and bricks_result is False:
            return False
        if prefix_result == True or bricks_result == True:
            return True
        else:
            return False
        
    
    def isEmpty(self) -> Optional[bool]:
        prefix_result = self.prefix.isEmpty()
        bricks_result = self.bricks.isEmpty()
        
        if prefix_result is True and bricks_result is True:
            return True
        if prefix_result is False and bricks_result is False:
            return False
        
        if prefix_result == bricks_result:
            return prefix_result
        if prefix_result is None:
            return bricks_result
        if bricks_result is None:
            return prefix_result
        return None
    
    def contains(self, substring: str) -> Optional[bool]:
        return self.bricks.contains(substring)
    
    def is_definitely_null(self) -> bool:
        return self.prefix.is_definitely_null() and self.bricks.is_definitely_null()
    
    def is_possibly_null(self) -> bool:
        return self.prefix.is_possibly_null() and self.bricks.is_possibly_null()
    
    def is_definitely_not_null(self) -> bool:
        return self.prefix.is_definitely_not_null() and self.bricks.is_definitely_not_null()
    
    def join(self, other: 'IntegratedStringValue') -> 'IntegratedStringValue':
        return IntegratedStringValue(
            self.prefix.join(other.prefix),
            BricksAnalysis.lub(self.bricks, other.bricks)
        )
    
    def widen(self, other: 'IntegratedStringValue') -> 'IntegratedStringValue':
        """Widening operation"""
        return IntegratedStringValue(
            self.prefix.widen(other.prefix),
            BricksAnalysis.widening(self.bricks, other.bricks)
        )
    
    def __repr__(self):
        return f"Integrated(Prefix={self.prefix}, Bricks={self.bricks})"
    
    def __eq__(self, other):
        if not isinstance(other, IntegratedStringValue):
            return False
        return self.prefix == other.prefix and self.bricks == other.bricks
    
    def __hash__(self):
        return hash((self.prefix, self.bricks))