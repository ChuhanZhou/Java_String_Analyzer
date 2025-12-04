from dataclasses import dataclass
from typing import Set, Optional


@dataclass(frozen=True)
class PrefixLenAbstraction:
    """finite-height string abstraction using prefix + length info. no suffixes and no nullability"""
    prefixes: Set[str]  # set of possible prefixes
    min_len: int
    max_len: int
    max_prefix_depth: int = 3  # ensures finite-height
    max_length: int = 100  # ensures finite-height
    
    def __post_init__(self):
        # truncate prefixes to max_depth
        if self.max_prefix_depth > 0:
            truncated = set()
            for prefix in self.prefixes:
                if len(prefix) > self.max_prefix_depth:
                    truncated.add(prefix[:self.max_prefix_depth])
                else:
                    truncated.add(prefix)
            object.__setattr__(self, 'prefixes', truncated)
        
        # bound length
        if self.max_len > self.max_length:
            object.__setattr__(self, 'max_len', self.max_length)
    
    @classmethod
    def bottom(cls, max_prefix_depth: int = 3, max_length: int = 100) -> "PrefixLenAbstraction":
        """bottom: no strings"""
        return cls(set(), 1, 0, max_prefix_depth, max_length)
    
    @classmethod
    def top(cls, max_prefix_depth: int = 3, max_length: int = 100) -> "PrefixLenAbstraction":
        """top: all strings"""
        return cls({""}, 0, max_length, max_prefix_depth, max_length)
    
    @classmethod
    def from_string(cls, s: str, max_prefix_depth: int = 3, max_length: int = 100) -> "PrefixLenAbstraction":
        """create from concrete string"""
        if not s:
            return cls({""}, 0, 0, max_prefix_depth, max_length)
        prefix = s[:min(len(s), max_prefix_depth)]
        return cls({prefix}, len(s), len(s), max_prefix_depth, max_length)
    
    def is_bottom(self) -> bool:
        return self.min_len > self.max_len
    
    def is_top(self) -> bool:
        return "" in self.prefixes and self.min_len == 0 and self.max_len == self.max_length
    
    def join(self, other: "PrefixLenAbstraction") -> "PrefixLenAbstraction":
        """least upper bound"""
        if self.is_bottom():
            return other
        if other.is_bottom():
            return self
        if self.is_top() or other.is_top():
            return self.top(self.max_prefix_depth, self.max_length)
        
        # join prefixes, find common prefixes or widen
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
        
        # if no common prefix, widen to top
        if not new_prefixes:
            return self.top()
        
        # join length intervals
        new_min_len = min(self.min_len, other.min_len)
        new_max_len = max(self.max_len, other.max_len)
        
        return PrefixLenAbstraction(new_prefixes, new_min_len, new_max_len, 
                                self.max_prefix_depth, self.max_length)
    
    def widen(self, other: "PrefixLenAbstraction") -> "PrefixLenAbstraction":
        """simple widening to force convergence"""
        joined = self.join(other)
        # if max length increases, widen to top
        if joined.max_len > self.max_len * 2:
            return self.top()
        return joined
    
    def concat(self, other: "PrefixLenAbstraction") -> "PrefixLenAbstraction":
        """abstract version of s1 + s2"""
        # combine prefixes
        new_prefixes = set()
        for p1 in self.prefixes:
            for p2 in other.prefixes:
                combined = p1 + p2
                if len(combined) > self.max_prefix_depth:
                    combined = combined[:self.max_prefix_depth]
                new_prefixes.add(combined)
        
        # add length
        new_min_len = self.min_len + other.min_len
        new_max_len = self.max_len + other.max_len
        if new_max_len > self.max_length:
            new_max_len = self.max_length
        
        return PrefixLenAbstraction(new_prefixes, new_min_len, new_max_len,
                                self.max_prefix_depth, self.max_length)
    
    def length(self) -> tuple[int, int]:
        """returns (min,max) length"""
        return (self.min_len, self.max_len)
    
    def startsWith(self, prefix: str) -> Optional[bool]:
        """best effort startswith check (True/False/None)"""
        if self.is_top():
            return None  # could be any string / unknown
        
        # check if any tracked prefix matches
        for p in self.prefixes:
            if p.startswith(prefix):
                # our tracked prefix matches
                # if prefix length <= our tracked prefix length, its true
                if len(prefix) <= len(p):
                    return True
                # otherwise might be true if we have longer strings
                if self.min_len >= len(prefix):
                    return None  # possibly true
                return False
        
        # no match in known prefixes
        if self.min_len < len(prefix):
            return False
        return None  # could still match if we have longer strings
    
    def equals(self, other: "PrefixLenAbstraction") -> Optional[bool]:
        """cheap equality check"""
        if self.is_top() or other.is_top():
            return None  # unknown
        
        # check if prefixes and lengths match 
        if self.prefixes == other.prefixes:
            # prefixes match, check if lengths also match 
            if (self.min_len == self.max_len and 
                other.min_len == other.max_len and 
                self.min_len == other.min_len):
                # exact match on both prefix and length. if exact length and matching prefix, they are equal
                return True
        
        # lengths disagree, false if both exact
        if (self.min_len == self.max_len and 
            other.min_len == other.max_len and 
            self.min_len != other.max_len):
            return False
        
        return None  # cant determine for abstract strings
    
    def substring(self, start: int, end: Optional[int] = None) -> "PrefixLenAbstraction":
        """keeps length info, drops prefix detail"""
        if end is None:
            # s.substring(start), from start to end of string
            new_min_len = max(0, self.min_len - start)
            new_max_len = max(0, self.max_len - start)
        else:
            # s.substring(start, end), from start to end
            new_min_len = max(0, min(self.min_len, end - start))
            new_max_len = max(0, min(self.max_len, end - start))
        
        # prefix info is basically unknown after substring
        new_prefixes = {""}
        
        return PrefixLenAbstraction(new_prefixes, new_min_len, new_max_len,
                                self.max_prefix_depth, self.max_length)
    
    def __str__(self) -> str:
        if self.is_top():
            return "⊤"
        if self.is_bottom():
            return "⊥"
        prefix_str = ",".join(sorted(self.prefixes)) if self.prefixes else "∅"
        return f"{{prefix={prefix_str}, len=[{self.min_len},{self.max_len}]}}"