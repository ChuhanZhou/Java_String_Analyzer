package jpamb.cases;

import jpamb.utils.Case;

public class Strings {

    @Case("(null) -> null pointer exception")
    @Case("(\"\") -> ok")
    @Case("(\"hello\") -> ok")
    public static int getLength(String s) {
        return s.length();
    }

    @Case("(null) -> assertion error")
    @Case("(\"\") -> assertion error")
    @Case("(\"wish\") -> ok")
    public static void assertNotEmpty(String s) {
        assert s != null && !s.isEmpty();
    }

    @Case("(null, \"cream\") -> null pointer exception")
    @Case("(\"ice\", null) -> null pointer exception")
    @Case("(\"ice\", \"cream\") -> ok")
    public static String concatenate(String s1, String s2) {
        return s1.concat(s2);
    }

    @Case("(null, 0) -> null pointer exception")
    @Case("(\"\", 0) -> index out of bounds")
    @Case("(\"seventeen\", -1) -> index out of bounds")
    @Case("(\"seventeen\", 9) -> index out of bounds")
    @Case("(\"seventeen\", 0) -> ok")
    @Case("(\"seventeen\", 8) -> ok")
    public static char getCharAt(String s, int index) {
        return s.charAt(index);
    }

    @Case("(null, 0, 1) -> null pointer exception")
    @Case("(\"hello\", -1, 2) -> index out of bounds")
    @Case("(\"hello\", 0, 6) -> index out of bounds")
    @Case("(\"hello\", 2, 1) -> index range exception")
    @Case("(\"hello\", 0, 3) -> ok")
    @Case("(\"\", 0, 0) -> ok")
    public static String getSubstring(String s, int start, int end) {
        return s.substring(start, end);
    }

    @Case("(null, \"fly\") -> null pointer exception")
    @Case("(\"butterfly\", null) -> null pointer exception")
    @Case("(\"butterfly\", \"fly\") -> ok")
    @Case("(\"butterfly\", \"a\") -> ok")
    public static boolean checkContains(String s, String substr) {
        return s.contains(substr);
    }

    @Case("(null) -> null pointer exception")
    @Case("(\"\") -> number format exception")
    @Case("(\"123\") -> ok")
    @Case("(\"dream\") -> number format exception")
    @Case("(\"12.3\") -> number format exception")
    @Case("(\" 123 \") -> number format exception")
    public static int parseToInt(String s) {
        return Integer.parseInt(s);
    }

    @Case("(null, null) -> null pointer exception")
    @Case("(\"tomorrow\", null) -> ok")
    @Case("(null, \"together\") -> null pointer exception")
    @Case("(\"tomorrow\", \"tomorrow\") -> ok")
    @Case("(\"tomorrow\", \"together\") -> ok")
    public static boolean compareStrings(String s1, String s2) {
        return s1.equals(s2);
    }

    @Case("(\"snow\", \"\") -> ok")
    @Case("(\"\", \"\") -> ok")
    @Case("(null, \" \") -> null pointer exception")
    @Case("(\"a b c\", \" \") -> ok")
    @Case("(\"snow\", \"n\") -> ok")
    public static String[] splitString(String s, String delimiter) {
        return s.split(delimiter);
    }

    @Case("(null) -> null pointer exception")
    @Case("(\"HELLO\") -> ok")
    @Case("(\"hello\") -> ok")
    @Case("(\"\") -> ok")
    public static String toLowerCase(String s) {
        return s.toLowerCase();
    }

    @Case("(null) -> null pointer exception")
    @Case("(\"HELLO\") -> ok")
    @Case("(\"hello\") -> ok")
    @Case("(\"\") -> ok")
    public static String toUpperCase(String s) {
        return s.toUpperCase();
    }

    @Case("(\"\", \"\", \"\") -> ok")
    @Case("(\"sail away\", \"sail\", \"fly\") -> ok")
    @Case("(null, \"sail\", \"fly\") -> null pointer exception")
    @Case("(\"sail away\", null, \"fly\") -> null pointer exception")
    @Case("(\"sail away\", \"sail\", null) -> null pointer exception")
    public static String replaceString(String s, String target, String replacement) {
        return s.replace(target, replacement);
    }

    @Case("(null) -> null pointer exception")
    @Case("(\"  stay  \") -> ok")
    @Case("(\"\") -> ok")
    @Case("(\"   \") -> ok")
    public static String trimString(String s) {
        return s.trim();
    }

    @Case("(\"test@example.com\") -> ok")
    @Case("(\"user.name+tag@example.co.dk\") -> ok")
    @Case("(\"user_123@test-domain.org\") -> ok")
    @Case("(\"invalid-email\") -> assertion error")
    @Case("(\"hello.com\") -> assertion error")
    @Case("(\"@example.com\") -> assertion error")
    @Case("(\"user@\") -> assertion error")
    @Case("(\"user@domain\") -> assertion error")
    @Case("(\" user@example.com\") -> assertion error")
    @Case("(\"user @example.com\") -> assertion error")
    @Case("(\"user@example.com \") -> assertion error")
    @Case("(\"user@domain..com\") -> assertion error")
    @Case("(\"user@@example.com\") -> assertion error")
    @Case("(\"\") -> assertion error")
    @Case("(null) -> assertion error")
    public static void assertValidEmail(String email) {
        String emailRegex = "^[A-Za-z0-9_+.-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$";
        assert email != null && email.matches(emailRegex);
    }



}