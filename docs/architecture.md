# Target Architecture: AI-Powered Universal SDET Framework

This document outlines the architectural blueprint for the AI-Powered Universal SDET Automation Framework, adapted from the HexStrike AI core.

## 1. High-Level System Architecture

The framework uses a modular, config-driven approach where AI agents interact with specialized testing tools via the Model Context Protocol (MCP).

```mermaid
graph TD
    User[QA Engineer / AI Agent] -->|Config/Prompt| Core[Core Engine]
    subgraph "Framework Core"
        Core --> Config[Config Loader]
        Core --> Data[Test Data Manager]
        Core --> Healer[AI Locator Healer]
        Core --> Analysis[AI Failure Analyzer]
    end

    subgraph "Execution Layer"
        Core --> PW[Playwright Runner]
        PW --> Browser[Browser Instances]
        PW --> API[API Clients]
    end

    subgraph "Intelligence Layer (MCP)"
        MCP[MCP Server] --> Tools[Safe Testing Tools]
        Tools --> UI_Tool[run_ui_test]
        Tools --> API_Tool[run_api_test]
        Tools --> DOM_Tool[inspect_dom]
        Tools --> Trace_Tool[analyze_trace]
    end

    Core --> MCP
    PW --> Reports[Allure Reports]
    PW --> Traces[Playwright Traces]
```

## 2. AI Locator Healing Flow

When a selector fails, the framework doesn't just stop; it attempts to "heal" the locator using LLM intelligence.

```mermaid
sequenceDiagram
    participant PW as Playwright Runner
    participant Healer as AI Healer
    participant LLM as LLM (OpenAI/Local)

    PW->>PW: Selector Timeout/Failure
    PW->>Healer: Trigger Healing (Failed Selector + DOM Snapshot)
    Healer->>Healer: Extract Context (ARIA, Labels, Context)
    Healer->>LLM: Prompt: "Suggest fix for this locator"
    LLM-->>Healer: Suggested New Locators (getByRole, etc.)
    Healer->>PW: Attempt New Locators
    alt Success
        PW-->>User: Test Continues (Log healing event)
    else Failure
        PW-->>User: Final Test Failure Report
    end
```

## 3. AI Failure Analysis Flow

Post-execution, AI analyzes artifacts to provide actionable insights into why a test failed.

```mermaid
graph LR
    Fail[Test Failure] --> Collect[Collect Artifacts]
    subgraph Artifacts
        A1[Screenshots]
        A2[Traces]
        A3[Console Logs]
        A4[Network Logs]
        A5[Stack Trace]
    end
    Collect --> A1 & A2 & A3 & A4 & A5
    A1 & A2 & A3 & A4 & A5 --> AI[AI Analyzer]
    AI --> Output[Failure Report]
    subgraph Report Details
        O1[Likely Reason]
        O2[Suggested Fix]
        O3[Confidence Score]
        O4[Category: Bug/Data/Env/Locator]
    end
    Output --> O1 & O2 & O3 & O4
```

## 4. MCP Testing Tool Flow

MCP exposes Playwright-based tools to AI agents in a controlled, safe manner.

```mermaid
graph TD
    Agent[AI Agent] -->|Request Tool| Server[MCP Server]
    subgraph "Safe Toolset"
        Server --> T1[run_ui_test]
        Server --> T2[inspect_dom]
        Server --> T3[generate_test]
        Server --> T4[analyze_trace]
    end
    T1 & T2 & T3 & T4 --> PW[Playwright Environment]
    PW --> Target[Authorized App Under Test]
```

## 5. CI/CD Pipeline

The framework is designed for modern DevOps environments, integrating seamlessly with GitHub Actions.

```mermaid
graph TD
    Push[Code Push] --> Trigger[GitHub Actions Trigger]
    Trigger --> Setup[Setup Node.js & Playwright]
    Setup --> Tests[Run Tests via Universal Config]
    Tests --> Results{Test Results}
    Results -->|Fail| Heal[AI Failure Analysis & Log]
    Results -->|Pass/Fail| Allure[Generate Allure Report]
    Allure --> Artifacts[Upload Allure & Traces]
    Artifacts --> Notify[Slack/Teams Notification]
```
