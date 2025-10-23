from .database import db, Member, Team, Question, QuestionPurchase, Transfer
from datetime import datetime
from config import Config


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

        # Получаем ВСЕ вопросы (одобренные и предложенные)
        all_questions = Question.query.all()
        available_questions = [q for q in all_questions if q.is_approved]
        proposed_questions = [q for q in all_questions if not q.is_approved]

        print(f"📚 Всего вопросов: {len(all_questions)}")
        print(f"✅ Одобренных: {len(available_questions)}")
        print(f"💡 Предложенных: {len(proposed_questions)}")

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

        # ИСПРАВЛЕННЫЙ ЗАПРОС переводов - ДОБАВЛЯЕМ ПРЕПОДАВАТЕЛЯ В ДАННЫЕ
        transfers_data = []
        transfers = Transfer.query.filter_by(team_id=team_id).order_by(Transfer.transferred_at.desc()).limit(10).all()

        for transfer in transfers:
            # Для переводов от преподавателя показываем "Преподаватель" вместо реального отправителя
            if transfer.transfer_type == 'teacher_reward':
                from_member_name = "Преподаватель"
            else:
                from_member = Member.query.get(transfer.from_member_id)
                from_member_name = from_member.name if from_member else "Неизвестный"

            to_member = Member.query.get(transfer.to_member_id)
            if to_member:
                transfers_data.append({
                    'transfer': transfer,
                    'from_member_name': from_member_name,  # ИСПОЛЬЗУЕМ ИМЯ, А НЕ ОБЪЕКТ
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
            'all_questions': all_questions,
            'total_team_points': sum(member.points for member in members)
        }

    @staticmethod
    def purchase_question(question_id, member_id):
        """
        Покупка вопроса участником (без пароля)
        Теперь вычитает баллы и у пользователя, и у команды
        """
        member = Member.query.get(member_id)
        if not member:
            return False, "Участник не найден"

        question = Question.query.get(question_id)
        if not question or not question.is_approved:
            return False, "Вопрос не найден или не одобрен"

        # Проверяем, не предложен ли вопрос нашей командой
        if question.proposed_by_team == member.team_id:
            return False, "Этот вопрос недоступен вашей команде"

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
            # Списание средств у участника
            member.points -= question.price

            # ДОБАВЛЕНО: Списание средств у команды
            team = Team.query.get(member.team_id)
            if team:
                team.total_points -= question.price

            # Создаем запись о покупке
            purchase = QuestionPurchase(
                question_id=question_id,
                team_id=member.team_id,
                purchased_by=member_id
            )
            db.session.add(purchase)
            db.session.commit()
            return True, f"Вопрос '{question.content[:50]}...' успешно куплен за {question.price} баллов"
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
                team_id=from_member.team_id,
                transfer_type='regular'
            )
            db.session.add(transfer)
            db.session.commit()
            return True, f"Успешно переведено {amount} баллов участнику {to_member.name}"
        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка при переводе: {str(e)}"

    @staticmethod
    def reward_points(from_member_id, to_member_id, amount, teacher_password):
        """
        Начисление баллов от преподавателя за выполненное задание
        """
        from_member = Member.query.get(from_member_id)
        if not from_member:
            return False, "Отправитель не найден"

        to_member = Member.query.get(to_member_id)
        if not to_member:
            return False, "Получатель не найден"

        # Проверяем пароль преподавателя
        from config import Config
        if teacher_password != Config.TEACHER_PASSWORD:
            return False, "Неверный пароль преподавателя"

        if amount <= 0:
            return False, "Сумма должна быть положительной"

        try:
            # Находим аккаунт преподавателя для записи в историю
            teacher_account = Member.query.filter_by(is_teacher=True).first()
            if not teacher_account:
                return False, "Аккаунт преподавателя не найден"

            # Начисляем баллы получателю
            to_member.points += amount

            # Начисляем баллы команде получателя
            team = Team.query.get(to_member.team_id)
            if team:
                team.total_points += amount

            # Создаем запись о начислении ОТ ПРЕПОДАВАТЕЛЯ
            transfer = Transfer(
                from_member_id=teacher_account.id,  # Используем ID преподавателя, а не текущего пользователя
                to_member_id=to_member_id,
                amount=amount,
                team_id=to_member.team_id,
                transfer_type='teacher_reward'
            )
            db.session.add(transfer)
            db.session.commit()
            return True, f"Успешно начислено {amount} баллов участнику {to_member.name} за выполненное задание"
        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка при начислении: {str(e)}"

    @staticmethod
    def propose_question(content, price, member_id):
        """
        Предложение нового вопроса
        """
        try:
            member = Member.query.get(member_id)
            if not member:
                return False, "Участник не найден"

            question = Question(
                content=content,
                price=price,
                is_approved=False,  # Требует модерации
                proposed_by=member_id,
                proposed_by_team=member.team_id
            )
            db.session.add(question)
            db.session.commit()
            return True, "Вопрос предложен на модерацию"
        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка при предложении вопроса: {str(e)}"


# Создаем глобальный экземпляр
wallet_core = WalletCore()