package com.testpipeline;

import org.json.JSONObject;

/**
 * Core software analysis logic for parsing and analyzing code snippets.
 */
public class Analyzer {

    /**
     * Analyzes a JSON input record and computes software metrics.
     *
     * @param jsonInput JSON string with id, domain, code_snippet, and description fields
     * @return JSON string containing original fields plus computed metrics
     */
    public String analyzeInput(String jsonInput) {
        JSONObject input = new JSONObject(jsonInput);

        String id = input.getString("id");
        String domain = input.getString("domain");
        String codeSnippet = input.getString("code_snippet");
        String description = input.getString("description");

        int lineCount = countLines(codeSnippet);
        int complexityScore = computeComplexityScore(codeSnippet);
        boolean hasAssertions = detectAssertions(codeSnippet);
        String detectedLanguage = detectLanguage(codeSnippet);

        JSONObject result = new JSONObject();
        result.put("id", id);
        result.put("domain", domain);
        result.put("code_snippet", codeSnippet);
        result.put("description", description);
        result.put("line_count", lineCount);
        result.put("complexity_score", complexityScore);
        result.put("has_assertions", hasAssertions);
        result.put("detected_language", detectedLanguage);

        return result.toString();
    }

    /**
     * Counts the number of non-empty lines in a code snippet.
     *
     * @param codeSnippet the source code to analyze
     * @return number of lines
     */
    private int countLines(String codeSnippet) {
        if (codeSnippet == null || codeSnippet.isEmpty()) {
            return 0;
        }
        String[] lines = codeSnippet.split("\\r?\\n");
        return lines.length;
    }

    /**
     * Computes a complexity score based on control-flow keywords.
     *
     * @param codeSnippet the source code to analyze
     * @return count of if/else/for/while/try keywords
     */
    private int computeComplexityScore(String codeSnippet) {
        if (codeSnippet == null || codeSnippet.isEmpty()) {
            return 0;
        }
        String lower = codeSnippet.toLowerCase();
        String[] keywords = {"if", "else", "for", "while", "try"};
        int score = 0;
        for (String keyword : keywords) {
            score += countOccurrences(lower, keyword);
        }
        return score;
    }

    /**
     * Detects whether the snippet contains test assertions.
     *
     * @param codeSnippet the source code to analyze
     * @return true if assertions are present
     */
    private boolean detectAssertions(String codeSnippet) {
        if (codeSnippet == null || codeSnippet.isEmpty()) {
            return false;
        }
        String lower = codeSnippet.toLowerCase();
        return lower.contains("assert")
                || lower.contains("assertequals")
                || lower.contains("asserttrue")
                || lower.contains("assert_false")
                || lower.contains("assertfalse");
    }

    /**
     * Detects the programming language using basic heuristics.
     *
     * @param codeSnippet the source code to analyze
     * @return detected language name or "unknown"
     */
    private String detectLanguage(String codeSnippet) {
        if (codeSnippet == null || codeSnippet.isEmpty()) {
            return "unknown";
        }
        String trimmed = codeSnippet.trim();
        String lower = trimmed.toLowerCase();

        if (lower.contains("def ") || lower.contains("import ") && lower.contains("pytest")
                || lower.contains("self.") || lower.contains("print(")) {
            return "Python";
        }
        if (lower.contains("public class") || lower.contains("private void")
                || lower.contains("system.out") || lower.contains("@test")
                || lower.contains("import java.")) {
            return "Java";
        }
        if (lower.contains("function ") || lower.contains("const ") || lower.contains("let ")
                || lower.contains("=>") || lower.contains("console.log")) {
            return "JS";
        }
        return "unknown";
    }

    /**
     * Counts occurrences of a keyword as a whole word.
     *
     * @param text the text to search
     * @param keyword the keyword to count
     * @return occurrence count
     */
    private int countOccurrences(String text, String keyword) {
        int count = 0;
        int index = 0;
        while ((index = text.indexOf(keyword, index)) != -1) {
            boolean startOk = index == 0 || !Character.isLetterOrDigit(text.charAt(index - 1));
            int endIndex = index + keyword.length();
            boolean endOk = endIndex >= text.length() || !Character.isLetterOrDigit(text.charAt(endIndex));
            if (startOk && endOk) {
                count++;
            }
            index += keyword.length();
        }
        return count;
    }
}
