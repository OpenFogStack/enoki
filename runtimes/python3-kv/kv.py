import os
import typing

import grpc

import fred.middleware_pb2 as fred
import fred.middleware_pb2_grpc as fred_grpc


__keygroup = os.environ.get("__KV_KEYGROUP")
__host = os.environ.get("__KV_HOST")
__node = os.environ.get("__KV_NODE")

if __keygroup is None:
    raise Exception("missing __KV_KEYGROUP")

if __host is None:
    raise Exception("missing __KV_HOST")

if __node is None:
    raise Exception("missing __KV_NODE")

# set up connection to middleware

__channel = grpc.insecure_channel(__host)
__client = fred_grpc.MiddlewareStub(__channel)

# let the middleware know which node we would like to use
cr = fred.ChooseReplicaRequest()
cr.keygroup = __keygroup
cr.nodeId = __node

try:
    __client.ChooseReplica(cr)
except Exception as e:
    print("failed to choose replica")
    print(e)
    raise e


def read(key: str) -> typing.List[str]:
    r = fred.ReadRequest()

    r.keygroup = __keygroup
    r.id = key

    data = __client.Read(r)

    values: typing.List[str] = []

    for item in data.items:
        values.append(item.val)

    return values


def scan(key: str, count: int) -> typing.List[str]:
    r = fred.ScanRequest()

    r.keygroup = __keygroup
    r.id = key
    r.count = count

    data = __client.Scan(r)

    values: typing.List[str] = []

    for item in data.data:
        values.append(item.data)

    return values


def update(key: str, value: str) -> None:
    r = fred.UpdateRequest()

    r.keygroup = __keygroup
    r.id = key
    r.data = value

    __client.Update(r)


def delete(key: str) -> None:
    r = fred.DeleteRequest()

    r.keygroup = __keygroup
    r.id = key

    __client.Delete(r)
