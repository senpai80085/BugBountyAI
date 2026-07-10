---
name: analysis
version: 1
author: BugBountyAI
description: Prompt to analyze deduplicated findings list
min_provider_version: gemini-1.5
---
Analyze the following list of discovered security findings:
"{{ findings }}"

Triage the findings, validate their impacts, and filter false positives.
Respond with a JSON object matching this schema:
{
  "validated_findings": [
    {
      "tool": "tool_name",
      "target": "example.com",
      "data": {},
      "severity": "medium",
      "description": "Details of validated finding"
    }
  ],
  "reasoning": "Explain your validation reasoning"
}
