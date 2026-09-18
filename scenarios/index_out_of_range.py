"""Scenario 2: Binary search with boundary condition off-by-one bug causing IndexError."""

BROKEN_SNIPPET = """
def binary_search(arr, target):
    left = 0
    right = len(arr) # Off by one bug: should be len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1

items = [10, 20, 30, 40, 50]
print(binary_search(items, 99))
"""

TASK_DESCRIPTION = (
    "Debug and fix an IndexError in binary search off-by-one index boundary:\n"
    "```python\n"
    "def binary_search(arr, target):\n"
    "    left = 0\n"
    "    right = len(arr)\n"
    "    while left <= right:\n"
    "        mid = (left + right) // 2\n"
    "        if arr[mid] == target: return mid\n"
    "        elif arr[mid] < target: left = mid + 1\n"
    "        else: right = mid - 1\n"
    "    return -1\n"
    "print(binary_search([10, 20, 30, 40, 50], 99))\n"
    "```"
)
