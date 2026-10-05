"""Explicit failure types for configured OCR text readers."""


class TextReaderUnavailableError(RuntimeError):
    """The configured reader or language data cannot be invoked."""


class TextReaderExecutionError(RuntimeError):
    """The configured reader started but failed during execution."""


class TextReaderLimitError(TextReaderExecutionError):
    """The reader exceeded the shared execution deadline."""
