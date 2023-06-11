from data.db_session import SqlAlchemyBase
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, orm
from data import db_session
from data.users import User


class Comment(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'comments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(String(500), nullable=False)
    idea_id = Column(Integer, ForeignKey('ideas.id'), nullable=False)
    idea = orm.relationship('Idea', backref='comments')
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = orm.relationship('User')
    add_time = Column(DateTime)

    def delete(self, comment_id):  # удаление комментария
        db_sess = db_session.create_session()
        comment = db_sess.query(Comment).get(comment_id)
        if comment:
            db_sess.delete(comment)
            db_sess.commit()
            return True
        return False
