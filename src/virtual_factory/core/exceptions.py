"""Custom exceptions for Virtual Factory."""


class OutputPolicyViolation(RuntimeError):
    """Raised when a signal config violates the output policy rules.

    This prevents internal truth from being published as industrial
    telemetry, which would break architecture rules #6–#8.
    """
