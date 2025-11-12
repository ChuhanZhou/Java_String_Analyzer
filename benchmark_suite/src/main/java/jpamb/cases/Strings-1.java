package jpamb.cases;

import jpamb.utils.Case;
import jpamb.utils.Tag;
import static jpamb.utils.Tag.TagType.*;

/**
 * String abstraction test cases for finite-height string analysis.
 * Tests string operations: concatenation, length, prefix analysis, etc.
 */
public class Strings {

  // ============================================================================
  // Basic String Operations
  // ===========================================================================

  @Case("() -> ok")
  public static void emptyString() {
    String s = "";
    assert s.length() == 0;
  }

  @Case("() -> ok")
  public static void singleCharString() {
    String s = "a";
    assert s.length() == 1;
  }

  @Case("() -> ok")
  public static void multiCharString() {
    String s = "hello";
    assert s.length() == 5;
  }

  // ============================================================================
  // String Concatenation
  // ============================================================================

  @Case("() -> ok")
  @Tag({ STRING })
  public static void concatEmptyStrings() {
    String s1 = "";
    String s2 = "";
    String result = s1 + s2;
    assert result.length() == 0;
  }

  @Case("() -> ok")
  @Tag({ STRING })
  public static void concatEmptyWithNonEmpty() {
    String s1 = "";
    String s2 = "hello";
    String result = s1 + s2;
    assert result.length() == 5;
  }

  @Case("() -> ok")
  @Tag({ STRING })
  public static void concatNonEmptyWithEmpty() {
    String s1 = "hello";
    String s2 = "";
    String result = s1 + s2;
    assert result.length() == 5;
  }

  @Case("() -> ok")
  @Tag({ STRING })
  public static void concatTwoNonEmptyStrings() {
    String s1 = "hello";
    String s2 = "world";
    String result = s1 + s2;
    assert result.length() == 10;
  }

  @Case("() -> ok")
  @Tag({ STRING })
  public static void concatMultipleStrings() {
    String s1 = "a";
    String s2 = "b";
    String s3 = "c";
    String result = s1 + s2 + s3;
    assert result.length() == 3;
  }

  @Case("(3) -> ok")
  @Case("(0) -> assertion error")
  @Tag({ STRING })
  public static void concatWithLengthParameter(int n) {
    String s1 = "cat";
    String s2 = "dog";
    String result = s1 + s2;
    assert result.length() == n;
  }

  // ============================================================================
  // String Length Analysis
  // ============================================================================

  @Case("(5) -> ok")
  @Case("(0) -> assertion error")
  @Tag({ STRING })
  public static void assertStringLength(int expectedLen) {
    String s = "hello";
    assert s.length() == expectedLen;
  }

  @Case("(10) -> ok")
  @Case("(5) -> assertion error")
  @Tag({ STRING })
  public static void assertConcatLength(int expectedLen) {
    String s1 = "hello";
    String s2 = "world";
    String result = s1 + s2;
    assert result.length() == expectedLen;
  }

  @Case("(0) -> ok")
  @Case("(1) -> assertion error")
  @Tag({ STRING })
  public static void assertEmptyStringLength(int n) {
    String s = "";
    assert s.length() == n;
  }

  // ============================================================================
  // String Prefix Analysis
  // ============================================================================

  @Case("() -> ok")
  @Tag({ STRING })
  public static void checkPrefix() {
    String s = "carpet";
    assert s.startsWith("car");
  }

  @Case("() -> ok")
  @Tag({ STRING })
  public static void checkNonPrefix() {
    String s = "carpet";
    assert !s.startsWith("dog");
  }

  @Case("() -> ok")
  @Tag({ STRING })
  public static void checkSingleCharPrefix() {
    String s = "hello";
    assert s.startsWith("h");
  }

  @Case("() -> ok")
  @Tag({ STRING })
  public static void checkFullStringAsPrefix() {
    String s = "hello";
    assert s.startsWith("hello");
  }

  @Case("() -> ok")
  @Tag({ STRING })
  public static void checkEmptyStringPrefix() {
    String s = "hello";
    assert s.startsWith("");
  }

  // ============================================================================
  // Conditional String Operations
  // ============================================================================

  @Case("(true) -> ok")
  @Case("(false) -> assertion error")
  @Tag({ STRING })
  public static void conditionalConcat(boolean flag) {
    String s1 = "hello";
    String s2;
    if (flag) {
      s2 = "world";
    } else {
      s2 = "xyz";
    }
    String result = s1 + s2;
    assert result.startsWith("hello");
  }

  @Case("(5) -> ok")
  @Case("(4) -> assertion error")
  @Tag({ STRING })
  public static void conditionalLength(int n) {
    String s = "hello";
    if (n == 5) {
      assert s.length() == n;
    } else {
      assert false; // should not reach here
    }
  }

