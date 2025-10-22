from .database import db, User, Team, Question, QuestionPurchase, Transfer, Transaction
from datetime import datetime


class WalletCore:
    @staticmethod
    def get_team_dashboard(team_id):
        """Получает данные для дашборда команды"""
        team = Team.query.get(team_id)
        if not team:
            return None

        # Получаем купленные вопросы
        purchased_questions = QuestionPurchase.query.filter_by(team_id=team_id).all()

        # Получаем переводы
        transfers = Transfer.query.filter_by(team_id=team_id).order_by(Transfer.transferred_at.desc()).limit(10).all()

        # Получаем доступные вопросы
        available_questions = Question.query.filter_by(is_approved=True).all()

        return {
            'team': team,
            'members': team.members,
            'purchased_questions': purchased_questions,
            'transfers': transfers,
            'available_questions': available_questions,
            'total_team_points': sum(member.points for member in team.members)
        }

    @staticmethod
    def purchase_question(question_id, user_id, personal_password):
        """
        Покупка вопроса пользователем
        """
        from .auth import password_hasher

        # Проверяем пользователя и пароль
        user = User.query.get(user_id)
        if not user or not password_hasher.verify_password(personal_password, user.personal_password):
            return False, "Неверный личный пароль"

        question = Question.query.get(question_id)
        if not question or not question.is_approved:
            return False, "Вопрос не найден или не одобрен"

        if user.points < question.price:
            return False, "Недостаточно средств"

        # Проверяем, не куплен ли вопрос уже командой
        existing_purchase = QuestionPurchase.query.filter_by(
            question_id=question_id,
            team_id=user.team_id
        ).first()

        if existing_purchase:
            return False, "Вопрос уже куплен вашей командой"

        try:
            # Списание средств
            user.points -= question.price
            user.team.total_points -= question.price

            # Создаем запись о покупке
            purchase = QuestionPurchase(
                question_id=question_id,
                team_id=user.team_id,
                purchased_by=user_id
            )
            db.session.add(purchase)

            # Записываем транзакцию
            transaction = Transaction(
                amount=question.price,
                transaction_type='purchase',
                description=f'Покупка вопроса: {question.content[:50]}...',
                team_id=user.team_id,
                user_id=user_id
            )
            db.session.add(transaction)

            db.session.commit()
            return True, "Вопрос успешно куплен"

        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка при покупке: {str(e)}"

    @staticmethod
    def transfer_points(from_user_id, to_user_id, amount, personal_password):
        """
        Перевод баллов между пользователями
        """
        from .auth import password_hasher

        # Проверяем отправителя и пароль
        from_user = User.query.get(from_user_id)
        if not from_user or not password_hasher.verify_password(personal_password, from_user.personal_password):
            return False, "Неверный личный пароль"

        to_user = User.query.get(to_user_id)
        if not to_user:
            return False, "Получатель не найден"

        if from_user.team_id != to_user.team_id:
            return False, "Можно переводить только сокомандникам"

        if from_user.points < amount:
            return False, "Недостаточно средств"

        if amount <= 0:
            return False, "Сумма должна быть положительной"

        try:
            # Выполняем перевод
            from_user.points -= amount
            to_user.points += amount

            # Создаем запись о переводе
            transfer = Transfer(
                from_user_id=from_user_id,
                to_user_id=to_user_id,
                amount=amount,
                team_id=from_user.team_id
            )
            db.session.add(transfer)

            # Записываем транзакцию
            transaction = Transaction(
                amount=amount,
                transaction_type='transfer',
                description=f'Перевод {from_user.username} -> {to_user.username}',
                team_id=from_user.team_id,
                user_id=from_user_id
            )
            db.session.add(transaction)

            db.session.commit()
            return True, "Перевод выполнен успешно"

        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка при переводе: {str(e)}"

    @staticmethod
    def propose_question(content, price, user_id):
        """
        Предложение нового вопроса
        """
        try:
            question = Question(
                content=content,
                price=price,
                created_by=user_id,
                is_approved=False  # Требует модерации
            )
            db.session.add(question)
            db.session.commit()
            return True, "Вопрос предложен на модерацию"
        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка при предложении вопроса: {str(e)}"


# Создаем глобальный экземпляр
wallet_core = WalletCore()