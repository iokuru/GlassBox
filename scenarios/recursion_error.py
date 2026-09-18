"""Scenario 1: Recursive Fibonacci with missing base case causing RecursionError."""

BROKEN_SNIPPET = """
def fib(n):
    return fib(n - 1) + fib(n - 2)

print(fib(5))
"""

TASK_DESCRIPTION = (
    "Debug and fix the following recursive Fibonacci function that is crashing with maximum recursion depth:\n"
    "```python\n"
    "def fib(n):\n"
    "    return fib(n - 1) + fib(n - 2)\n"
    "print(fib(5))\n"
    "```"
)
