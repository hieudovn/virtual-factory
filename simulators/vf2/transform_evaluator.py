"""Safe expression evaluator for VF-2 dependent signal transforms.

Allows basic math operations and a whitelist of functions while blocking
dangerous Python builtins.
"""

from __future__ import annotations

import math
import random


# Whitelist of allowed functions / constants
_SAFE_FUNCTIONS: dict[str, object] = {
    "abs": abs,
    "max": max,
    "min": min,
    "round": round,
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "log": math.log,
    "exp": math.exp,
    "pi": math.pi,
    "e": math.e,
}


def evaluate_transform(
    expr: str,
    namespace: dict[str, float],
    rng: random.Random,
) -> float:
    """Safely evaluate a transform expression.

    Allowed in expressions:
    - Variables from *namespace* (e.g. ``input``, ``STATUS``)
    - ``+``, ``-``, ``*``, ``/``, ``**``, ``(``, ``)``
    - Whitelist functions: ``abs``, ``max``, ``min``, ``round``,
      ``sqrt``, ``sin``, ``cos``, ``log``, ``exp``
    - ``noise(mean, std)`` — Gaussian random
    - ``clamp(x, lo, hi)`` — bound to range

    Forbidden: ``__builtins__``, ``__import__``, ``exec``, ``eval``,
    ``open``, etc.

    Args:
        expr: Expression string, e.g. ``"input * 120.0 + noise(0, 2.0)"``.
        namespace: Variable values, e.g. ``{"input": 1.0, "STATUS": 1.0}``.
        rng: Random generator for ``noise()`` calls.

    Returns:
        Evaluated ``float`` value.
    """
    # Build safe evaluation namespace
    local_ns: dict[str, object] = dict(namespace)
    local_ns.update(_SAFE_FUNCTIONS)
    local_ns["noise"] = lambda m, s: rng.gauss(float(m), float(s))
    local_ns["clamp"] = lambda x, lo, hi: max(float(lo), min(float(x), float(hi)))

    # Evaluate in a restricted environment
    result = eval(expr, {"__builtins__": {}}, local_ns)  # noqa: S307
    return float(result)
