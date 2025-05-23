from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):
    user_id: Optional[int] = Field(primary_key=True)
    username: Optional[str]
    phone_number: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    given_name: Optional[str]
    city: Optional[str]
    create_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Kua(SQLModel, table=True):
    user_id: Optional[int] = Field(primary_key=True)
    gender: Optional[str]
    birth_date: Optional[str]
    kua_number: Optional[str]
    count_visit: Optional[int] = 0


class Zodiac(SQLModel, table=True):
    user_id: Optional[int] = Field(primary_key=True)
    birth_date: Optional[str]
    chinese_sign: Optional[str]
    chinese_element: Optional[str]
    count_visit: Optional[int] = 0


class Mashhad(SQLModel, table=True):
    user_id: Optional[int] = Field(primary_key=True)
    name: Optional[str]
    city: Optional[str]
    create_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Fengshui_Test(SQLModel, table=True):
    user_id: Optional[int] = Field(primary_key=True)
    f_name: Optional[str]
    l_name: Optional[str]
    phone: Optional[str]
    city: Optional[str]
    metrage: Optional[str]
    problem: Optional[str]
    create_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
