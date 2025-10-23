from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_user, logout_user, current_user, login_required
from app.backend.auth import auth_manager
from app.backend.wallet_core import wallet_core
from app.backend.database import Member, Team

bp = Blueprint('frontend', __name__)


@bp.route('/')
def index():
    return redirect(url_for('frontend.team_login'))


@bp.route('/team-login', methods=['GET', 'POST'])
def team_login():
    """Единственная страница входа - только через ключи"""
    session_token = None

    if request.method == 'POST':
        # Всегда отправляем ключи при нажатии кнопки
        session_token, message = auth_manager.initiate_team_login()
        flash(message, 'success')

    return render_template('team_login.html', session_token=session_token)


@bp.route('/verify-keys', methods=['POST'])
def verify_keys():
    """Проверка комбинации ключей"""
    session_token = request.form.get('session_token')
    keys_input = request.form.get('keys_input')

    if not session_token or not keys_input:
        return jsonify({'success': False, 'message': 'Заполните все поля'})

    # Разделяем ключи по запятым или пробелам
    shares = [key.strip() for key in keys_input.replace(',', ' ').split() if key.strip()]

    if len(shares) < 3:
        return jsonify({'success': False, 'message': 'Нужно минимум 3 ключа'})

    # Проверяем комбинацию
    success, message = auth_manager.verify_combined_key(shares, session_token)

    if success:
        # Получаем команду (у нас только одна)
        team = Team.query.first()
        return jsonify({
            'success': True,
            'message': message,
            'redirect_url': url_for('frontend.dashboard', team_id=team.id)
        })
    else:
        return jsonify({'success': False, 'message': message})


@bp.route('/personal-login', methods=['GET', 'POST'])
def personal_login():
    """Личный вход участника"""
    if request.method == 'POST':
        member_name = request.form.get('member_name')
        personal_password = request.form.get('personal_password')

        member, is_valid = auth_manager.verify_personal_login(member_name, personal_password)

        if is_valid and member:
            login_user(member)
            flash(f'Добро пожаловать, {member.name}!', 'success')
            return redirect(url_for('frontend.dashboard', team_id=member.team_id))
        else:
            flash('Неверное имя участника или пароль', 'error')

    return render_template('personal_login.html')


@bp.route('/dashboard/<int:team_id>')
@login_required
def dashboard(team_id):
    """Дашборд команды"""
    dashboard_data = wallet_core.get_team_dashboard(team_id)

    if not dashboard_data:
        flash('Команда не найдена', 'error')
        return redirect(url_for('frontend.team_login'))

    return render_template('dashboard.html', **dashboard_data)


@bp.route('/purchase-question', methods=['POST'])
@login_required
def purchase_question():
    """Покупка вопроса (без пароля)"""
    question_id = request.form.get('question_id')

    success, message = wallet_core.purchase_question(
        question_id,
        current_user.id
    )

    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')

    return redirect(url_for('frontend.dashboard', team_id=current_user.team_id))


@bp.route('/transfer-points', methods=['POST'])
@login_required
def transfer_points():
    """Перевод баллов (без пароля)"""
    to_member_id = request.form.get('to_member_id')
    amount = request.form.get('amount')

    try:
        amount = int(amount)
    except ValueError:
        flash('Некорректная сумма', 'error')
        return redirect(url_for('frontend.dashboard', team_id=current_user.team_id))

    success, message = wallet_core.transfer_points(
        current_user.id,
        to_member_id,
        amount
    )

    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')

    return redirect(url_for('frontend.dashboard', team_id=current_user.team_id))


@bp.route('/propose-question', methods=['POST'])
@login_required
def propose_question():
    """Предложение нового вопроса"""
    content = request.form.get('content')
    price = request.form.get('price')

    try:
        price = int(price)
    except ValueError:
        flash('Некорректная цена', 'error')
        return redirect(url_for('frontend.dashboard', team_id=current_user.team_id))

    success, message = wallet_core.propose_question(content, price, current_user.id)

    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')

    return redirect(url_for('frontend.dashboard', team_id=current_user.team_id))


@bp.route('/logout')
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('frontend.team_login'))