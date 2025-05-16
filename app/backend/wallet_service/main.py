import asyncio

from wallet_service.app.gRpc.server import serve

if __name__ == "__main__":
    asyncio.run(serve())
