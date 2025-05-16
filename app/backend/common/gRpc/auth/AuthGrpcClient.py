from common.gRpc.GpcCilent import GrpcClient
from common.gRpc.auth import auth_pb2_grpc


class AuthGrpcClient(GrpcClient):
    def __init__(self, url):
        super().__init__(url)

    async def get_stub(self) -> auth_pb2_grpc.AuthServiceStub | None:
        channel = await self.get_channel()
        if channel:
            return auth_pb2_grpc.AuthServiceStub(channel)
        return None
