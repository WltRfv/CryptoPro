from .database import db, Member, Team, Question, QuestionPurchase, Transfer
from datetime import datetime


class WalletCore:
    @staticmethod
    def get_team_dashboard(team_id):
        """Получает данные для дашборда команды"""
        team = Team.query.get(team_id)
        if not team:
            return None

        # Получаем купленные вопросы с информацией о покупателе
        purchased_questions = db.session.query(QuestionPurchase, Question, Member).\
            join(Question, QuestionPurchase.question_id == Question.id).\
            join(Member, QuestionPurchase.purchased_by == Member.id).\
            filter(QuestionPurchase.team_id == team_id).all()

        # Получаем переводы с информацией об отправителе и получателе
        transfers = db.session.query(Transfer, Member.label('from_member'), Member.label('to_member')).\
            join(Member, Transfer.from_member_id == Member.id).\
            join(Member, Transfer.to_member_id == Member.id).\
            filter(Transfer.team_id == team_id).\
            order_by(Transfer.transferred_at.desc()).limit(10).all()

        # Получаем доступные вопросы
        available_questions = Question.query.filter_by(is_approved=True).all()

        # Получаем участников команды
        members = Member.query.filter_by(team_id=team_id).all()

        return {
            'team': team,
            'members': members,
            'purchased_questions': purchased_questions,
            'transfers': transfers,
            'available_questions': available_questions,
            'total_team_points': sum(member.points for member in members)
        }

    @staticmethod
    def purchase_question(question_id, member_id):
        """
        Покупка вопроса участником (без пароля)
        """
        member = Member.query.get(member_id)
        if not member:
            return False, "Участник не найден"

        question = Question.query.get(question_id)
        if not question or not question.is_approved:
            return False, "Вопрос не найден или не одобрен"

        if member.points < question.price:
            return False, "Недостаточно средств"

        # Проверяем, не куплен ли вопрос уже командой
        existing_purchase = QuestionPurchase.query.filter_by(
            question_id=question_id,
            team_id=member.team_id
        ).first()

        if existing_purchase:
            return False, "Вопрос уже куплен вашей командой"

        try:
            # Списание средств
            member.points -= question.price

            # Создаем запись о покупке
            purchase = QuestionPurchase(
                question_id=question_id,
                team_id=member.team_id,
                purchased_by=member_id
            )
            db.session.add(purchase)

            db.session.commit()
            return True, f"Вопрос '{question.content}' успешно куплен за {question.price} баллов"

        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка при покупке: {str(e)}"

    @staticmethod
    def transfer_points(from_member_id, to_member_id, amount):
        """
        Перевод баллов между участниками (без пароля)
        """
        from_member = Member.query.get(from_member_id)
        if not from_member:
            return False, "Отправитель не найден"

        to_member = Member.query.get(to_member_id)
        if not to_member:
            return False, "Получатель не найден"

        if from_member.team_id != to_member.team_id:
            return False, "Можно переводить только сокомандникам"

        if from_member.points < amount:
            return False, "Недостаточно средств"

        if amount <= 0:
            return False, "Сумма должна быть положительной"

        try:
            # Выполняем перевод
            from_member.points -= amount
            to_member.points += amount

            # Создаем запись о переводе
            transfer = Transfer(
                from_member_id=from_member_id,
                to_member_id=to_member_id,
                amount=amount,
                team_id=from_member.team_id
            )
            db.session.add(transfer)

            db.session.commit()
            return True, f"Успешно переведено {amount} баллов участнику {to_member.name}"

        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка при переводе: {str(e)}"

    @staticmethod
    def propose_question(content, price, member_id):
        """
        Предложение нового вопроса
        """
        try:
            question = Question(
                content=content,
                price=price,
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