import json
from typing import AsyncGenerator, Any
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient


class KafkaAsyncClient:
    def __init__(self, kafka_broker: str):
        self.kafka_broker = kafka_broker
        self.producer = None
        self.consumer: AIOKafkaConsumer | None = None
        self.admin_client = None

    async def init_producer(self):
        self.producer = AIOKafkaProducer(bootstrap_servers=self.kafka_broker)
        await self.producer.start()

    async def init_consumer(self, group_id: str, topics: list[str]):
        self.consumer = AIOKafkaConsumer(
            *topics,
            bootstrap_servers=self.kafka_broker,
            group_id=group_id,
            enable_auto_commit=False,  # Отключаем авто-коммит
            auto_offset_reset="earliest",
            max_poll_records=10,  # Уменьшите для теста
            session_timeout_ms=120000,  # Увеличено до 2 минут
            heartbeat_interval_ms=30000,  # 30 секунд
            request_timeout_ms=120000,
            max_poll_interval_ms=300000,  # 5 минут
            security_protocol="PLAINTEXT"
        )
        await self.consumer.start()

    async def init_admin_client(self):
        self.admin_client = AIOKafkaAdminClient(bootstrap_servers=self.kafka_broker)

    async def produce_message(self, topic: str, message: str):
        await self.producer.send_and_wait(topic, message.encode("utf-8"))

    async def consume_messages(self) -> AsyncGenerator[dict[str, Any], None]:
        async for msg in self.consumer:
            data = json.loads(msg.decode("utf-8"))
            yield data

    async def close(self):
        await self.consumer.stop() if self.consumer is not None else None
        await self.producer.stop() if self.producer is not None else None
        await self.admin_client.close() if self.admin_client is not None else None

    async def create_topic(
        self, topic: str, num_partitions: int, replication_factor: int
    ):
        """
        Создание топика в Kafka.
        """
        await self.admin_client.create_topics(
            [topic],
            num_partitions=num_partitions,
            replication_factor=replication_factor,
        )
