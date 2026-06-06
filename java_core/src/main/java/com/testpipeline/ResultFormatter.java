package com.testpipeline;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.stream.Collectors;

/**
 * Formats test runner output into a final JSON envelope and provides the CLI entry point.
 */
public class ResultFormatter {

    /**
     * Wraps test runner output in a standardized result envelope.
     *
     * @param testRunnerOutput JSON string from the TestRunner
     * @return formatted JSON envelope string
     */
    public String format(String testRunnerOutput) {
        JSONObject input = new JSONObject(testRunnerOutput);

        JSONObject metrics = new JSONObject();
        metrics.put("line_count", input.getInt("line_count"));
        metrics.put("complexity_score", input.getInt("complexity_score"));
        metrics.put("has_assertions", input.getBoolean("has_assertions"));
        metrics.put("detected_language", input.getString("detected_language"));

        JSONArray flags = input.getJSONArray("flags");

        JSONObject envelope = new JSONObject();
        envelope.put("record_id", input.getString("id"));
        envelope.put("domain", input.getString("domain"));
        envelope.put("metrics", metrics);
        envelope.put("flags", flags);
        envelope.put("test_status", input.getString("test_status"));
        envelope.put("processed_at", Instant.now().toString());

        return envelope.toString();
    }

    /**
     * Main entry point: reads JSON from stdin, chains pipeline stages, prints result to stdout.
     *
     * @param args command-line arguments (unused)
     */
    public static void main(String[] args) {
        try {
            BufferedReader reader = new BufferedReader(
                    new InputStreamReader(System.in, StandardCharsets.UTF_8));
            String jsonInput = reader.lines().collect(Collectors.joining("\n"));

            if (jsonInput.trim().isEmpty()) {
                System.err.println("Error: No input provided on stdin");
                System.exit(1);
            }

            Analyzer analyzer = new Analyzer();
            TestRunner testRunner = new TestRunner();
            ResultFormatter formatter = new ResultFormatter();

            String analyzed = analyzer.analyzeInput(jsonInput);
            String tested = testRunner.runScenario(analyzed);
            String formatted = formatter.format(tested);

            System.out.println(formatted);
        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
            System.exit(1);
        }
    }
}
