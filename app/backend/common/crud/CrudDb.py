from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete, exc, Result
from typing import Type, TypeVar, List, Optional

T = TypeVar("T")


class CRUD:
    @staticmethod
    async def get_by_filter(
        session: AsyncSession,
        model: Type[T],
        limit: int = 100,
        skip: int = 0,
        **filters,
    ) -> List[T]:
        try:
            filters_conditions = [
                getattr(model, key) == value for key, value in filters.items()
            ]
            stmt = select(model).limit(limit).offset(skip)

            if filters_conditions:
                stmt = stmt.filter(*filters_conditions)

            res: Result = await session.execute(stmt)
            result_list: List[T] = list(res.scalars().all())

            return result_list
        except exc.NoResultFound as e:
            return list()
        except exc.SQLAlchemyError as e:
            raise ValueError(f"Failed to get {model.__name__}: {str(e)}")

    @staticmethod
    async def create(session: AsyncSession, model: Type[T], **kwargs) -> T:
        try:
            new_object: T = model(**kwargs)
            session.add(new_object)
            await session.flush()
            await session.refresh(new_object)
            return new_object
        except exc.SQLAlchemyError as e:
            raise ValueError(f"Failed to create {model.__name__}: {str(e)}")

    @staticmethod
    async def update_by_id(
        session: AsyncSession, model: Type[T], object_id: int, **update_fields
    ) -> Optional[T]:
        try:
            if not update_fields:
                raise ValueError("No fields provided for update.")

            stmt = (
                update(model)
                .where(model.id == object_id)
                .values(**update_fields)
                .returning(model)
            )

            result: Result = await session.execute(stmt)
            updated_object: T | None = result.scalars().one_or_none()

            if updated_object is None:
                return None

            return updated_object

        except exc.SQLAlchemyError as e:
            raise ValueError(f"Failed to update {model.__name__}")

    @staticmethod
    async def delete_by_id(
        session: AsyncSession, model: Type[T], object_id: int
    ) -> None:
        try:
            stmt = delete(model).where(model.id == object_id)
            await session.execute(stmt)
        except exc.SQLAlchemyError as e:
            raise ValueError(f"Failed to delete {model.__name__}")
