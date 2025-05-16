from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker


class Database:
    def __init__(self, url, echo):
        self.engine = create_async_engine(url=url, echo=echo)
        self.session_factory = async_sessionmaker(
            bind=self.engine, autoflush=False, autocommit=False
        )

    async def get_async_session(self) -> AsyncSession:
        async with self.session_factory() as sess:
            yield sess
