import pytest
from glassbox.failure.classifier import FailureClassifier
from glassbox.types import FailureType, Observation


def test_classify_syntax_error():
    classifier = FailureClassifier()
    obs = Observation(
        content="SyntaxError: invalid syntax at line 2",
        is_error=True,
        metadata={"error_type": "syntax_error"},
    )
    rec = classifier.classify(obs)
    assert rec is not None
    assert rec.failure_type == FailureType.SYNTAX_ERROR
    assert rec.error_signature == "SyntaxError"


def test_classify_rate_limited():
    classifier = FailureClassifier()
    obs = Observation(
        content="HTTP 429 Client Error: Too Many Requests. Rate limit reached.",
        is_error=True,
    )
    rec = classifier.classify(obs)
    assert rec is not None
    assert rec.failure_type == FailureType.RATE_LIMITED


def test_classify_timeout():
    classifier = FailureClassifier()
    obs = Observation(
        content="Execution timed out after 6.0 seconds.",
        is_error=True,
        metadata={"error_type": "execution_timeout"},
    )
    rec = classifier.classify(obs)
    assert rec is not None
    assert rec.failure_type == FailureType.EXECUTION_TIMEOUT


def test_classify_recursion_error():
    classifier = FailureClassifier()
    obs = Observation(
        content="RecursionError: maximum recursion depth exceeded while calling a Python object",
        is_error=True,
    )
    rec = classifier.classify(obs)
    assert rec is not None
    assert rec.failure_type == FailureType.RUNTIME_EXCEPTION
    assert "RecursionError" in (rec.error_signature or "")


def test_classify_irrelevant_result():
    classifier = FailureClassifier()
    obs = Observation(
        content="Search query is too broad or ambiguous. Returned 0 high-confidence results.",
        is_error=True,
        metadata={"error_type": "irrelevant_result"},
    )
    rec = classifier.classify(obs)
    assert rec is not None
    assert rec.failure_type == FailureType.IRRELEVANT_RESULT
