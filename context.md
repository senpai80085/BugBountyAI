Use this as the **first prompt** in Antigravity/GSD.

```md
# PROJECT CONTEXT

You are building the core engine for an AI-native Bug Bounty Skill.

This is a long-term production project.

Read the repository completely before making changes.

Read AGENTS.md and ARCHITECTURE.md first.

Do NOT redesign the architecture.

---

# WHAT THIS PROJECT IS

This project is NOT:

- a web application
- a dashboard
- a GUI
- a CLI framework
- another AI agent

This project IS:

A reusable AI Bug Bounty Engine (Skill) that can be embedded inside any AI agent.

Examples:

- Hermes
- Antigravity
- Codex
- Claude Code
- OpenHands
- OpenAI Agents
- Custom AI Agents

The engine should be completely independent from the AI framework.

Any AI should be able to import this engine and use it.

---

# FINAL GOAL

The final user experience should look like this:

bugbounty example.com

or

Scan example.com

or

Perform a complete reconnaissance of example.com

The AI agent understands the request.

The AI calls this engine.

The engine performs the complete assessment.

The AI returns a structured report.

The AI should not need to know how individual tools work.

The engine handles everything.

---

# HOW IT WORKS

User

↓

AI Agent

↓

BugBounty Engine

↓

Planner

↓

Workflow Engine

↓

Tool Registry

↓

Tool Plugins

↓

Executor

↓

SSH

↓

Kali Linux

↓

Security Tools

↓

Results

↓

AI Analysis

↓

Report

↓

User

---

# EXECUTION

The engine never executes tools locally.

The engine connects through SSH to a dedicated Kali Linux VM.

Current environment:

Windows Host

↓

SSH

↓

Kali Linux VM

The SSH layer already exists.

Executor is responsible for execution.

Only Executor may communicate with SSH.

No other module may use Paramiko.

---

# KALI LINUX

The Kali machine contains tools such as

subfinder

httpx

naabu

katana

nuclei

ffuf

amass

gau

waybackurls

dnsx

tlsx

assetfinder

hakrawler

sqlmap

wpscan

nikto

feroxbuster

dirsearch

and future tools.

The engine must be able to support unlimited future tools.

---

# TOOL DESIGN

Every tool is its own plugin.

Example

tools/

subfinder.py

httpx.py

katana.py

naabu.py

nuclei.py

Every tool inherits Tool.

Every tool has exactly one responsibility.

Every tool only builds commands.

Executor executes commands.

---

# PLANNER

The Planner is the brain.

The planner decides

which workflow

which tool

tool order

tool arguments

parallel execution

next action

The planner NEVER imports tool modules directly.

The planner only communicates with the Registry.

---

# REGISTRY

Registry automatically discovers tool plugins.

No manual imports.

Dropping a new file inside

tools/

should automatically register it.

---

# WORKFLOW ENGINE

No workflow logic is hardcoded.

Everything is YAML.

Example

Recon

↓

subfinder

↓

httpx

↓

katana

↓

naabu

↓

nuclei

Tomorrow we may add

API workflow

GraphQL workflow

Mobile workflow

WordPress workflow

Cloud workflow

No Python code should change.

Only YAML.

---

# AI

AI is used for reasoning.

NOT execution.

Responsibilities

Understand user objective.

Choose workflow.

Analyze tool output.

Decide next action.

Identify anomalies.

Prioritize findings.

Summarize results.

Generate reports.

Future AI providers

Gemini

OpenAI

Claude

OpenRouter

Ollama

DeepSeek

Changing AI provider must not require code changes.

---

# REPORTS

Reports should include

Executive Summary

Target Information

DNS

Subdomains

Alive Hosts

Technologies

Open Ports

Interesting URLs

JavaScript Files

Potential Vulnerabilities

Confirmed Findings

Risk Levels

CVSS

Proof of Concept

Reproduction Steps

References

Recommendations

Markdown

JSON

Future HTML/PDF

---

# FUTURE

The engine should eventually support

parallel execution

multiple targets

multiple SSH executors

Docker executors

local executors

distributed scanning

plugin marketplace

custom workflows

custom AI providers

memory

historical scans

continuous monitoring

scheduled scans

---

# DEVELOPMENT RULES

Never redesign architecture.

Never break interfaces.

One module at a time.

One responsibility per class.

Strong typing.

Docstrings.

Unit tests.

No placeholders.

No TODOs.

No duplicated code.

Always preserve backwards compatibility.

Run tests after every completed module.

Stop after completing the requested layer.

Never implement future layers without approval.

If architecture changes appear necessary,

STOP

Explain the reason

Wait for approval.

---

# OBJECTIVE

Build a production-quality reusable Bug Bounty Engine that can become the security skill used by any AI agent.

The AI agent should simply ask:

"Perform bug bounty reconnaissance on example.com"

and this engine should autonomously:

- Plan the workflow
- Execute tools on Kali over SSH
- Collect outputs
- Analyze findings with AI
- Decide follow-up actions
- Generate professional reports

without the AI agent needing to know anything about individual security tools.
