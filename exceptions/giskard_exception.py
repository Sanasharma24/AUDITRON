from typing import Optional, Tuple

import platform


class auditronException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class auditronPythonEnvException(auditronException):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class auditronPythonVerException(auditronPythonEnvException):
    def __init__(self, cls_name, e, required_py_ver, *args: object) -> None:
        super().__init__(
            f"Failed to load '{cls_name}' due to {e.__class__.__name__}.\n"
            f"Make sure you are loading it in the environment with matched Python version (required {required_py_ver}, loading with {platform.python_version()}).",
            *args,
        )


class auditronPythonDepException(auditronPythonEnvException):
    def __init__(self, cls_name, e, *args: object) -> None:
        super().__init__(
            f"Failed to load '{cls_name}' due to {e.__class__.__name__}.\n"
            "Make sure you are loading it in the environment with matched dependencies.",
            *args,
        )


def python_env_exception_helper(cls_name, e: Exception, required_py_ver: Optional[Tuple[str, str, str]] = None):
    if required_py_ver is not None and required_py_ver[:2] != platform.python_version_tuple()[:2]:
        # Python major and minor versions are not matched
        # Notice that there could be some false positive, check: https://github.com/auditron-AI/auditron/pull/1620
        return auditronPythonVerException(cls_name, e, required_py_ver=required_py_ver)
    # We assume the other cases as the dependency issues
    return auditronPythonDepException(cls_name, e)
