"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
"""
import builtins
import google.protobuf.descriptor
import google.protobuf.message
import sys

if sys.version_info >= (3, 8):
    import typing as typing_extensions
else:
    import typing_extensions

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor

@typing_extensions.final
class Data(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    FUNCTIONIDENTIFIER_FIELD_NUMBER: builtins.int
    DATA_FIELD_NUMBER: builtins.int
    functionIdentifier: builtins.str
    data: builtins.str
    def __init__(
        self,
        *,
        functionIdentifier: builtins.str = ...,
        data: builtins.str = ...,
    ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal["data", b"data", "functionIdentifier", b"functionIdentifier"]) -> None: ...

global___Data = Data

@typing_extensions.final
class Response(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor

    RESPONSE_FIELD_NUMBER: builtins.int
    response: builtins.str
    def __init__(
        self,
        *,
        response: builtins.str = ...,
    ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal["response", b"response"]) -> None: ...

global___Response = Response
