# Headless Mobile–Backend Integration Test Framework

A fast, deterministic, cross-platform integration test framework that verifies interaction between mobile production code and backend services **without launching the mobile applications, without Appium, without emulators/simulators, and without UI rendering**.

## Features

- **Zero UI / Headless Execution**: Executes directly on JVM (Android) and Swift/CLI (iOS) in milliseconds.
- **Cross-Platform Behavioral Parity**: Executes identical scenario contracts on both Android and iOS and verifies state & action parity.
- **Dual Execution Modes**:
  - `Controlled Backend Mode`: Uses local mock server and deterministic JSON fixtures.
  - `Real Backend Mode`: Directly targets Alpha, Staging, or Production backends.
- **Action & State Collector**: Captures domain action streams (`AUTH_SUCCESS`, `TASK_LOADED`, `STATE_CHANGED`) and snapshots resulting state.
- **CI/CD Ready**: Emits standard JUnit XML and Markdown summaries for automated PR and release gating.

## Project Structure

```text
mobile-backend-integration-tests/
├── config/                  # Environment endpoints and test account configs
├── scenarios/               # Data-driven cross-platform test scenarios (.yaml)
│   ├── auth/
│   └── tasks/
├── backend/
│   ├── fixtures/            # Reusable JSON response payloads
│   └── simulator/           # Controlled Mock Backend Server
├── adapters/
│   ├── core/                # Platform-agnostic adapter interfaces & models
│   ├── android/             # Android Headless Adapter (JVM / Retrofit / Koin)
│   └── ios/                 # iOS Headless Adapter (Swift / Moya / Settings)
├── action-collector/        # Domain action event recorder
├── state-collector/         # Mobile state snapshot & comparator
├── assertions/              # Cross-Platform Parity Engine
├── reporting/               # JUnit XML & Markdown report generators
├── runner/                  # Unified scenario execution CLI
└── run-tests.sh             # Main entry point script
```

## Quick Start

### 1. Run All Scenarios (Android & iOS against Epsilon Backend)
```bash
./run-tests.sh --platform all --env epsilon
```

### 2. Run Single Platform
```bash
./run-tests.sh --platform android --env epsilon
./run-tests.sh --platform ios --env epsilon
```

### 3. Run against Local Controlled Mock Backend
```bash
./run-tests.sh --platform all --env local-mock
```

### 4. Run against Specific Backend with Custom Credentials
```bash
TEST_USER="your.user@retechlabs.com" TEST_PASSWORD="SecretPassword" \
  ./run-tests.sh --platform all --env staging
```

### 4. Run Specific Scenario
```bash
./run-tests.sh --scenario auth_login_success
./run-tests.sh --scenario get_task_details
```
