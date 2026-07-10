\# BugBountyAI Development Rules



\## Objective



Build a reusable AI-native Bug Bounty engine that integrates with Hermes and other AI agents.



This is NOT a web app.

This is NOT a CLI framework.



The repository is an AI Skill / Engine.



\---



\## Principles



\- Production quality only

\- SOLID architecture

\- Type hints everywhere

\- Modular plugins

\- No duplicated code

\- Small focused classes

\- Unit tests for every module

\- No breaking existing interfaces

\- No placeholders

\- No TODOs

\- No hardcoded paths

\- Never redesign architecture without approval



\---



\## Architecture



core/

providers/

tools/

workflows/

prompts/

tests/



\---



\## Executors



Only Executor may communicate with SSH.



No tool may import Paramiko.



\---



\## Providers



Every provider implements the same interface.



Gemini is the first provider.



Future:



\- OpenAI

\- Claude

\- Ollama

\- OpenRouter



\---



\## Tools



Every tool inherits Tool.



Tool interface:



validate()



build()



parse()



execute()



Never execute commands directly.



Always use Executor.



\---



\## Planner



Planner decides which tool to run.



Planner never imports tools directly.



Planner only uses Registry.



\---



\## Registry



Registry auto-discovers tools.



No manual imports.



\---



\## Workflows



Stored as YAML.



Never hardcode workflows.



\---



\## Code Style



Python 3.12+



PEP8



Docstrings



Type hints



Small functions



Dependency Injection



No global mutable state



\---



Before writing code:



1\. Read existing code.

2\. Preserve architecture.

3\. Make minimal changes.

4\. Keep tests passing.

