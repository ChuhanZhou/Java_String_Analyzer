from dataclasses import dataclass
from typing import Set, Optional


@dataclass(frozen=True)
class StringAbstraction:
    """
    Finite-height string abstraction.
    - prefix: known prefixes (bounded depth ensures finite-height)
    - length: length interval (bounded max ensures finite-height)
    """
    prefixes: Set[str]  # Set of possible prefixes
    min_len: int
    max_len: int
    max_prefix_depth: int = 3  # Ensures finite-height
    max_length: int = 100  # Ensures finite-height
    
    def __post_init__(self):
        # Truncate prefixes to max_depth
        if self.max_prefix_depth > 0:
            truncated = set()
            for prefix in self.prefixes:
                if len(prefix) > self.max_prefix_depth:
                    truncated.add(prefix[:self.max_prefix_depth])
                else:
                    truncated.add(prefix)
            object.__setattr__(self, 'prefixes', truncated)
        
        # Bound length
        if self.max_len > self.max_length:
            object.__setattr__(self, 'max_len', self.max_length)
    
    @classmethod
    def bottom(cls, max_prefix_depth: int = 3, max_length: int = 100) -> "StringAbstraction":
        """Bottom: no strings"""
        return cls(set(), 1, 0, max_prefix_depth, max_length)
    
    @classmethod
    def top(cls, max_prefix_depth: int = 3, max_length: int = 100) -> "StringAbstraction":
        """Top: all strings"""
        return cls({""}, 0, max_length, max_prefix_depth, max_length)
    
    @classmethod
    def from_string(cls, s: str, max_prefix_depth: int = 3, max_length: int = 100) -> "StringAbstraction":
        """Create from concrete string"""
        if not s:
            return cls({""}, 0, 0, max_prefix_depth, max_length)
        prefix = s[:min(len(s), max_prefix_depth)]
        return cls({prefix}, len(s), len(s), max_prefix_depth, max_length)
    
    def is_bottom(self) -> bool:
        return self.min_len > self.max_len
    
    def is_top(self) -> bool:
        return "" in self.prefixes and self.min_len == 0 and self.max_len == self.max_length
    
    def join(self, other: "StringAbstraction") -> "StringAbstraction":
        """Join (least upper bound)"""
        if self.is_bottom():
            return other
        if other.is_bottom():
            return self
        if self.is_top() or other.is_top():
            return self.top(self.max_prefix_depth, self.max_length)
        
        # Join prefixes: find common prefixes or widen
        new_prefixes = set()
        for p1 in self.prefixes:
            for p2 in other.prefixes:
                # Find longest common prefix
                common = ""
                for i in range(min(len(p1), len(p2))):
                    if p1[i] == p2[i]:
                        common += p1[i]
                    else:
                        break
                if common:
                    new_prefixes.add(common)
        
        # If no common prefix, widen to top
        if not new_prefixes:
            return self.top()
        
        # Join length intervals
        new_min_len = min(self.min_len, other.min_len)
        new_max_len = max(self.max_len, other.max_len)
        
        return StringAbstraction(new_prefixes, new_min_len, new_max_len, 
                                self.max_prefix_depth, self.max_length)
    
    def widen(self, other: "StringAbstraction") -> "StringAbstraction":
        """Widening operator for termination"""
        joined = self.join(other)
        # If max length increases significantly, widen to top
        if joined.max_len > self.max_len * 2:
            return self.top()
        return joined
    
    def concat(self, other: "StringAbstraction") -> "StringAbstraction":
        """
        Transfer function: string concatenation (s1 + s2)
        
        Example: "hello" + "world" = "helloworld"
        - Prefix: combine prefixes (up to max depth)
        - Length: add lengths together
        """
        # Combine prefixes
        new_prefixes = set()
        for p1 in self.prefixes:
            for p2 in other.prefixes:
                combined = p1 + p2
                if len(combined) > self.max_prefix_depth:
                    combined = combined[:self.max_prefix_depth]
                new_prefixes.add(combined)
        
        # Add lengths
        new_min_len = self.min_len + other.min_len
        new_max_len = self.max_len + other.max_len
        if new_max_len > self.max_length:
            new_max_len = self.max_length
        
        return StringAbstraction(new_prefixes, new_min_len, new_max_len,
                                self.max_prefix_depth, self.max_length)
    
    def length(self) -> tuple[int, int]:
        """
        Transfer function: string length
        
        Returns: (min_length, max_length) interval
        Example: If string has length [5, 10], returns (5, 10)
        """
        return (self.min_len, self.max_len)
    
    def startsWith(self, prefix: str) -> Optional[bool]:
        """
        Transfer function: check if string starts with prefix
        
        Returns:
        - True: definitely starts with prefix
        - False: definitely doesn't start with prefix  
        - None: unknown (can't determine)
        
        Example: "carpet".startsWith("car") = True
        """
        if self.is_top():
            return None  # Unknown - could be any string
        
        # Check if any of our tracked prefixes starts with the given prefix
        for p in self.prefixes:
            if p.startswith(prefix):
                # Our tracked prefix matches
                # If prefix length <= our tracked prefix length, it's definitely true
                if len(prefix) <= len(p):
                    return True
                # Otherwise, might be true if we have longer strings
                if self.min_len >= len(prefix):
                    return None  # Possibly true
                return False
        
        # No prefix matches - check if we could still have a match
        # If our min length is less than prefix length, definitely false
        if self.min_len < len(prefix):
            return False
        return None  # Could still match if we have longer strings
    
    def equals(self, other: "StringAbstraction") -> Optional[bool]:
        """
        Transfer function: check string equality
        
        Returns:
        - True: definitely equal
        - False: definitely not equal
        - None: unknown (can't determine)
        
        Example: "hello".equals("hello") = True
        """
        if self.is_top() or other.is_top():
            return None  # Unknown
        
        # Check if prefixes and lengths match exactly
        if self.prefixes == other.prefixes:
            # Prefixes match - check if lengths also match exactly
            if (self.min_len == self.max_len and 
                other.min_len == other.max_len and 
                self.min_len == other.min_len):
                # Exact match on both prefix and length
                # If we have exact length and matching prefix, they're equal
                return True
        
        # Prefixes don't match - check if we can determine false
        # If both have exact lengths and they differ, definitely false
        if (self.min_len == self.max_len and 
            other.min_len == other.max_len and 
            self.min_len != other.max_len):
            return False
        
        return None  # Can't determine for abstract strings
    
    def substring(self, start: int, end: Optional[int] = None) -> "StringAbstraction":
        """
        Transfer function: substring extraction
        
        Example: "hello".substring(0, 3) = "hel"
        
        Note: We lose prefix information (too complex to track),
        but we keep length bounds.
        """
        if end is None:
            # s.substring(start) - from start to end of string
            new_min_len = max(0, self.min_len - start)
            new_max_len = max(0, self.max_len - start)
        else:
            # s.substring(start, end) - from start to end
            new_min_len = max(0, min(self.min_len, end - start))
            new_max_len = max(0, min(self.max_len, end - start))
        
        # Prefix: lose information (too complex to track substring prefixes)
        # Set to top since we can't precisely track substring prefixes
        new_prefixes = {""}  # Top - represents any prefix
        
        return StringAbstraction(new_prefixes, new_min_len, new_max_len,
                                self.max_prefix_depth, self.max_length)
    
    def __str__(self) -> str:
        if self.is_top():
            return "⊤"
        if self.is_bottom():
            return "⊥"
        prefix_str = ",".join(sorted(self.prefixes)) if self.prefixes else "∅"
        return f"{{prefix={prefix_str}, len=[{self.min_len},{self.max_len}]}}"

