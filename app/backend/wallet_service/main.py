import asyncio

from wallet_service.app.gRpc.server import Service

if __name__ == "__main__":
    service = Service()
    asyncio.run(service.serve())
