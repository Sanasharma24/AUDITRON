from typing import Callable, List, Optional, Type, TypeVar, Union

import functools
import inspect
import sys

from auditron.core.core import TestFunctionMeta
from auditron.registry.decorators_utils import make_all_optional_or_suite_input, set_return_type
from auditron.registry.auditron_test import auditronTest, auditronTestMethod


# TODO: I think this should be moved into auditron_test.py ?
# For slicing_function and transformation_function the decorator is in the same file as the class
def test(
    _fn=None,
    name=None,
    tags: Optional[List[str]] = None,
    debug_description: str = "This debugging session opens one by one all the examples that make the test fail.",
):
    if sys.version_info >= (3, 10):
        import typing as t
    else:
        import typing_extensions as t
    P = t.ParamSpec("P")
    R = TypeVar("R")

    def inner(
        original: Union[Callable[P, R], Type[auditronTest]]
    ) -> Union[Callable[P, auditronTest], auditronTest, auditronTestMethod]:
        """
        Declare output as both Callable and auditronTest so that there's autocompletion
        for auditronTest's methods as well as the original wrapped function arguments (for __call__)
        """
        from auditron.registry.registry import tests_registry

        tests_registry.register(
            TestFunctionMeta(original, name=name, tags=tags, debug_description=debug_description, type="TEST")
        )

        if inspect.isclass(original) and issubclass(original, auditronTest):
            return original

        return _wrap_test_method(original)

    if callable(_fn):
        # in case @test decorator was used without parenthesis
        return functools.wraps(_fn)(inner(_fn))
    else:
        return inner


def _wrap_test_method(original):
    auditron_test_method = functools.wraps(original)(auditronTestMethod(original))
    make_all_optional_or_suite_input(auditron_test_method)
    set_return_type(auditron_test_method, auditronTestMethod)
    return auditron_test_method()
