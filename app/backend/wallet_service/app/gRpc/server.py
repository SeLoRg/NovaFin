import grpc
from common.gRpc.wallet_service import wallet_pb2, wallet_pb2_grpc
from wallet_service.Core.logger import logger
from wallet_service.app.gRpc.WalletServiceServicer import WalletServiceServicer
from wallet_service.Core.async_kafka_client import async_kafka_client


async def serve():
    try:
        logger.info(f"Инициализация продюсера...")
        await async_kafka_client.init_producer()
        logger.info(f"Продюсер инициализирован")
        server = grpc.aio.server(
            options=[
                (
                    "grpc.http2.max_pings_without_data",
                    0,
                ),  # бесконечно (разрешить пинги без вызовов)
                (
                    "grpc.http2.min_time_between_pings_ms",
                    300000,
                ),  # не чаще, чем раз в 15 минут
                ("grpc.keepalive_time_ms", 600000),  # пинг каждые 60 сек
                ("grpc.keepalive_timeout_ms", 20000),  # ждать 20 сек ответа на пинг
                (
                    "grpc.keepalive_permit_without_calls",
                    True,
                ),  # пинговать можно даже без вызовов
            ]
        )
        wallet_pb2_grpc.add_WalletServiceServicer_to_server(
            WalletServiceServicer(), server
        )
        server.add_insecure_port("[::]:8004")
        await server.start()
        logger.info("Сервер запущен")
        await server.wait_for_termination()

    finally:
        logger.info(f"Остановка kafka produser/consumer...")
        await async_kafka_client.close()
        logger.info(f"kafka client закрыт")
        logger.info(f"Сервер остановлен")
