import asyncio
import json
from decimal import Decimal
import async_timeout
from aiokafka.structs import ConsumerRecord, TopicPartition, OffsetAndMetadata
from common.Enums.OperationType import OperationType
from wallet_worker.Core.async_kafka_client import async_kafka_client
from wallet_worker.Core.database_helper import async_database_helper
from wallet_worker.app.services import wallet_service
from wallet_worker.Core.logger import logger
from wallet_worker.exceptions.catch_errors import catch_errors
from common.schemas import (
    WalletTransactionRequest,
    WalletTransactionResult,
)
from wallet_worker.Core.config import settings
from wallet_worker.Core.redis_cli import redis_client


MAX_RETRIES = 3


@catch_errors(logger=logger)
async def handle_message_transaction(msg: ConsumerRecord):
    logger.info(f"--------------Handle-------------------------")
    value_msg_json = msg.value.decode("utf-8")
    logger.info(f"Сообщение от wallet.transaction.request: {value_msg_json}")
    value: WalletTransactionRequest = WalletTransactionRequest(
        **json.loads(msg.value.decode("utf-8"))
    )

    try:
        # Создаем копию сообщения для модификации
        message_data = json.loads(msg.value.decode("utf-8"))

        if message_data.get("retries", 0) >= MAX_RETRIES:
            logger.info(f"Max retries reached, sending to DLQ")
            await async_kafka_client.produce_message(
                topic="wallet.transaction.dlq", message=json.dumps(message_data)
            )
            # Коммитим офсет даже для DLQ
            await async_kafka_client.consumer.commit(
                {
                    TopicPartition(msg.topic, msg.partition): OffsetAndMetadata(
                        msg.offset + 1, ""
                    )
                }
            )
            return

        async with async_database_helper.session_factory() as session:
            try:
                if value.operation == OperationType.DEPOSIT:
                    await wallet_service.deposit(
                        session=session,
                        wallet_id=value.wallet_id,
                        currency_code=value.currency,
                        amount=Decimal(str(value.amount)),
                    )
                elif value.operation == OperationType.WITHDRAW:
                    await wallet_service.withdraw(
                        session=session,
                        wallet_id=value.wallet_id,
                        currency_code=value.currency,
                        amount=Decimal(str(value.amount)),
                    )
                elif value.operation == OperationType.TRANSFER:
                    await wallet_service.transfer(
                        session=session,
                        from_wallet_id=value.wallet_id,
                        to_wallet_id=value.to_wallet_id,
                        currency_code=value.currency,
                        amount=Decimal(str(value.amount)),
                    )
                elif value.operation == OperationType.CONVERT:
                    await wallet_service.convert(
                        session=session,
                        wallet_id=value.wallet_id,
                        from_currency=value.currency,
                        to_currency=value.to_currency,
                        amount=Decimal(str(value.amount)),
                    )

                result = WalletTransactionResult(
                    status="success",
                    correlation_id=value.correlation_id,
                    operation=value.operation,
                    amount=value.amount,
                    wallet_id=value.wallet_id,
                    idempotency_key=value.idempotency_key,
                )
                result = result.to_dict()

                logger.info(
                    f"Сохранение результата операции idemotency_key={value.idempotency_key} в redis..."
                )

                await redis_client.setex(
                    name=f"{settings.REDIS_KEY_IDEMPOTENCY}:{value.idempotency_key}",
                    time=24 * 3600,
                    value=json.dumps(result),
                )

                logger.info(f"Результат сохранен")

                logger.info(f"Отправка результата обработчика в топик")
                await async_kafka_client.produce_message(
                    topic=settings.OUTPUT_TOPIC,
                    message=json.dumps(result),
                )
                logger.info("Сообщение отправлено")

                await session.commit()

                # Явный коммит офсета после успешной обработки
                await async_kafka_client.consumer.commit(
                    {
                        TopicPartition(msg.topic, msg.partition): OffsetAndMetadata(
                            msg.offset + 1, ""
                        )
                    }
                )

                logger.info(f"Сообщение обработалось успешно")
                return result
            except Exception as e:
                await session.rollback()
                # Увеличиваем счетчик retries и отправляем сообщение обратно
                message_data["retries"] = message_data.get("retries", 0) + 1
                logger.info(f"Повторная отправка сообщения в кафку...")
                await async_kafka_client.produce_message(
                    topic=msg.topic, message=json.dumps(message_data)
                )
                logger.info(f"Отправлено")
                # Коммитим текущий офсет
                await async_kafka_client.consumer.commit(
                    {
                        TopicPartition(msg.topic, msg.partition): OffsetAndMetadata(
                            msg.offset + 1, ""
                        )
                    }
                )
                raise

    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {str(e)}", exc_info=True)
        raise


async def consume():
    logger.info("Консюмер запущен")
    logger.info("Инициализация consumer")
    await async_kafka_client.init_consumer(
        group_id="wallet-worker",
        topics=[settings.INPUT_TOPIC],
    )
    logger.info(f"consumer инициализирован")
    logger.info("Инициализация producer")
    await async_kafka_client.init_producer()
    logger.info(f"producer инициализирован")

    try:
        async for msg in async_kafka_client.consumer:
            try:
                async with async_timeout.timeout(30.0):  # Таймаут обработки
                    result = await handle_message_transaction(msg)
                    logger.info(f"Result from wallet.transaction.request: {result}")
                    await async_kafka_client.consumer.commit(
                        {
                            TopicPartition(msg.topic, msg.partition): OffsetAndMetadata(
                                msg.offset + 1, ""
                            )
                        }
                    )
            except asyncio.TimeoutError:
                logger.error("Обработка сообщения превысила таймаут")
                continue

    except Exception as e:
        logger.critical(f"Fatal error in consumer loop: {e}", exc_info=True)
    finally:
        await async_kafka_client.close()

    logger.info("Консюмер остновлен")
