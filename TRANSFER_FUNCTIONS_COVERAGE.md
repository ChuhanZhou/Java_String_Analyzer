# Transfer Functions Coverage in Strings.java

## Overview

this document shows which transfer functions from `finite_height_string.py` are tested in `Strings.java`.

## Transfer Functions in finite_height_string.py

1. **concat()** - string concatenation
2. **length()** - string length
3. **startsWith()** - prefix checking
4. **equals()** - string equality
5. **substring()** - substring extraction

## Test Coverage in Strings.java

### 1. concat()

**Test cases:**

- `concatEmptyStrings()` - "" + "" = ""
- `concatEmptyWithNonEmpty()` - "" + "hello" = "hello"
- `concatNonEmptyWithEmpty()` - "hello" + "" = "hello"
- `concatTwoNonEmptyStrings()` - "hello" + "world" = "helloworld"
- `concatMultipleStrings()` - "a" + "b" + "c" = "abc"
- `concatWithLengthParameter(int n)` - tests concat with parameter
- `conditionalConcat(boolean flag)` - tests concat in conditional branches
- `chainedConcat()` - multiple concatenations
- `stringBuilderConcat()` - concatenation via method call

**Status:** all cases covered

---

### 2. length()

**Test cases:**

- `emptyString()` - tests length of ""
- `singleCharString()` - tests length of "a"
- `multiCharString()` - tests length of "hello"
- `assertStringLength(int expectedLen)` - tests length assertion
- `assertConcatLength(int expectedLen)` - tests length after concat
- `assertEmptyStringLength(int n)` - tests empty string length
- `conditionalLength(int n)` - tests length in conditional
- `repeatStringLoop(int times)` - tests length in loops
- `buildStringWithLength(int targetLen)` - tests length after loop building
- `repeatWithLength(int len)` - tests length after repeated concat
- `multiParameterStringLength(int len1, int len2)` - tests multiple string lengths

**Status:** all cases covered

---

### 3. startsWith()

**Test cases:**

- `checkPrefix()` - "carpet".startsWith("car")
- `checkNonPrefix()` - "carpet".startsWith("dog") = false
- `checkSingleCharPrefix()` - "hello".startsWith("h")
- `checkFullStringAsPrefix()` - "hello".startsWith("hello")
- `checkEmptyStringPrefix()` - "hello".startsWith("")
- `conditionalConcat(boolean flag)` - tests startsWith after conditional concat
- `chainedConcat()` - tests startsWith after chained concat
- `prefixAndLengthCheck(int expectedLen)` - tests startsWith with length check
- `prefixOfEmptyString()` - tests startsWith on empty string

**Status:** all cases covered

---

### 4. equals()

**Test cases:**

- `stringEquality()` - "hello".equals("hello") = true
- `stringInequality()` - "hello".equals("world") = false
- `concatAndCompare()` - tests equals after concat
- `substringFullString()` - tests equals after substring

**Status:** all cases covered

---

### 5. substring()

**Test cases:**

- `substringFromStart()` - "hello".substring(0, 3) = "hel"
- `substringFromMiddle()` - "hello".substring(1, 4) = "ell"
- `substringFullString()` - "hello".substring(0, 5) = "hello"

**Status:** all cases covered

---

## Summary

| transfer function | test cases     | status        |
| ----------------- | -------------- | ------------- |
| concat()          | 9 test cases   | fully covered |
| length()          | 11+ test cases | fully covered |
| startsWith()      | 9 test cases   | fully covered |
| equals()          | 4 test cases   | fully covered |
| substring()       | 3 test cases   | fully covered |

**Overall Status:**

all five transfer functions from `finite_height_string.py` have test coverage in `Strings.java`.
