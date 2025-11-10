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
        """Transfer function: string concatenation"""
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
    
    def __str__(self) -> str:
        if self.is_top():
            return "⊤"
        if self.is_bottom():
            return "⊥"
        prefix_str = ",".join(sorted(self.prefixes)) if self.prefixes else "∅"
        return f"{{prefix={prefix_str}, len=[{self.min_len},{self.max_len}]}}"


# Example usage
if __name__ == "__main__":
    s1 = StringAbstraction.from_string("carpet")
    s2 = StringAbstraction.from_string("carton")
    
    print(f"s1 = {s1}")
    print(f"s2 = {s2}")
    print(f"s1.join(s2) = {s1.join(s2)}")
    print(f"s1.concat(s2) = {s1.concat(s2)}")
