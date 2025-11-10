from enum import Enum

#Bounded Abstraction
class Abstraction(Enum):
    POSITIVE = "+"
    NEGATIVE = "-"
    ZERO = "0"

    def __neg__(self):
        match self:
            case Abstraction.POSITIVE:
                return Abstraction.NEGATIVE
            case Abstraction.NEGATIVE:
                return Abstraction.POSITIVE
            case Abstraction.ZERO:
                return Abstraction.ZERO

    def __add__(self, other):
        sets = {self, other}
        if len(sets) == 1:
            return sets
        elif Abstraction.ZERO in sets:
            sets.remove(Abstraction.ZERO)
            return sets
        else:
            return {Abstraction.NEGATIVE,Abstraction.ZERO,Abstraction.POSITIVE}

    def __sub__(self, other):
        if self == Abstraction.ZERO:
            return {-other}
        elif other == Abstraction.ZERO:
            return {self}
        elif self == other:
            return {Abstraction.NEGATIVE, Abstraction.ZERO, Abstraction.POSITIVE}
        else:
            return {self}

    def __mul__(self, other):
        sets = {self, other}
        if Abstraction.ZERO in sets:
            return {Abstraction.ZERO}
        elif len(sets) == 1:
            return {Abstraction.POSITIVE}
        else:
            return {Abstraction.NEGATIVE}

    def __truediv__(self, other):
        if other == Abstraction.ZERO:
            raise ZeroDivisionError("Abstract division by zero")
        elif self == Abstraction.ZERO:
            return {Abstraction.ZERO}
        elif self == other:
            return {Abstraction.POSITIVE}
        else:
            return {Abstraction.NEGATIVE}

class AbstractInt(object):
    state_set = None

    def __init__(self, value=None):
        self.state_set = set()
        if value is not None:
            if value < 0:
                self.state_set.add(Abstraction.NEGATIVE)
            elif value > 0:
                self.state_set.add(Abstraction.POSITIVE)
            elif value == 0:
                self.state_set.add(Abstraction.ZERO)

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
        result = AbstractInt()
        for s_state in self.state_set:
            for o_state in other.state_set:
                result.state_set.update(s_state / o_state)
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

    def __copy__(self):
        copy = AbstractInt()
        copy.state_set = self.state_set.copy()
        return copy

    def __str__(self):
        return str([s.value for s in self.state_set])

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