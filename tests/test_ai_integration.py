from __future__ import annotations

import os
from unittest.mock import MagicMock, patch
import pytest
from typing import Any
from pydantic import BaseModel

# Set dummy key for provider initializations
os.environ["GEMINI_API_KEY"] = "mock-api-key-value"

from core.prompt_manager import PromptManager, parse_prompt_file
from memory.conversation import Conversation, Role
from models.context import ScanContext
from models.finding import Severity
from models.report import AnalysisResult
from models.tool import ToolResult
from core.command import Command
from providers.base import (
    AuthenticationError,
    ContextOverflowError,
    ProviderUnavailableError,
    RateLimitError,
    TimeoutError,
    ValidationError,
)
from providers.gemini import GeminiProvider, map_exception
from engine.analysis.normalizer import Normalizer
from engine.analysis.deduplicator import Deduplicator
from engine.analysis.classifier import Classifier
from engine.analysis.analyzer import Analyzer
from engine.analyst import Analyst
from google.genai.errors import APIError


# ----------------------------------------------------
# 1. Prompt Manager Tests
# ----------------------------------------------------

def test_prompt_manager_parsing():
    content = """---
name: test_prompt
version: 2
author: TestAuthor
description: Test prompt description
created: 2026-07-10
tags: [unit, test]
---
Analyze {{ target_host }} with {{ options }}"""

    template = parse_prompt_file(content)
    assert template.metadata.name == "test_prompt"
    assert template.metadata.version == 2
    assert template.metadata.author == "TestAuthor"
    assert template.metadata.description == "Test prompt description"
    assert "target_host" in template.required_vars
    assert "options" in template.required_vars
    assert len(template.required_vars) == 2


def test_prompt_manager_invalid_frontmatter():
    bad_content = "Analyze {{ host }}"
    with pytest.raises(ValueError, match="Invalid frontmatter"):
        parse_prompt_file(bad_content)


def test_prompt_manager_missing_metadata_field():
    content = """---
name: missing_fields
version: 1
author: test
---
hello {{ world }}"""
    with pytest.raises(ValueError, match="Missing required prompt metadata field"):
        parse_prompt_file(content)


def test_prompt_manager_validation():
    content = """---
name: check_vars
version: 1
author: test
description: test
---
Hello {{ name }}"""
    template = parse_prompt_file(content)
    manager = PromptManager()

    # Pass correct variables
    manager.validate(template, {"name": "Alice"})

    # Missing variables
    with pytest.raises(ValueError, match="Missing required variables"):
        manager.validate(template, {})

    # Unknown variables
    with pytest.raises(ValueError, match="Unknown variables"):
        manager.validate(template, {"name": "Alice", "age": 30})


# ----------------------------------------------------
# 2. Conversation Memory & Trimming Tests
# ----------------------------------------------------

def test_conversation_messages_and_trimming():
    conv = Conversation(max_tokens=50)
    conv.add_message(Role.SYSTEM, "System Prompt")
    conv.add_message(Role.USER, "First user message that is somewhat long")
    conv.add_message(Role.MODEL, "Response")
    conv.add_message(Role.USER, "Latest short prompt")

    # Simple estimator counting word length
    def word_estimator(text: str) -> int:
        return len(text.split())

    # Initial token estimation is around 14 words
    assert len(conv.get_messages()) == 4
    
    # Restrict window to 8 words max, forcing trimming of oldest non-system message
    conv.max_tokens = 8
    conv.trim_history(word_estimator)

    messages = conv.get_messages()
    # Preserves System Prompt [0], trims User Message [1], and preserves rest
    assert messages[0].role == Role.SYSTEM
    assert messages[-1].content == "Latest short prompt"
    assert len(messages) < 4


# ----------------------------------------------------
# 3. Gemini Provider Exception Mapping Tests
# ----------------------------------------------------