  // ============================================================================
  // Loop-based String Operations
  // ============================================================================

  @Case("(1) -> ok")
  @Case("(0) -> assertion error")
  @Tag({ STRING, LOOP })
  public static void repeatStringLoop(int times) {
    assert times > 0;
    String s = "a";
    for (int i = 0; i < times; i++) {
      s = s + "b";
    }
    assert s.length() >= 1;
  }

  @Case("(3) -> ok")
  @Case("(0) -> assertion error")
  @Tag({ STRING, LOOP })
  public static void repeatStringLoopBounded(int times) {
    assert times > 0;
    String s = "x";
    int length = 1;
    for (int i = 0; i < times; i++) {
      s = s + "y";
      length++;
    }
    assert length == times + 1;
  }

  @Case("(5) -> ok")
  @Case("(4) -> assertion error")
  @Tag({ STRING, LOOP })
  public static void buildStringWithLength(int targetLen) {
    assert targetLen > 0;
    String s = "";
    for (int i = 0; i < targetLen; i++) {
      s = s + "x";
    }
    assert s.length() == targetLen;
  }

  // ============================================================================
  // Substring Operations
  // ============================================================================

  @Case("() -> ok")
  @Tag({ STRING })
  public static void substringFromStart() {
    String s = "hello";
    String sub = s.substring(0, 3);
    assert sub.length() == 3;
  }

  @Case("() -> ok")
  @Tag({ STRING })
  public static void substringFromMiddle() {
    String s = "hello";
    String sub = s.substring(1, 4);
    assert sub.length() == 3;
  }

  @Case("() -> ok")
  @Tag({ STRING })
  public static void substringFullString() {
    String s = "hello";
    String sub = s.substring(0, 5);
    assert sub.equals(s);
  }

  // ============================================================================
  // String Comparison
  // ============================================================================

  @Case("() -> ok")
  @Tag({ STRING })
  public static void stringEquality() {
    String s1 = "hello";
    String s2 = "hello";
    assert s1.equals(s2);
  }

  @Case("() -> ok")
  @Tag({ STRING })
  public static void stringInequality() {
    String s1 = "hello";
    String s2 = "world";
    assert !s1.equals(s2);
  }

  @Case("() -> ok")
  @Tag({ STRING })
  public static void concatAndCompare() {
    String s1 = "hello";
    String s2 = "world";
    String result = s1 + s2;
    assert result.equals("helloworld");
  }

  // ============================================================================
  // Complex String Scenarios
  // ============================================================================

  @Case("() -> ok")
  @Tag({ STRING })
  public static void chainedConcat() {
    String s1 = "a";
    String s2 = "b";
    String s3 = "c";
    String result = s1 + s2 + s3;
    assert result.length() == 3;
    assert result.startsWith("a");
  }

  @Case("(3) -> ok")
  @Case("(2) -> assertion error")
  @Tag({ STRING })
  public static void prefixAndLengthCheck(int expectedLen) {
    String prefix = "car";
    String suffix = "pet";
    String result = prefix + suffix;
    assert result.length() == expectedLen;
    assert result.startsWith("car");
  }

  @Case("() -> ok")
  @Tag({ STRING, CALL })
  public static void stringBuilderConcat() {
    String s1 = "Hello";
    String s2 = "World";
    String result = concatenate(s1, s2);
    assert result.length() == 10;
  }

  public static String concatenate(String a, String b) {
    return a + b;
  }

  @Case("(5) -> ok")
  @Case("(4) -> assertion error")
  @Tag({ STRING })
  public static void repeatWithLength(int len) {
    String base = "x";
    String result = base;
    for (int i = 1; i < len; i++) {
      result = result + "x";
    }
    assert result.length() == len;
  }

  // ============================================================================
  // Edge Cases
  // ============================================================================

  @Case("() -> ok")
  @Tag({ STRING })
  public static void nullCheckPrevented() {
    String s = "notNull";
    assert s != null;
  }

  @Case("() -> ok")
  @Tag({ STRING })
  public static void emptyStringAfterConditional() {
    String s = "";
    if (false) {
      s = "nonempty";
    }
    assert s.length() == 0;
  }

  @Case("() -> ok")
  @Tag({ STRING })
  public static void prefixOfEmptyString() {
    String s = "";
    assert s.startsWith("");
  }

  @Case("(1, 1) -> ok")
  @Case("(2, 3) -> assertion error")
  @Tag({ STRING })
  public static void multiParameterStringLength(int len1, int len2) {
    String s1 = "a";
    for (int i = 1; i < len1; i++) s1 = s1 + "a";
    
    String s2 = "b";
    for (int i = 1; i < len2; i++) s2 = s2 + "b";
    
    assert s1.length() == len1;
    assert s2.length() == len2;
  }

}
