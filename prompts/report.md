---
name: report
version: 1
author: BugBountyAI
description: Prompt to summarize scan findings for reporting
min_provider_version: gemini-1.5
---
Generate a summary report from these findings:
"{{ findings }}"

Scan context: "{{ context }}"

Respond with a JSON object.
