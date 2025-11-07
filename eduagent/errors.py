# TODO(zhangzhong): errors could not be easily extracted from the entire codebase
# I need to refactor other components first, and extract errors gradually.


class EduAgentError(Exception):
    """Base class for all EduAgent errors."""


def demo_function(a: int) -> int:
    return a + 1
