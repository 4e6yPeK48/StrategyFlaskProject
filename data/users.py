# primary_key, foreign_key, autoincrement

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, orm
import datetime  # можно удалить
from sqlalchemy_serializer import SerializerMixin
from data.db_session import SqlAlchemyBase
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin


class User(SqlAlchemyBase, SerializerMixin, UserMixin):  # класс пользователя, юзер миксин для сессии
    __tablename__ = 'users'
    id = Column(Integer, autoincrement=True, primary_key=True)
    username = Column(String, nullable=False)
    hashed_password = Column(String)

    def set_password(self, password):  # хеш пароля
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):  # проверка хеша пароля
        return check_password_hash(self.hashed_password, password)
