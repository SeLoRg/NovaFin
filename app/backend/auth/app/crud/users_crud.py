from common.Models import Users
from sqlalchemy import select, delete, update, and_, or_, Result
from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy.exc
from auth.app.logger import logger
import json


async def get_users_by_filter(
    session: AsyncSession, limit: int = 100, skip: int = 0, **filters
) -> list[Users]:
    try:
        filters_conditions = [
            getattr(Users, key) == value for key, value in filters.items()
        ]
        stmt = select(Users).limit(limit).offset(skip)

        if filters_conditions:
            stmt = stmt.filter(*filters_conditions)

        res: Result = await session.execute(stmt)
        users: list[Users] = list(res.scalars().all())

        return users
    except sqlalchemy.exc.NoResultFound as e:
        return list()
    except sqlalchemy.exc.SQLAlchemyError as e:
        logger.error(f"Error while get users: {str(e)}")
        raise ValueError("Failed get users")


async def create_user(session: AsyncSession, **kwargs) -> Users:
    try:
        new_user: Users = Users(**kwargs)
        session.add(new_user)
        await session.flush()
        await session.refresh(new_user)
        return new_user
    except sqlalchemy.exc.SQLAlchemyError as e:
        logger.error(f"Error while create user: {str(e)}")
        raise ValueError("Failed create users")


async def update_user_by_id(
    session: AsyncSession, user_id: int, **update_fields
) -> Users | None:
    try:
        if not update_fields:
            raise ValueError("No fields provided for update.")

        stmt = (
            update(Users)
            .where(Users.id == user_id)
            .values(**update_fields)
            .returning(Users)
        )

        result: Result = await session.execute(stmt)
        updated_user: Users | None = result.scalars().one_or_none()

        if updated_user is None:
            return

        return updated_user

    except sqlalchemy.exc.SQLAlchemyError as e:
        print(f"Database error during users update: {str(e)}")
        raise ValueError("Failed update users")


async def delete_user_by_id(user_id: int, session: AsyncSession) -> None:
    try:
        stmt = delete(Users).where(Users.id == user_id)
        await session.execute(stmt)
    except sqlalchemy.exc.SQLAlchemyError as e:
        print(f"Error deleting users: {str(e)}")
        raise ValueError("Failed delete users")
