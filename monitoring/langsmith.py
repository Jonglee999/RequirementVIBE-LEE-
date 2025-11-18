"""
LangSmith tracing helpers.

Provides a thin shim around ``langsmith.traceable`` so the rest of the codebase
can safely import a decorator even if the optional dependency is not installed
yet (for example, during partial deployments or local tests).
"""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Optional, TypeVar, overload

F = TypeVar("F", bound=Callable[..., Any])


def _identity_decorator(func: F) -> F:
    """Return the function unchanged (used when LangSmith is unavailable)."""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    return wrapper  # type: ignore[return-value]


try:  # pragma: no cover - optional dependency path
    from langsmith import traceable as _traceable  # type: ignore

    def traceable(*args: Any, **kwargs: Any):
        """
        Pass-through wrapper for ``langsmith.traceable`` that also supports being
        used with or without parentheses.
        """

        if args and callable(args[0]) and len(args) == 1 and not kwargs:
            return _traceable(args[0])
        return _traceable(*args, **kwargs)

except Exception:  # pragma: no cover - fallback when langsmith is absent

    def traceable(*args: Any, **kwargs: Any):
        """
        Fallback decorator used when LangSmith is not installed.
        Returns the wrapped function unchanged so the application keeps working.
        """

        if args and callable(args[0]) and len(args) == 1 and not kwargs:
            return _identity_decorator(args[0])

        def decorator(func: F) -> F:
            return _identity_decorator(func)

        return decorator


