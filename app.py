from flask import render_template, redirect, request, flash, url_for, session
from flask import Flask
from flask_ngrok import run_with_ngrok

import data
from data import db_session, users
from forms.registration import RegistrationForm
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from forms.login import LoginForm
from sqlalchemy.orm import Query
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
from flask_dropzone import Dropzone
import os

# Создаем экземпляр CSRFProtect
csrf = CSRFProtect()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['FLASK_DEBUG'] = 1
# дебаг нужен для отлавливания и исправления ошибок в реальном времени
login_manager = LoginManager()
login_manager.init_app(app)
csrf.init_app(app)  # csrf токен для предотвращения поддельных запросов

# создаем экземпляры расширений
dropzone = Dropzone(app)

# добавляем конфигурацию для загрузки файлов
app.config['UPLOAD_FOLDER'] = 'static/uploads/photos'
app.config['DROPZONE_ALLOWED_FILE_TYPE'] = 'image'
app.config['DROPZONE_MAX_FILES'] = 1
app.config['DROPZONE_UPLOAD_MULTIPLE'] = False


@app.route('/registration', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    User = data.users.User
    db_sess = db_session.create_session()
    if form.validate_on_submit():  # если форма регистрации на подтверждение, то...
        if form.password.data != form.confirm_password.data:
            flash(message='Пароли не совпадают',
                  category='danger')  # Выдача предупреждения на следующую страницу, в html файле есть обработчик
            # для flash предупреждений (далее также)
            return redirect('/registration')  # Перенаправление на страницу регистрации
        if db_sess.query(User).filter(User.username == form.username.data).first():
            flash(message='Пользователь с таким именем пользователя уже существует', category='warning ')
            return redirect('/registration')  # Перенаправление на страницу регистрации
        user = User()
        user.username = form.username.data
        user.password = form.password.data
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        flash(message='Регистрация прошла успешно', category='success')  # Выдача сообщения об успешной регистрации
        return redirect('/login')
    return render_template('registration.html', title='Регистрация', form=form)


@login_manager.user_loader  # для сессии
def load_user(user_id):
    User = data.users.User
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@app.route('/logout')  # выход
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/login', methods=['GET', 'POST'])
def login():
    User = data.users.User
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.username == form.username.data).first()
        if user and user.check_password(form.password.data):  # проверяет хеш пароля через функцию внутри класса юзер
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        flash(message='Неправильный логин или пароль', category='danger')
        return redirect('/login')
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/')  # главная страница
def main_page():
    return render_template('main_page.html')


@app.errorhandler(404)  # обработчик 404
def not_found_error(error):
    return render_template('404.html'), 404


def main():
    db_session.global_init('products.db')
    app.run(debug=True)


main()
