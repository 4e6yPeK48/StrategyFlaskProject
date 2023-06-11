from flask import render_template, redirect, request, flash, url_for, session, abort
from flask import Flask
from flask_ngrok import run_with_ngrok

import data
from data import db_session, users, ideas, comments
from forms.registration import RegistrationForm
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from forms.login import LoginForm
from sqlalchemy.orm import Query
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
from flask_dropzone import Dropzone
from flask_uploads import UploadSet, configure_uploads, IMAGES, DATA, ALL
import os
import datetime
from babel.dates import format_datetime
from babel import Locale

Idea = ideas.Idea
Comment = comments.Comment
User = users.User
# Создаем экземпляр CSRFProtect
csrf = CSRFProtect()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['FLASK_DEBUG'] = 1
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ideas.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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
app.config['UPLOADED_IMAGES_DEST'] = 'static/img'
images = UploadSet('images', IMAGES)
configure_uploads(app, images)


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


@app.route('/')
def landing():
    return render_template('empty.html')


# TODO: https://urbanideas.work/work сделать главную страницу, изображение static сзади всего как на сайте

# Обработчик для страницы index (main_page.html)
@app.route('/ideas')
def index():
    sort_by = request.args.get('sort_by', '')
    search = request.args.get('search', '')

    db_sess = db_session.create_session()

    if sort_by == 'name_asc':
        ideas = db_sess.query(Idea).filter(Idea.approved == 1).order_by(Idea.name.asc()).all()
    elif sort_by == 'name_desc':
        ideas = db_sess.query(Idea).filter(Idea.approved == 1).order_by(Idea.name.desc()).all()
    elif sort_by == 'date_old':
        ideas = db_sess.query(Idea).filter(Idea.approved == 1).order_by(Idea.add_time.asc()).all()
    elif sort_by == 'date_new':
        ideas = db_sess.query(Idea).filter(Idea.approved == 1).order_by(Idea.add_time.desc()).all()
    elif search:
        ideas = db_sess.query(Idea).filter(Idea.approved == 1, Idea.name.ilike(f'%{search}%')).all()
    else:
        ideas = db_sess.query(Idea).filter(Idea.approved == 1).all()

    return render_template('main_page.html', ideas=ideas, sort_by=sort_by)


@app.route('/add_comment/<int:idea_id>', methods=['POST'])
def add_comment(idea_id):
    db_sess = db_session.create_session()
    comment_text = request.form.get('comment_text')
    if not comment_text:
        return redirect(url_for('idea_detail', idea_id=idea_id))

    comment = Comment(
        text=comment_text,
        idea_id=idea_id,
        user_id=current_user.id,
        add_time=datetime.datetime.now()
    )
    db_sess.add(comment)
    db_sess.commit()

    return redirect(url_for('idea_detail', idea_id=idea_id))


@app.route('/idea/<int:idea_id>')
def idea_detail(idea_id):
    db_sess = db_session.create_session()
    idea = db_sess.query(Idea).get(idea_id)
    if idea is None:
        abort(404)

    locale = Locale.parse('ru')
    for comment in idea.comments:
        comment.add_time_formatted = format_datetime(comment.add_time, format='d MMMM Y, H:mm', locale=locale)

    return render_template('idea_detail.html', idea=idea, comments=comments, locale=locale)


@app.route('/delete_idea/<int:idea_id>', methods=['POST'])
def delete_idea(idea_id):
    # Проверка, является ли пользователь администратором
    if current_user.username != 'admin':
        abort(403)

    # Получение идеи из базы данных
    db_sess = db_session.create_session()
    idea = db_sess.query(Idea).get(idea_id)

    if not idea:
        flash('Идея не найдена', 'warning')  # Обработка случая, если идея не найдена

    # Удаление идеи из базы данных
    db_sess.delete(idea)
    db_sess.commit()
    flash('Идея успешно удалена', 'success')
    return redirect(url_for('index'))


# Функция для первой страницы добавления идеи
@app.route('/add_idea/step1', methods=['GET', 'POST'])
def add_idea_step1():
    if request.method == 'POST':
        return redirect(url_for('add_idea_step2'))
    return render_template('add_idea_step1.html')


# Функция для второй страницы добавления идеи
@app.route('/add_idea/step2', methods=['GET', 'POST'])
def add_idea_step2():
    if request.method == 'POST':
        # Сохранение введенной информации в сессии
        session['idea_name'] = request.form.get('idea_name')
        session['idea_description'] = request.form.get('idea_description')
        session['idea_time'] = datetime.datetime.now()
        return redirect(url_for('add_idea_step3'))
    return render_template('add_idea_step2.html')


# Функция для третьей страницы добавления идеи
@app.route('/add_idea/step3', methods=['GET', 'POST'])
def add_idea_step3():
    db_sess = db_session.create_session()
    if request.method == 'POST':
        # Сохранение введенной информации в сессии
        # Обработка отправки идеи на проверку
        # Используйте сохраненную информацию из сессии
        idea_name = session.get('idea_name')
        idea_description = session.get('idea_description')
        idea_time = session.get('idea_time')

        # Сохранение изображения
        image = request.files['image']
        if image:
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        # Создание экземпляра идеи и сохранение в базу данных
        idea = Idea(user_id=current_user.id,
                    name=idea_name,
                    description=idea_description,
                    image=filename,
                    add_time=idea_time)

        db_sess.add(idea)
        db_sess.commit()

        session.clear()  # Очистка сессии после отправки идеи
        flash('Идея отправлена на проверку', 'success')
        return redirect(url_for('index'))

    return render_template('add_idea_step3.html')


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
@app.route('/like_dislike/<int:idea_id>/<action>', methods=['POST'])
def like_dislike(idea_id, action):
    db_sess = db_session.create_session()
    idea = db_sess.query(Idea).get(idea_id)
    if idea:
        if action == 'like':
            idea.likes += 1
        elif action == 'dislike':
            idea.likes -= 1
        db_sess.commit()
    return '<script>document.location.href = document.referrer</script>'


@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404


@app.errorhandler(403)
def not_found_error(error):
    return render_template('403.html'), 403


def main():
    db_session.global_init('ideas.db')
    app.run(debug=True)


main()

# TODO: задачи - проанализировать, создать эскизы, создать прототип, создать продукт
