# Live Real-Time Test Progress Setup Guide

This guide explains how to configure automation repositories (`retech-web-automation`, `retech-mobile-automation`, `retech-api-automation`) to emit real-time progress markers during CI test execution. The Automation Dashboard parses these tokens directly from GitHub Actions logs to show live execution bars, currently executing tests, and pass/fail counts.

---

## 1. TestNG Listener (`LiveTestNGListener.java`)

Add this listener to your test framework (e.g. `src/test/java/com/retech/listeners/LiveTestNGListener.java`):

```java
package com.retech.listeners;

import org.testng.ISuite;
import org.testng.ISuiteListener;
import org.testng.ITestListener;
import org.testng.ITestResult;

import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Emits real-time test execution progress tokens to console stdout and GitHub Step Summary.
 */
public class LiveTestNGListener implements ITestListener, ISuiteListener {
    private static final boolean IS_CI = "true".equalsIgnoreCase(System.getenv("GITHUB_ACTIONS"));
    private static final String REPO_KEY = System.getenv().getOrDefault("DASHBOARD_REPO_KEY", "web");
    private static final String RUN_ID = System.getenv().getOrDefault("GITHUB_RUN_ID", "local");
    
    private final AtomicInteger total = new AtomicInteger(0);
    private final AtomicInteger completed = new AtomicInteger(0);
    private final AtomicInteger passed = new AtomicInteger(0);
    private final AtomicInteger failed = new AtomicInteger(0);
    private final AtomicInteger skipped = new AtomicInteger(0);

    @Override
    public void onStart(ISuite suite) {
        int count = suite.getAllMethods().size();
        total.set(count);
        emitProgress("SUITE_STARTED", "Suite initialized with " + count + " tests");
    }

    @Override
    public void onTestStart(ITestResult result) {
        String testIdentifier = formatTestName(result);
        emitProgress("TEST_RUNNING", testIdentifier);
    }

    @Override
    public void onTestSuccess(ITestResult result) {
        passed.incrementAndGet();
        completed.incrementAndGet();
        emitProgress("TEST_PASSED", formatTestName(result));
    }

    @Override
    public void onTestFailure(ITestResult result) {
        failed.incrementAndGet();
        completed.incrementAndGet();
        String error = result.getThrowable() != null ? result.getThrowable().getMessage() : "Assertion/Execution failure";
        emitProgress("TEST_FAILED", formatTestName(result) + " — " + error);
    }

    @Override
    public void onTestSkipped(ITestResult result) {
        skipped.incrementAndGet();
        completed.incrementAndGet();
        emitProgress("TEST_SKIPPED", formatTestName(result));
    }

    @Override
    public void onFinish(ISuite suite) {
        emitProgress("SUITE_COMPLETED", "Suite execution completed");
    }

    private String formatTestName(ITestResult result) {
        return result.getTestClass().getRealClass().getSimpleName() + "#" + result.getMethod().getMethodName();
    }

    private void emitProgress(String status, String details) {
        int c = completed.get();
        int t = Math.max(total.get(), c);
        int p = passed.get();
        int f = failed.get();
        int s = skipped.get();
        double pct = t > 0 ? ((double) c / t) * 100.0 : 0.0;

        // Structured JSON payload formatted on a single line
        String json = String.format(
            "{\"repo\":\"%s\",\"runId\":\"%s\",\"status\":\"%s\",\"details\":\"%s\",\"completed\":%d,\"total\":%d,\"passed\":%d,\"failed\":%d,\"skipped\":%d,\"percent\":%.1f,\"timestamp\":%d}",
            REPO_KEY, RUN_ID, status, escape(details), c, t, p, f, s, pct, System.currentTimeMillis() / 1000
        );

        // Standard token prefix detected by the dashboard live log parser
        System.out.println("[QA_LIVE_PROGRESS] " + json);
        System.out.flush();

        // Optional: Update GitHub Step Summary for GitHub UI viewers
        String summaryFile = System.getenv("GITHUB_STEP_SUMMARY");
        if (IS_CI && summaryFile != null && !summaryFile.isBlank()) {
            writeStepSummary(summaryFile, t, c, p, f, s, pct, details);
        }
    }

    private void writeStepSummary(String path, int t, int c, int p, int f, int s, double pct, String details) {
        try (PrintWriter out = new PrintWriter(new FileWriter(path, false))) {
            out.println("### 🧪 Live Test Execution Progress");
            out.printf("- **Status:** `%.1f%%` (%d / %d completed)%n", pct, c, t);
            out.printf("- **Passed:** %d | **Failed:** %d | **Skipped:** %d%n", p, f, s);
            out.printf("- **Current:** `%s`%n", details);
        } catch (IOException ignored) {}
    }

    private String escape(String s) {
        if (s == null) return "";
        return s.replace("\"", "'").replace("\n", " ").replace("\r", "");
    }
}
```

---

## 2. Registering in `testng.xml`

In your test suite configuration file (`testng.xml`):

```xml
<suite name="Automation Regression Suite">
    <listeners>
        <listener class-name="com.retech.listeners.LiveTestNGListener"/>
    </listeners>
    <test name="Web Tests">
        <!-- package or test classes -->
    </test>
</suite>
```

---

## 3. GitHub Actions Workflow Configuration

In `.github/workflows/test.yml`:

```yaml
- name: Run TestNG Suite
  env:
    DASHBOARD_REPO_KEY: "web" # Use "web", "mobile-ios", "mobile-android", or "api"
  run: mvn clean test -DsuiteXmlFile=testng.xml
```

---

## 4. How the Dashboard Tracks It

1. The Dashboard's `live-tracker.js` queries `https://api.github.com/repos/{owner}/{repo}/actions/runs?status=in_progress`.
2. When a workflow run is in progress, it fetches the active job's live stdout log stream.
3. It parses the latest `[QA_LIVE_PROGRESS]` JSON line.
4. The dashboard immediately renders:
   - Live Glowing Status Badge (`🟢 Web Automation RUNNING`)
   - Real-time animated progress bar (`X / Y` tests, percentage)
   - Currently running test name & last 50 log lines
   - Real-time Estimated Time Remaining (ETA) based on average test duration.
5. When the run finishes, the dashboard automatically transitions to the final Allure report snapshot.
