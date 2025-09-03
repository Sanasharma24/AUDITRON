from typing import Callable, List, Optional, Set, Union

import copy
import inspect
import pickle
import sys
from abc import ABC, abstractmethod
from pathlib import Path

import yaml

from auditron.core.core import SMT, TestFunctionMeta
from auditron.core.savable import Artifact
from auditron.core.test_result import TestResult
from auditron.core.validation import configured_validate_arguments
from auditron.exceptions.auditron_exception import python_env_exception_helper
from auditron.registry.registry import get_object_uuid, tests_registry
from auditron.registry.utils import dump_by_value
from auditron.utils.analytics_collector import analytics

DATA_PKL = "data.pkl"

Result = Union[TestResult, bool]


class auditronTest(Artifact[TestFunctionMeta], ABC):
    """
    The base class of all auditron's tests.

    The tests are executed inside the `execute` method. All arguments should be passed in the `__init__` method. It is
    required to set default values for all arguments (either `None` or a default values).
    """

    def __init__(self):
        test_uuid = get_object_uuid(type(self))
        meta = tests_registry.get_test(test_uuid)
        if meta is None:
            # equivalent to adding @test decorator
            from auditron.registry.decorators import test

            test(type(self))
            meta = tests_registry.get_test(test_uuid)
        super(auditronTest, self).__init__(meta)

    @abstractmethod
    def execute(self) -> Result:
        """
        Execute the test
        :return: A TestResult or a bool containing detailed information of the test execution results
        :rtype: Union[TestResult, bool]
        """
        ...

    @classmethod
    def _get_name(cls) -> str:
        return "tests"

    @classmethod
    def _get_meta_class(cls) -> type(SMT):
        return TestFunctionMeta

    def _get_uuid(self) -> str:
        return get_object_uuid(type(self))

    def _save_locally(self, local_dir: Path):
        with open(Path(local_dir) / DATA_PKL, "wb") as f:
            dump_by_value(type(self), f)

    @classmethod
    def _load_meta_locally(cls, local_dir, uuid: str) -> Optional[TestFunctionMeta]:
        meta = tests_registry.get_test(uuid)

        if meta is not None:
            return meta

        with open(local_dir / "meta.yaml", "r", encoding="utf-8") as f:
            return yaml.load(f, Loader=yaml.Loader)

    @classmethod
    def load(cls, local_dir: Path, uuid: str, meta: TestFunctionMeta):
        if local_dir.exists():
            with open(Path(local_dir) / "data.pkl", "rb") as f:
                try:
                    func = pickle.load(f)
                except Exception as e:
                    raise python_env_exception_helper(cls.__name__, e)
        elif meta.module in sys.modules and hasattr(sys.modules[meta.module], meta.name):
            func = getattr(sys.modules[meta.module], meta.name)
        else:
            return None

        if inspect.isclass(func) or hasattr(func, "meta"):
            auditron_test = func()
        elif isinstance(func, auditronTest):
            auditron_test = func
        else:
            auditron_test = auditronTestMethod(func)

        tests_registry.add_func(meta)
        auditron_test.meta = meta

        return auditron_test

    def assert_(self):
        """Wrap execution of the test into a "assert" for unit test executions."""
        result = self.execute()
        if isinstance(result, bool):
            assert result
        else:
            if result.messages:
                message = " ".join([getattr(message, "text", None) or repr(message) for message in result.messages])
            else:
                # Pass more context in case the message is empty
                message = " ".join(str(result).replace("\n", " ").split())

            assert result.passed, message

    @property
    def display_name(self):
        return self.meta.display_name


Function = Callable[..., Result]

Test = Union[auditronTest, Function]


class auditronTestMethod(auditronTest):
    def __init__(self, test_fn: Function) -> None:
        self.args = list()
        self.kwargs = dict()

        self.is_initialized = False
        self.test_fn = test_fn
        test_uuid = get_object_uuid(self.test_fn)
        meta = tests_registry.get_test(test_uuid)

        if meta is None:
            # equivalent to adding @test decorator
            from auditron.registry.decorators import test

            test()(test_fn)
            meta = tests_registry.get_test(test_uuid)

        super(auditronTest, self).__init__(meta)

    def __deepcopy__(self, memo):
        # This is necessary, to avoid deepcopy model, which can have thread lock, or some unpickable object
        # https://stackoverflow.com/questions/53601999/getting-typeerror-cant-pickle-thread-lock-objects-when-an-object-is-deepcopi
        # https://stackoverflow.com/questions/1500718/how-to-override-the-copy-deepcopy-operations-for-a-python-object

        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        filtered_items = [(k, v) for k, v in self.__dict__.items() if k not in ["args", "kwargs"]]
        for k, v in filtered_items:
            setattr(result, k, copy.deepcopy(v, memo))
        result.args = list()
        result.kwargs = dict()
        return result

    def __call__(self, *args, **kwargs) -> "auditronTestMethod":
        instance = copy.deepcopy(self)

        instance.is_initialized = True
        instance.args = args
        instance.kwargs = kwargs

        return instance

    @property
    def dependencies(self) -> Set[Artifact]:
        from inspect import Parameter, signature

        parameters: List[Parameter] = list(signature(self.test_fn).parameters.values())

        return set([param.default for param in parameters if isinstance(param.default, Artifact)])

    @property
    def params(self):
        params = self.kwargs.copy()

        for idx, arg in enumerate(self.args):
            params[next(iter([arg.name for arg in self.meta.args.values() if arg.argOrder == idx]))] = arg

        return params

    def execute(self) -> Result:
        analytics.track("test:execute", {"test_name": self.meta.full_name})

        # if params contains debug then we check if test_fn has debug argument
        if "debug" in self.kwargs and "debug" not in list(inspect.signature(self.test_fn).parameters.keys()):
            self.kwargs.pop("debug")

        return configured_validate_arguments(self.test_fn)(*self.args, **self.kwargs)

    def __repr__(self) -> str:
        if not self.is_initialized:
            hint = "Test object hasn't been initialized, call it by providing the inputs"
        else:
            hint = 'To execute the test call "execute()" method'
        output = [hint]
        if self.params and len(self.params):
            output.append(f"Named inputs: {self.params}")

        return "\n".join(output)

    def _save_locally(self, local_dir: Path):
        with open(Path(local_dir) / "data.pkl", "wb") as f:
            dump_by_value(self.test_fn, f)
