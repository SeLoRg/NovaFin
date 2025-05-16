import asyncio
from auth.app.gRpc.server import serve


if __name__ == "__main__":
    asyncio.run(serve())
