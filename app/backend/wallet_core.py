from .database import db, Member, Team, Question, QuestionPurchase, Transfer
from datetime import datetime


class WalletCore:
    @staticmethod
    def get_team_dashboard(team_id):
        """Получает данные для дашборда команды"""
        print(f"📊 Получение дашборда для команды {team_id}")

        team = Team.query.get(team_id)
        if not team:
            print("❌ Команда не найдена")
            return None

        # Получаем участников команды
        members = Member.query.filter_by(team_id=team_id).all()
        print(f"👥 Найдено участников: {len(members)}")

        # Получаем доступные вопросы
        available_questions = Question.query.filter_by(is_approved=True).all()
        print(f"📚 Доступно вопросов: {len(available_questions)}")

        # Получаем предложенные вопросы (все, даже не одобренные)
        proposed_questions = Question.query.filter_by(is_approved=False).all()
        print(f"💡 Предложено вопросов: {len(proposed_questions)}")

        # ИСПРАВЛЕННЫЙ ЗАПРОС купленных вопросов
        purchased_questions_data = []
        purchased_questions = QuestionPurchase.query.filter_by(team_id=team_id).all()
        for purchase in purchased_questions:
            question = Question.query.get(purchase.question_id)
            purchaser = Member.query.get(purchase.purchased_by)
            if question and purchaser:
                purchased_questions_data.append({
                    'question': question,
                    'purchaser': purchaser,
                    'purchase': purchase
                })
        print(f"🛒 Купленных вопросов: {len(purchased_questions_data)}")

        # ИСПРАВЛЕННЫЙ ЗАПРОС переводов
        transfers_data = []
        transfers = Transfer.query.filter_by(team_id=team_id).order_by(Transfer.transferred_at.desc()).limit(10).all()
        for transfer in transfers:
            from_member = Member.query.get(transfer.from_member_id)
            to_member = Member.query.get(transfer.to_member_id)
            if from_member and to_member:
                transfers_data.append({
                    'transfer': transfer,
                    'from_member': from_member,
                    'to_member': to_member
                })
        print(f"📊 Переводов в истории: {len(transfers_data)}")

        return {
            'team': team,
            'members': members,
            'purchased_questions': purchased_questions_data,
            'proposed_questions': proposed_questions,
            'transfers': transfers_data,
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
                is_approved=False,  # Требует модерации
                created_by=member_id
            )
            db.session.add(question)
            db.session.commit()
            return True, "Вопрос предложен на модерацию"
        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка при предложении вопроса: {str(e)}"


# Создаем глобальный экземпляр
wallet_core = WalletCore()