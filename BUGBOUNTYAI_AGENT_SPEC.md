# BugBountyAI -- Project Specification (Frozen Architecture)

> Version: 1.0 (Architecture Frozen)

## Purpose

Build a reusable AI-native Bug Bounty Skill/Engine that can be embedded
into AI agents (Hermes, Antigravity, Codex, OpenAI Agents, etc.).

This project is **NOT**: - a web application - a GUI - a standalone
agent framework

It is an extensible execution engine that enables an AI agent to plan,
execute, analyze, and report authorized security assessments.

## Core Principles

-   Production-quality code only.
-   Python 3.12+.
-   Strong typing.
-   SOLID design.
-   No placeholders or TODOs.
-   Small focused modules.
-   Unit tests for every module.
-   Minimal coupling.
-   Dependency injection where appropriate.
-   No architecture changes without explicit approval.

## High-Level Flow

AI Provider → Planner → Workflow Engine → Tool Registry → Tool Plugin →
Executor → Kali Linux → Results → AI Analysis → Report

## Repository Layout

``` text
BugBountyAI/
├── core/
│   ├── config.py
│   ├── logger.py
│   ├── ssh.py
│   ├── executor.py
│   ├── registry.py
│   └── planner.py
├── providers/
│   ├── base.py
│   └── gemini.py
├── tools/
│   ├── base.py
│   ├── subfinder.py
│   ├── httpx.py
│   ├── katana.py
│   ├── naabu.py
│   ├── nuclei.py
│   └── ...
├── workflows/
├── prompts/
├── config/
├── reports/
├── loot/
├── tests/
└── README.md
```

## Responsibilities

### core/config.py

Loads YAML configuration and environment variables.

### core/logger.py

Central logging only.

### core/ssh.py

Persistent Paramiko connection. No business logic.

### core/executor.py

Single abstraction for command execution.

Required interface:

-   run(command)
-   upload(local, remote)
-   download(remote, local)

Only Executor may communicate with SSH.

### core/registry.py

Automatically discovers tools. Planner never imports tools directly.

### core/planner.py

Receives an objective. Chooses workflow. Invokes tools through the
registry. Never executes shell commands directly.

## AI Providers

Every provider must expose the same interface:

-   chat()
-   stream()
-   set_system_prompt()
-   clear_history()

Current: - Gemini

Future: - OpenAI - Anthropic - Ollama - OpenRouter - DeepSeek

Planner must not depend on a specific provider.

## Tool Contract

Every tool inherits Tool.

Required methods:

-   validate()
-   build()
-   parse()
-   execute()

Tools never call Paramiko.

Tools only call Executor.

Each tool performs exactly one task.

## Executor Contract

Executor hides execution backend.

Future backends: - SSH - Local - Docker

Tool code must not change when backend changes.

## Workflows

Workflows are YAML.

Example:

``` yaml
name: recon

steps:
  - subfinder
  - httpx
  - katana
  - naabu
  - nuclei
```

No workflow logic is hardcoded in Python.

## Remote Execution

Commands execute on Kali.

Temporary working directory:

/tmp/bugbounty/`<target>`{=html}/

Results are copied back into:

loot/

Never pass Windows paths to Kali commands.

## Reporting

Generate: - Markdown - JSON

Future: - HTML

## Coding Rules

-   One class = one responsibility.
-   Never duplicate logic.
-   Never redesign architecture automatically.
-   Preserve backward compatibility.
-   Keep functions small.
-   Prefer composition over inheritance.

## Testing

Every module requires tests.

Tests must: - create their own data - clean up after execution - avoid
external state where possible

## Security Scope

This framework is intended for authorized security assessments only. Do
not include functionality intended to bypass authorization or automate
exploitation beyond explicitly permitted testing.

## Development Order (Frozen)

1.  Tool Base
2.  Registry
3.  Executor
4.  Provider Base
5.  Gemini Provider
6.  Planner
7.  Tool Plugins
8.  Workflow Engine
9.  AI Analysis
10. Reporting

Never skip layers.

## Definition of Done

A module is complete only if: - implementation finished - tests pass -
imports clean - documented - no lint/type errors introduced

## Agent Instructions

Before changing code:

1.  Read the repository.
2.  Read this document.
3.  Preserve architecture.
4.  Implement only the requested module.
5.  Run tests.
6.  Fix failures.
7.  Do not refactor unrelated code.
8.  Ask before any architectural change.
