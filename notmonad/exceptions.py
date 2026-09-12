"""Errors raised by notmonad."""


class NotMonadError(Exception):
    """Base class for notmonad errors."""


class CallerConflictError(NotMonadError, TypeError):
    """Raised when a pipeline stack contains more than one caller monad."""


class LoopLimitError(NotMonadError, RuntimeError):
    """Raised when a loop exceeds its configured ``max_steps`` safety limit."""


class MemKeyError(NotMonadError, KeyError):
    """Raised when a memory key is missing and ``__strict=True``."""
