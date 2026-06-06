package com.testpipeline;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Executes rule-based test scenarios on analyzer output.
 */
public class TestRunner {

    /**
     * Runs test scenarios against analyzer output and produces flags and status.
     *
     * @param analyzerOutput JSON string from the Analyzer
     * @return JSON string with flags array and test_status
     */
    public String runScenario(String analyzerOutput) {
        JSONObject input = new JSONObject(analyzerOutput);

        JSONArray flags = new JSONArray();

        int complexityScore = input.getInt("complexity_score");
        boolean hasAssertions = input.getBoolean("has_assertions");
        int lineCount = input.getInt("line_count");

        if (complexityScore > 5) {
            flags.put("high_complexity");
        }
        if (!hasAssertions) {
            flags.put("missing_assertions");
        }
        if (lineCount < 3) {
            flags.put("trivial_input");
        }

        String testStatus = determineTestStatus(flags);

        JSONObject result = new JSONObject(input.toString());
        result.put("flags", flags);
        result.put("test_status", testStatus);

        return result.toString();
    }

    /**
     * Determines overall test status based on raised flags.
     *
     * @param flags array of flag strings
     * @return pass, warn, or fail status
     */
    private String determineTestStatus(JSONArray flags) {
        if (flags.length() == 0) {
            return "pass";
        }

        boolean hasHighComplexity = false;
        boolean hasMissingAssertions = false;
        boolean hasTrivialInput = false;

        for (int i = 0; i < flags.length(); i++) {
            String flag = flags.getString(i);
            if ("high_complexity".equals(flag)) {
                hasHighComplexity = true;
            } else if ("missing_assertions".equals(flag)) {
                hasMissingAssertions = true;
            } else if ("trivial_input".equals(flag)) {
                hasTrivialInput = true;
            }
        }

        if (hasTrivialInput || (hasHighComplexity && hasMissingAssertions)) {
            return "fail";
        }
        if (hasHighComplexity || hasMissingAssertions) {
            return "warn";
        }
        return "pass";
    }
}
