# admin_tools/register_key.py
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app import create_app
from app.backend.database import db, Member, PublicKey


def register_public_key():
    app = create_app()

    with app.app_context():
        print("👥 Участники в системе:")
        members = Member.query.all()
        for m in members:
            print(f" - {m.name}")

        member_name = input("\nВведите имя участника: ").strip()
        member = Member.query.filter_by(name=member_name).first()

        if not member:
            print("❌ Участник не найден!")
            return

        print(f"\nВведите публичный ключ участника {member_name}:")
        print("(скопируйте содержимое файла *_public.pem)")
        public_key = ""
        try:
            while True:
                line = input()
                public_key += line + "\n"
        except EOFError:
            pass

        # Сохраняем в базу
        old_key = PublicKey.query.filter_by(member_id=member.id).first()
        if old_key:
            db.session.delete(old_key)

        new_key = PublicKey(
            member_id=member.id,
            public_key=public_key.strip()
        )
        db.session.add(new_key)
        db.session.commit()

        print(f"✅ Публичный ключ для {member.name} зарегистрирован!")


if __name__ == "__main__":
    register_public_key()