from dataclasses import dataclass
from typing import Set, Optional


@dataclass(frozen=True)
class StringAbstraction:
    """finite-height string abstraction using prefix + length info"""
    prefixes: Set[str]  # Set of possible prefixes
    suffixes: Set[str]
    min_len: int
    max_len: int
    can_be_null: bool = False
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

            # Truncate suffixes
            truncated_suffixes = set()
            for suffix in self.suffixes:
                if len(suffix) > self.max_prefix_depth:
                    truncated_suffixes.add(suffix[-self.max_prefix_depth:])
                else:
                    truncated_suffixes.add(suffix)
            object.__setattr__(self, 'suffixes', truncated_suffixes)
        
        # Bound length
        if self.max_len > self.max_length:
            object.__setattr__(self, 'max_len', self.max_length)

    @classmethod
    def null(cls) -> "StringAbstraction":
        """Represents definitely null"""
        return cls(set(), set(), 0, 0, can_be_null=True, max_prefix_depth=0, max_length=0)
    
    def is_definitely_null(self) -> bool:
        """Check if definitely null"""
        return self.can_be_null and len(self.prefixes) == 0 and self.max_len == 0
    
    def is_definitely_not_null(self) -> bool:
        """Check if definitely not null"""
        return not self.can_be_null
    
    def is_possibly_null(self) -> bool:
        """Check if possibly null"""
        return bool(self.can_be_null) and not self.is_definitely_null()
    
    @classmethod
    def bottom(cls, max_prefix_depth: int = 3, max_length: int = 100) -> "StringAbstraction":
        """Bottom: no strings"""
        return cls(set(), set(), 1, 0, can_be_null=False, 
                  max_prefix_depth=max_prefix_depth, max_length=max_length)
    
    @classmethod
    def top(cls, max_prefix_depth: int = 3, max_length: int = 100) -> "StringAbstraction":
        """Top: all strings"""
        return cls({""}, {""}, 0, max_length, can_be_null=True, max_prefix_depth=max_prefix_depth, max_length=max_length)
    
    @classmethod
    def from_string(cls, s: str, max_prefix_depth: int = 3, max_length: int = 100) -> "StringAbstraction":
        """Create from concrete string"""
        if s is None: return cls.top(max_prefix_depth, max_length)
        prefix = s[:min(len(s), max_prefix_depth)]
        suffix = s[max(0, len(s) - max_prefix_depth):]
        return cls({prefix}, {suffix}, len(s), len(s),can_be_null=False, max_prefix_depth=max_prefix_depth, max_length=max_length)
    
    def is_bottom(self) -> bool:
        return self.min_len > self.max_len
    
    def is_top(self) -> bool:
        return "" in self.prefixes and "" in self.suffixes and self.min_len == 0 and self.max_len == self.max_length
    
    def join(self, other: "StringAbstraction") -> "StringAbstraction":
        """Join (least upper bound)"""
        if self.is_bottom():
            return other
        if other.is_bottom():
            return self
        
        new_can_be_null = bool(self.can_be_null or other.can_be_null)
        new_min_len = min(self.min_len, other.min_len)
        new_max_len = max(self.max_len, other.max_len)
        
        # Join prefixes: find common prefixes or widen
        new_prefixes = set()
        if not self.prefixes or not other.prefixes:
            new_prefixes = {""}
        else:
            for p1 in self.prefixes:
                for p2 in other.prefixes:
                    # Find longest common prefix
                    common = ""
                    for i in range(min(len(p1), len(p2))):
                        if p1[i] == p2[i]:
                            common += p1[i]
                        else:
                            break
                    new_prefixes.add(common)
        
        # Join suffixes: find common suffixes (from end)
        new_suffixes = set()
        if not self.suffixes or not other.suffixes:
            new_suffixes = {""}
        else:
            for s1 in self.suffixes:
                for s2 in other.suffixes:
                    common = ""
                    for i in range(1, min(len(s1), len(s2)) + 1):
                        if s1[-i] == s2[-i]:
                            common = s1[-i] + common
                        else:
                            break
                    new_suffixes.add(common)
        
        return StringAbstraction(new_prefixes, new_suffixes, new_min_len, new_max_len, new_can_be_null,
                                self.max_prefix_depth, self.max_length)
    
    def widen(self, other: "StringAbstraction") -> "StringAbstraction":
        """Widening operator for termination"""
        if self.is_bottom():
            return other
        if other.is_bottom():
            return self
        if self.is_top() or other.is_top():
            return self.top()
        new_can_be_null = bool(self.can_be_null or other.can_be_null)

        # Widen prefixes
        new_prefixes = self.prefixes.copy()
        if self.prefixes != other.prefixes:
            # If prefixes diverge, widen to top prefix
            new_prefixes = {""}

        # Widen suffixes
        new_suffixes = self.suffixes.copy()
        if self.suffixes != other.suffixes:
            new_suffixes = {""}

        # Widen lengths
        new_min_len = min(self.min_len, other.min_len)

        # Widen max_len: if increasing, accelerate to infinity (max_length)
        if other.max_len > self.max_len:
            if other.max_len > self.max_len * 2:
                # Rapid increase - jump to max
                new_max_len = self.max_length
            else:
                new_max_len = other.max_len
        else:
            new_max_len = self.max_len

        # If everything widened to top, return top
        if new_prefixes == {""} and new_suffixes == {""} and new_max_len == self.max_length:
            return self.top()

        return StringAbstraction(new_prefixes, new_suffixes, new_min_len, new_max_len,new_can_be_null,
                                self.max_prefix_depth, self.max_length)
    
    def concat(self, other: "StringAbstraction") -> "StringAbstraction":
        """
        Transfer function: string concatenation (s1 + s2)
        
        Example: "hello" + "world" = "helloworld"
        - Prefix: combine prefixes (up to max depth)
        - Length: add lengths together
        """
        # Combine prefixes
        if self.is_bottom() or other.is_bottom():
            return self.bottom()
        
        
        new_prefixes = set()
        for p1 in self.prefixes:
            for p2 in other.prefixes:
                combined = p1 + p2
                if len(combined) > self.max_prefix_depth:
                    combined = combined[:self.max_prefix_depth]
                new_prefixes.add(combined)
        
        new_suffixes = set()
        
        if other.min_len >= self.max_prefix_depth:
            new_suffixes = other.suffixes.copy()
        else:
            for s1 in self.suffixes:
                for p2 in other.prefixes:
                    combined = s1 + p2
                    new_suffixes.add(combined[-self.max_prefix_depth:])
        
        # Add lengths
        new_min_len = self.min_len + other.min_len
        new_max_len = self.max_len + other.max_len
        if new_max_len > self.max_length:
            new_max_len = self.max_length
        
        return StringAbstraction(new_prefixes,  new_suffixes, new_min_len, new_max_len,
                                self.max_prefix_depth, self.max_length)
    
    def length(self) -> tuple[int, int]:
        """
        Transfer function: string length
        
        Returns: (min_length, max_length) interval
        Example: If string has length [5, 10], returns (5, 10)
        """
        return (self.min_len, self.max_len)
    
    def isEmpty(self) -> Optional[bool]:
        """
        Transfer function: check if string is empty     
        Example: "".isEmpty() = True
        """
        if self.min_len == 0 and self.max_len == 0:
            return True  # Definitely empty
        elif self.min_len > 0:
            return False  # Definitely not empty
        else:
            return None
    
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
            return None 
        
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
    
    def endsWith(self, suffix: str) -> Optional[bool]:
        """
        Transfer function: check if string ends with suffix
        
        Returns:
        - True: definitely ends with suffix
        - False: definitely doesn't end with suffix  
        - None: unknown (can't determine)
        
        Example: "carpet".endsWith("pet") = True
        
        Note: NOW we can determine this precisely because we track suffixes!
        """
        if self.is_top():
            return None
        
        # Length check
        if self.max_len < len(suffix):
            return False
        
        # Check tracked suffixes
        for s in self.suffixes:
            if s.endswith(suffix):
                # Our tracked suffix matches
                if len(suffix) <= len(s):
                    return True
                if self.min_len >= len(suffix):
                    return None  # Possibly true
                return False
        
        if self.min_len < len(suffix):
            return False
        return None
    
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
        if (self.prefixes == other.prefixes and 
            self.suffixes == other.suffixes):
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
        
        if self.prefixes and other.prefixes:
            if not (self.prefixes & other.prefixes): 
                return False

        if self.max_len < other.min_len or self.min_len > other.max_len:
            return False
        
        if self.max_len < other.min_len or self.min_len > other.max_len:
            return False
        
        return None  # Can't determine for abstract strings
    
    def substring(self, start: int, end: Optional[int] = None) -> "StringAbstraction":
        """
        Transfer function: substring extraction
        
        Example: "hello".substring(0, 3) = "hel"
        
        Note: We lose prefix information (too complex to track),
        but we keep length bounds.
        """
        if start == 0 and (end is None or end >= self.max_len):
            return self
        
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
        new_suffixes = {""}  # Top - represents any suffix
        
        return StringAbstraction(new_prefixes, new_suffixes, new_min_len, new_max_len,
                                can_be_null=False,
                                max_prefix_depth=self.max_prefix_depth, 
                                max_length=self.max_length)
    
    def __str__(self) -> str:
        if self.is_top():
            return "⊤"
        if self.is_bottom():
            return "⊥"
        null_str = "+null" if self.can_be_null else ""
        prefix_str = ",".join(sorted(self.prefixes)) if self.prefixes else "∅"
        suffix_str = ",".join(sorted(self.suffixes)) if self.suffixes else "∅"
        return f"{{prefix={prefix_str}, len=[{self.min_len},{self.max_len}]{null_str}}}"
