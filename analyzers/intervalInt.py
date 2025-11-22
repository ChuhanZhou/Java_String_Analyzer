class IntervalInt(object):
    def __init__(self, low, high, exclude_zero=False):
        # Validate interval
        if low == float('inf') or high == float('-inf'):
            self.low = float('inf')
            self.high = float('-inf')
            self.exclude_zero = False
        elif low > high:
            self.low = float('inf')
            self.high = float('-inf')
            self.exclude_zero = False
        else:
            self.low = low
            self.high = high
            self.exclude_zero = exclude_zero if (low <= 0 <= high) else False
    
    def from_concrete(value):
        return IntervalInt(value, value, exclude_zero=False)
    
    def top():
        return IntervalInt(float('-inf'), float('inf'), exclude_zero=False)
    
    def bottom():
        return IntervalInt(float('inf'), float('-inf'), exclude_zero=False)
    
    def is_bottom(self):
        return self.low == float('inf') and self.high == float('-inf')
    
    def is_top(self):
        return self.low == float('-inf') and self.high == float('inf')
    
    def contains(self, value):
        if self.is_bottom():
            return False
        in_range = self.low <= value <= self.high
        if in_range and value == 0 and self.exclude_zero:
            return False
        return in_range
    
    def definitely_not_zero(self):
        if self.low > 0 or self.high < 0:
            return True
        if self.exclude_zero and self.low <= 0 <= self.high:
            return True
        return False
    
    def join(self, other):
        if self.is_bottom():
            return other
        if other.is_bottom():
            return self
        
        new_low = min(self.low, other.low)
        new_high = max(self.high, other.high)
        new_exclude_zero = self.exclude_zero and other.exclude_zero
        return IntervalInt(new_low, new_high, exclude_zero=new_exclude_zero)
    
    def meet(self, other):
        if self.is_bottom() or other.is_bottom():
            return IntervalInt.bottom()
        
        new_low = max(self.low, other.low)
        new_high = min(self.high, other.high)
        
        if new_low > new_high:
            return IntervalInt.bottom()
        
        new_exclude_zero = self.exclude_zero or other.exclude_zero
        return IntervalInt(new_low, new_high, exclude_zero=new_exclude_zero)
    
    def widen(self, other, constants):
        if self.is_bottom():
            return other
        if other.is_bottom():
            return self
        
        sorted_constants = sorted(constants | {int(self.low), int(self.high)} 
                                 if not (isinstance(self.low, float) or isinstance(self.high, float))
                                 else constants)
        
        if other.low < self.low:
            # Lower bound decreased, jump to previous constant or -inf
            new_low = float('-inf')
            for c in reversed(sorted_constants):
                if c <= other.low:
                    new_low = c
                    break
        else:
            new_low = self.low
        
        if other.high > self.high:
            # Upper bound increased, jump to next constant or +inf
            new_high = float('inf')
            for c in sorted_constants:
                if c >= other.high:
                    new_high = c
                    break
        else:
            new_high = self.high
        
        return IntervalInt(new_low, new_high, exclude_zero=False)
    
    def __add__(self, other):
        if self.is_bottom() or other.is_bottom():
            return IntervalInt.bottom()
        return IntervalInt(self.low + other.low, self.high + other.high)
    
    def __sub__(self, other):
        if self.is_bottom() or other.is_bottom():
            return IntervalInt.bottom()
        return IntervalInt(self.low - other.high, self.high - other.low)
    
    def __mul__(self, other):
        if self.is_bottom() or other.is_bottom():
            return IntervalInt.bottom()
        
        products = [
            self.low * other.low,
            self.low * other.high,
            self.high * other.low,
            self.high * other.high
        ]
        return IntervalInt(min(products), max(products))
    
    def __truediv__(self, other):
        if self.is_bottom() or other.is_bottom():
            return IntervalInt.bottom()
        
        if other.low <= 0 <= other.high and not other.exclude_zero:
            raise ZeroDivisionError("Abstract division by zero")
        
        if other.exclude_zero and other.low <= 0 <= other.high:
            return IntervalInt.top()
        
        quotients = [
            self.low / other.low,
            self.low / other.high,
            self.high / other.low,
            self.high / other.high
        ]
        return IntervalInt(int(min(quotients)), int(max(quotients)))
    
    def __neg__(self):
        if self.is_bottom():
            return IntervalInt.bottom()
        return IntervalInt(-self.high, -self.low)
    
    def __le__(self, other):
        if self.is_bottom():
            return True
        if other.is_bottom():
            return False
        return other.low <= self.low and self.high <= other.high
    
    def __lt__(self, other):
        return self <= other and self != other
    
    def __ge__(self, other):
        return other <= self
    
    def __gt__(self, other):
        return other < self
    
    def __eq__(self, other):
        if not isinstance(other, IntervalInt):
            return False
        return (self.low == other.low and self.high == other.high and 
                self.exclude_zero == other.exclude_zero)
    
    def __hash__(self):
        return hash((self.low, self.high, self.exclude_zero))
    
    def __str__(self):
        if self.is_bottom():
            return "EMPTY"
        
        low_str = "-inf" if self.low == float('-inf') else str(int(self.low) if isinstance(self.low, float) else self.low)
        high_str = "+inf" if self.high == float('inf') else str(int(self.high) if isinstance(self.high, float) else self.high)
        
        result = f"[{low_str},{high_str}]"
        if self.exclude_zero:
            result += "\\{0}"
        return result
    
    def __repr__(self):
        return self.__str__()