# BugBountyAI Analyst Pipeline

This document describes the modular architecture of the Security Analyst engine.

---

## 1. Triage Pipeline Flow

The [`Analyst`](file:///c:/BugBountyAI/engine/analyst.py) orchestrator runs tool results through a sequence of five decoupled processing stages:

```text
       Raw Tool Results List (ToolResult)
                     │
                     ▼
           1. Normalization Stage (normalizer.py)
                     │
                     ▼
          2. Deduplication Stage (deduplicator.py)
                     │
                     ▼
           3. Classification Stage (classifier.py)
                     │
                     ▼
            4. AI Validation Stage (analyzer.py)
                     │
                     ▼
          5. Risk Score Categorization (analyst.py)
```

---

## 2. Pipeline Stage Stages

1. **Normalizer**: Extracts raw finding dicts from tool metadata results or standard output logs.
2. **Deduplicator**: Filters out redundant finding hashes based on tool name, target hostname, and description keywords.
3. **Classifier**: Converts raw dicts into strongly typed `Finding` objects, mapping severity strings to the `Severity` Enum.
4. **Analyzer**: Queries the AI provider using a structured validation schema (`AnalysisDecision`) to check for false positives. If the AI is disabled, it acts as a pass-through validating all findings automatically.
5. **Risk Score**: Evaluates the highest priority finding severity and assigns it as the overall `risk_score` (critical, high, medium, low, info) to the [`AnalysisResult`](file:///c:/BugBountyAI/models/report.py).
