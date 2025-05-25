import signal
from datetime import timedelta
import grpc
from common.gRpc.wallet_service import wallet_pb2, wallet_pb2_grpc
from wallet_service.Core.logger import logger
from wallet_service.app.gRpc.WalletServiceServicer import WalletServiceServicer
from wallet_service.Core.async_kafka_client import async_kafka_client
from celery_workers.background_tasks.tasks import update_currencies
import asyncio


class Service:
    def __init__(self):
        self._is_running = True
        self._background_task = None

    async def update_currencies_event(self):
        while self._is_running:
            try:
                logger.info("Запуск задачи обновления курсов валют")
                update_currencies.delay()
                await asyncio.sleep(timedelta(hours=1).total_seconds())
            except asyncio.CancelledError:
                logger.info("Задача обновления валют остановлена")
                break
            except Exception as e:
                logger.error(f"Ошибка в цикле обновления валют: {str(e)}")
                await asyncio.sleep(60)

    async def _shutdown(self, sig):
        logger.info(f"Получен сигнал {sig.name}, остановка сервиса...")
        self._is_running = False
        if self._background_task:
            self._background_task.cancel()
        await async_kafka_client.close()

    async def serve(self):
        # Обработка сигналов завершения
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig, lambda s=sig: asyncio.create_task(self._shutdown(s))
            )

        try:
            logger.info("Запуск фоновых задач")
            self._background_task = asyncio.create_task(self.update_currencies_event())

            logger.info("Инициализация продюсера Kafka...")
            await async_kafka_client.init_producer()

            logger.info("Запуск gRPC сервера...")
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
            logger.info("Сервер запущен на порту 8004")
            await server.wait_for_termination()

        finally:
            await self._shutdown(signal.SIGTERM)
