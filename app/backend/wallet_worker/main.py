import asyncio
from wallet_worker.app.kafka_consumer import consume

if __name__ == "__main__":
    asyncio.run(consume())
