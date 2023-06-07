from flask import render_template, redirect, request, flash, url_for, session
from flask import Flask
from flask_ngrok import run_with_ngrok

import data
from data import db_session, users, ideas
from forms.registration import RegistrationForm
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from forms.login import LoginForm
from sqlalchemy.orm import Query
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
from flask_dropzone import Dropzone
import os

Idea = ideas.Idea
# Создаем экземпляр CSRFProtect
csrf = CSRFProtect()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['FLASK_DEBUG'] = 1
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ideas.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOADED_IMAGES_DEST'] = 'uploads'
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
            flash(message='Такой пользователь уже существует', category='warning ')
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


# Обработчик для страницы index (main_page.html)
@app.route('/')
def index():
    db_sess = db_session.create_session()
    ideas = db_sess.query(Idea).filter_by(approved=True).order_by(Idea.add_time.desc()).all()
    return render_template('main_page.html', ideas=ideas)


# Обработчик для страницы approved_ideas
@app.route('/approved_ideas')
def approved_ideas():
    db_sess = db_session.create_session()
    ideas = db_sess.query(Idea).filter_by(approved=True).all()
    return render_template('approved_ideas.html', ideas=ideas)


# Обработчик для страницы add_idea
@app.route('/add_idea', methods=['GET', 'POST'])
def add_idea():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        image = request.files['image']

        # Обработка и сохранение идеи в базу данных
        db_sess = db_session.create_session()
        idea = Idea(user_id=current_user.id, name=name, description=description, image=image.filename)
        db_sess.add(idea)
        db_sess.commit()

        # Сохранение изображения в папку проекта (используйте свою логику сохранения изображения)

        return redirect(url_for('index'))
    return render_template('add_idea.html')


# Обработчик для страницы admin_panel
@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    if current_user.username != 'admin':
        abort(403)  # Если пользователь не админ, возвращаем ошибку 403 Forbidden
    db_sess = db_session.create_session()
    ideas = db_sess.query(Idea).all()
    return render_template('admin_panel.html', ideas=ideas)


# Обработчик для принятия/отклонения идеи админом
@app.route('/admin/approve_idea/<int:idea_id>', methods=['POST'])
def approve_idea(idea_id):
    if current_user.username != 'admin':
        abort(403)
    # Получение идеи по идентификатору `idea_id`
    db_sess = db_session.create_session()
    idea = db_sess.query(Idea).get(idea_id)
    if idea:
        # Принять или отклонить идею
        idea.approved = True  # Или False, в зависимости от действия
        db_sess.commit()
        flash('Идея успешно принята.', 'success')
    else:
        flash('Идея не найдена.', 'error')

    return redirect(url_for('admin_panel'))


@app.route('/admin/reject_idea/<int:idea_id>', methods=['POST'])
def reject_idea(idea_id):
    db_sess = db_session.create_session()
    idea = db_sess.query(Idea).get(idea_id)

    if not idea:
        return "Идея не найдена"

    # Отклонение идеи
    idea.approved = False
    db_sess.commit()

    return redirect(url_for('admin_panel'))


# Обработчик для кнопки лайк/дизлайк
@app.route('/like_dislike/<int:idea_id>/<action>')
def like_dislike(idea_id, action):
    db_sess = db_session.create_session()
    idea = db_sess.query(Idea).get(idea_id)
    if idea:
        if action == 'like':
            idea.likes += 1
        elif action == 'dislike':
            idea.likes -= 1
        db_sess.commit()
    return redirect(url_for('index'))


@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404


def main():
    db_session.global_init('ideas.db')
    app.run(debug=True)


main()
