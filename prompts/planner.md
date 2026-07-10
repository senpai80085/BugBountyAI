---
name: planner
version: 1
author: BugBountyAI
description: Prompt to recommend a scan workflow based on user target objective
min_provider_version: gemini-1.5
---
Analyze the user's objective: "{{ objective }}"
Available tool capabilities: {{ capabilities }}

Select the most appropriate workflow to run from: ['recon'].
Respond with a JSON object matching this schema:
{
  "selected_workflow": "recon",
  "execution_strategy": "parallel",
  "reasoning": "Explain your choice",
  "expected_outputs": ["subdomains.txt"],
  "confidence": 0.95,
  "estimated_duration": 120.0
}
