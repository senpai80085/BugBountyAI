---
name: triage
version: 1
author: BugBountyAI
description: Prompt to evaluate risk severity and classify findings
min_provider_version: gemini-1.5
---
Triage and assess the severity classification for this finding data:
"{{ finding_data }}"

Respond with a JSON object matching this schema:
{
  "severity": "medium",
  "justification": "Explain why this severity was assigned"
}
