from data.db_session import SqlAlchemyBase
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, orm
from data import db_session
from data.users import User


class Idea(SqlAlchemyBase, SerializerMixin):  # класс идей
    __tablename__ = 'ideas'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String)
    image = Column(String, default=None)
    add_time = Column(DateTime, nullable=False)
    approved = Column(Boolean, default=False)
    likes = Column(Integer, default=0)

    def delete(self, idea_id):  # удаление идеи
        db_sess = db_session.create_session()
        idea = db_sess.query(Idea).get(idea_id)
        if idea:
            db_sess.delete(idea)
            db_sess.commit()
            return True
        return False
