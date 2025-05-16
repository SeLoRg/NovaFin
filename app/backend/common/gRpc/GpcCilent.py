from abc import ABC, abstractmethod
from getaway.app.logger import logger
import grpc


class GrpcClient(ABC):
    def __init__(self, url):
        self.url = url
        self._channel: grpc.aio.Channel | None = None

    async def connect(self) -> grpc.aio.Channel | None:
        try:
            logger.info(f"Try create gRpc channel to auth service...")
            channel: grpc.aio.Channel = grpc.aio.insecure_channel(
                self.url,
                options=[
                    ("grpc.keepalive_time_ms", 300000),
                    ("grpc.keepalive_timeout_ms", 10000),
                    ("grpc.http2.max_pings_without_data", 0),  # Неограниченные pings
                    ("grpc.keepalive_permit_without_calls", 1),
                    ("grpc.max_reconnect_backoff_ms", 10000),
                    ("grpc.initial_reconnect_backoff_ms", 1000),
                    ("grpc.enable_retries", 1),
                    ("grpc.max_send_message_length", 50 * 1024 * 1024),
                    ("grpc.max_receive_message_length", 50 * 1024 * 1024),
                ],
            )
            self._channel = channel
            logger.info(f"gRpc channel to auth service create")
            return channel
        except Exception as e:
            logger.error(f"Error during connect to auth service: {str(e)}")
            return None

    async def get_channel(self) -> grpc.aio.Channel | None:
        if self._channel is None:
            logger.info(f"No connection")
            channel: grpc.aio.Channel | None = await self.connect()
            self._channel = channel

        res: grpc.ChannelConnectivity = self._channel.get_state()
        logger.info(f"Connection to {self.url} state: {res}")
        if res not in (
            grpc.ChannelConnectivity.READY,
            grpc.ChannelConnectivity.CONNECTING,
            grpc.ChannelConnectivity.IDLE,
        ):
            logger.info(f"Connection to {self.url} is fault")
            self._channel = await self.connect()

        if res == grpc.ChannelConnectivity.CONNECTING:
            logger.info(f"Connection to {self.url} in CONNECTING state")
            return self._channel

        if self._channel is None:
            logger.error(f"Connection to {self.url} failed after retry.")
            return None

        logger.info(f"Connection to {self.url} is ok")
        return self._channel

    async def close(self):
        if self._channel is not None:
            logger.info(f"Close channel...")
            await self._channel.close()
            self._channel = None

        if self._channel is None:
            logger.info("Channel is closed")

    @abstractmethod
    async def get_stub(self):
        pass