def test_gemini_exception_mapping():
    # Mock Google SDK APIError helper
    def make_api_error(status_code: int, msg: str) -> Any:
        err = MagicMock(spec=APIError)
        err.code = status_code
        err.message = msg
        err.__str__.return_value = msg
        return err

    assert isinstance(map_exception(make_api_error(401, "invalid credentials")), AuthenticationError)
    assert isinstance(map_exception(make_api_error(429, "rate limit exceeded")), RateLimitError)
    assert isinstance(map_exception(make_api_error(408, "request timeout")), TimeoutError)
    assert isinstance(map_exception(make_api_error(400, "token context limits exceeded")), ContextOverflowError)
    assert isinstance(map_exception(make_api_error(503, "service unavailable")), ProviderUnavailableError)
    
    # Generic network and connection mapper checks
    assert isinstance(map_exception(ConnectionError("Unreachable socket connection")), ProviderUnavailableError)


@patch("google.genai.Client")
def test_gemini_chat_and_structured_failures(mock_client_cls):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client

    # structured response returns invalid JSON
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "{invalid json"
    mock_model.generate_content.return_value = mock_response
    mock_client.models = mock_model

    provider = GeminiProvider()
    conv = Conversation()
    conv.add_message(Role.USER, "hi")

    class SimpleSchema(BaseModel):
        val: str

    with pytest.raises(ValidationError):
        provider.structured(conv, SimpleSchema)


# ----------------------------------------------------
# 4. Security Analyst Pipeline Tests
# ----------------------------------------------------

def test_analyst_normalizer_and_deduplicator():
    results = [
        ToolResult(
            command=Command(executable="subfinder"),
            success=True,
            exit_code=0,
            stdout="sub.example.com",
            stderr="",
            duration=0.1,
            metadata={"subdomains": ["sub.example.com", "other.example.com"]},
        ),
        ToolResult(
            command=Command(executable="subfinder"),
            success=True,
            exit_code=0,
            stdout="sub.example.com\nother.example.com",
            stderr="",
            duration=0.1,
            metadata={"subdomains": ["sub.example.com"]},
        )
    ]

    normalizer = Normalizer()
    deduplicator = Deduplicator()

    # Normalization outputs raw dicts
    raw_findings = normalizer.normalize(results)
    assert len(raw_findings) == 3

    # Deduplication filters duplicates
    dedup = deduplicator.deduplicate(raw_findings)
    assert len(dedup) == 2
    assert dedup[0]["target"] == "sub.example.com"
    assert dedup[1]["target"] == "other.example.com"


def test_analyst_classifier_severity():
    classifier = Classifier()
    raw = [
        {"tool": "nuclei", "target": "site.com", "severity": "critical", "description": "SQLi"},
        {"tool": "httpx", "target": "site.com", "severity": "unknown", "description": "Port open"},
    ]

    findings = classifier.classify(raw)
    assert findings[0].severity == Severity.CRITICAL
    assert findings[1].severity == Severity.INFO


def test_analyst_fallback_pipeline():
    """Verify orchestrator runs pass-through logic when AI is disabled."""
    normalizer = Normalizer()
    deduplicator = Deduplicator()
    classifier = Classifier()
    analyzer = Analyzer(provider=None, prompt_manager=None)

    analyst = Analyst(
        provider=None,
        prompt_manager=None,
        normalizer=normalizer,
        deduplicator=deduplicator,
        classifier=classifier,
        analyzer=analyzer,
    )

    results = [
        ToolResult(
            command=Command(executable="subfinder"),
            success=True,
            exit_code=0,
            stdout="domain.com",
            stderr="",
            duration=0.1,
            metadata={},
        )
    ]
    context = ScanContext(target="domain.com", workspace="ws", loot_dir="l", report_dir="r")

    analysis_res = analyst.analyze(results, context)
    assert isinstance(analysis_res, AnalysisResult)
    assert len(analysis_res.findings) == 1
    assert analysis_res.findings[0].target == "domain.com"
    assert analysis_res.risk_score == "info"
    assert "AI reasoning is disabled" in analysis_res.summary
