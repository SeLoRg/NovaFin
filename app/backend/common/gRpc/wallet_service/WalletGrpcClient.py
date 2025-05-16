from common.gRpc.GpcCilent import GrpcClient
from common.gRpc.wallet_service import wallet_pb2_grpc


class WalletGrpcClient(GrpcClient):
    def __init__(self, url):
        super().__init__(url)

    async def get_stub(self) -> wallet_pb2_grpc.WalletServiceStub | None:
        channel = await self.get_channel()
        if channel:
            return wallet_pb2_grpc.WalletServiceStub(channel)
        return None
