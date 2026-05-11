"""QA gate for Module C contract violations (parity with Module A naming)."""


class QAGateFailure(Exception):
    """Raised when a Module C dataset fails contract validation."""
