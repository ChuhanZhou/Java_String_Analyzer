from enum import Enum

class Sign(Enum):
    POSITIVE = "+"
    NEGATIVE = "-"
    ZERO = "0"
    
    def __neg__(self):
        match self:
            case Sign.POSITIVE:
                return Sign.NEGATIVE
            case Sign.NEGATIVE:
                return Sign.POSITIVE
            case Sign.ZERO:
                return Sign.ZERO
    
    def __add__(self, other):
        signs = {self, other}
        if len(signs) == 1:
            return signs
        elif Sign.ZERO in signs:
            signs.remove(Sign.ZERO)
            return signs
        else:
            return {Sign.NEGATIVE, Sign.ZERO, Sign.POSITIVE}
    
    def __sub__(self, other):
        if self == Sign.ZERO:
            return {-other}
        elif other == Sign.ZERO:
            return {self}
        elif self == other:
            return {Sign.NEGATIVE, Sign.ZERO, Sign.POSITIVE}
        else:
            return {self}
    
    def __mul__(self, other):
        signs = {self, other}
        if Sign.ZERO in signs:
            return {Sign.ZERO}
        elif len(signs) == 1:
            return {Sign.POSITIVE}
        else:
            return {Sign.NEGATIVE}
    
    def __truediv__(self, other):
        if other == Sign.ZERO:
            raise ZeroDivisionError("Abstract division by zero")
        elif self == Sign.ZERO:
            return {Sign.ZERO}
        elif self == other:
            return {Sign.POSITIVE}
        else:
            return {Sign.NEGATIVE}
        
class AbstractInt(object):
    def __init__(self, value=None):
        self.state_set = set()
        if value is not None:
            if isinstance(value, int):
                if value < 0:
                    self.state_set.add(Sign.NEGATIVE)
                elif value > 0:
                    self.state_set.add(Sign.POSITIVE)
                else:
                    self.state_set.add(Sign.ZERO)
            elif isinstance(value, set):
                self.state_set = value.copy()
    
    def top():
        result = AbstractInt()
        result.state_set = {Sign.POSITIVE, Sign.NEGATIVE, Sign.ZERO}
        return result
    
    def bottom():
        return AbstractInt()
    
    def is_bottom(self):
        return len(self.state_set) == 0
    
    def is_top(self):
        return self.state_set == {Sign.POSITIVE, Sign.NEGATIVE, Sign.ZERO}
    
    def join(self, other):
        result = AbstractInt()
        result.state_set = self.state_set | other.state_set
        return result
    
    def meet(self, other):
        result = AbstractInt()
        result.state_set = self.state_set & other.state_set
        return result
    
    def __add__(self, other):
        result = AbstractInt()
        for s_state in self.state_set:
            for o_state in other.state_set:
                result.state_set.update(s_state + o_state)
        return result
    
    def __sub__(self, other):
        result = AbstractInt()
        for s_state in self.state_set:
            for o_state in other.state_set:
                result.state_set.update(s_state - o_state)
        return result
    
    def __mul__(self, other):
        result = AbstractInt()
        for s_state in self.state_set:
            for o_state in other.state_set:
                result.state_set.update(s_state * o_state)
        return result
    
    def __truediv__(self, other):
        if Sign.ZERO in other.state_set:
            raise ZeroDivisionError("Abstract division by zero")
        result = AbstractInt()
        for s_state in self.state_set:
            for o_state in other.state_set:
                result.state_set.update(s_state / o_state)
        return result
    
    def __neg__(self):
        result = AbstractInt()
        for s_state in self.state_set:
            result.state_set.add(-s_state)
        return result
    
    def __lt__(self, other):
        return self.state_set < other.state_set

    def __gt__(self, other):
        return self.state_set > other.state_set

    def __eq__(self, other):
        return self.state_set == other.state_set

    def __ne__(self, other):
        return self.state_set != other.state_set

    def __le__(self, other):
        return self.state_set <= other.state_set

    def __ge__(self, other):
        return self.state_set >= other.state_set
    
    def __hash__(self):
        return hash(frozenset(self.state_set))
    
    def __copy__(self):
        copy = AbstractInt()
        copy.state_set = self.state_set.copy()
        return copy
    
    def __str__(self):
        if self.is_bottom():
            return "EMPTY"  
        return "{" + ",".join(sorted([s.value for s in self.state_set])) + "}"
    
    def __repr__(self):
        return self.__str__()
    
if __name__ == '__main__':
    print("Start prove abstract operation correctly")
    test_values = [-2,-1,0,1,2]

    total_case_num = 0
    true_case_num = 0
    for v1 in test_values:
        for v2 in test_values:
            a1 = AbstractInt(v1)
            a2 = AbstractInt(v2)

            r_l = AbstractInt(v1 + v2)
            r_r = a1 + a2
            r = r_l <= r_r
            total_case_num+=1
            true_case_num+=int(r)
            print("[{}] α({} + {}) <= α({}) + α({}): {} <= {}".format(r, v1, v2, v1, v2, r_l, r_r))

            r_l = AbstractInt(v1 - v2)
            r_r = a1 - a2
            r = r_l <= r_r
            total_case_num += 1
            true_case_num += int(r)
            print("[{}] α({} - {}) <= α({}) - α({}): {} <= {}".format(r, v1, v2, v1, v2, r_l, r_r))

            r_l = AbstractInt(v1 * v2)
            r_r = a1 * a2
            r = r_l <= r_r
            total_case_num += 1
            true_case_num += int(r)
            print("[{}] α({} * {}) <= α({}) * α({}): {} <= {}".format(r, v1, v2, v1, v2, r_l, r_r))

            try:
                r_r = a1 / a2
            except ZeroDivisionError as e:
                r = v2 == 0
                total_case_num += 1
                true_case_num += int(r)
                print("[{}] α({}) / α({}): {}".format(r, v1, v2, e))
            else:
                r_l = AbstractInt(v1 / v2)
                r = r_l <= r_r
                total_case_num += 1
                true_case_num += int(r)
                print("[{}] α({} / {}) <= α({}) / α({}): {} <= {}".format(r, v1, v2, v1, v2, r_l, r_r))

    prove_print = "[Accuracy]: {:.2f}% ({}/{})".format(true_case_num / total_case_num * 10 ** 2, true_case_num,total_case_num)
    print("-"*len(prove_print))
    print(prove_print)
    print("-"*len(prove_print))