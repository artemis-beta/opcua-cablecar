import enum
import typing

SERVER_URL = "opc.tcp://127.0.0.1:{port}/freeopcua/server"


def enum_member_str(enumeration: enum.EnumMeta) -> str:
    return str(enumeration).split(".")[-1]


def ignore_no_change(func: typing.Callable) -> None:
    def _inner_func(self, value: typing.Any) -> None:
        if getattr(self, func.__name__) == value:
            return
        func(self, value)

    return _inner_func
