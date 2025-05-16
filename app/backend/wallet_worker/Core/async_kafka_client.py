from common.kafka.KafkaAsyncClient import KafkaAsyncClient
from wallet_worker.Core.config import settings

async_kafka_client = KafkaAsyncClient(settings.KAFKA_BROKER)
