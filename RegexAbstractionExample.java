package jpamb.cases;

import jpamb.utils.Case;

/**
 * Benchmark scenarios specifically designed for Regex (Bricks) Abstraction.
 * Covers: Structure preservation, Suffix checks, and Branch merging.
 */
public class RegexAbstractionExample {

    // Scenario 1: Server Log (Structure: Prefix + Loop + Suffix)
    @Case("(5) -> ok")
    public static void generateServerLog(int msgLength) {
        // 1. Fixed Prefix
        String logEntry = "[INFO] ";

        // 2. Variable Loop Body (Widening)
        String message = ".";
        for (int i = 0; i < msgLength; i++) {
            logEntry = logEntry + message;
        }

        // 3. Fixed Suffix
        logEntry = logEntry + "\n";

        // Verification
        assert logEntry.startsWith("[INFO] ");
        assert logEntry.endsWith("\n");
    }

    // Scenario 2: HTTP Protocol (Suffix Validation)
    @Case("(\"index.html\") -> ok")
    public static void buildHttpRequest(String resource) {
        // 1. Start
        String request = "GET /";

        // 2. Variable Resource
        request = request + resource;

        // 3. Fixed Protocol Version
        request = request + " HTTP/1.1";

        // Verification
        assert request.endsWith(" HTTP/1.1");
    }

    // Scenario 3: SQL Safety (Branch Merging & Keyword Integrity)
    @Case("(true) -> ok")
    public static void checkSqlSafety(boolean isAdmin) {
        String query;

        // 1. Branching
        if (isAdmin) {
            query = "DELETE";
        } else {
            query = "SELECT";
        }

        // 2. Concatenation
        query = query + " * FROM users";

        // Verification
        if (query.contains("DELETE")) {
            System.out.println("Dangerous query detected");
        }
    }
}