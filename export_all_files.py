import os


def get_project_tree(start_path='.'):
    """Генерирует дерево каталогов проекта"""
    tree = ["СТРУКТУРА ПРОЕКТА:\n" + "=" * 50 + "\n"]

    for root, dirs, files in os.walk(start_path):
        # Игнорируем системные папки
        dirs[:] = [d for d in dirs if
                   d not in {'.git', '__pycache__', 'venv', '.idea', 'node_modules'} and not d.startswith('.')]

        level = root.replace(start_path, '').count(os.sep)
        indent = ' ' * 2 * level
        tree.append(f"{indent}📁 {os.path.basename(root)}/")

        subindent = ' ' * 2 * (level + 1)
        for file in files:
            if file not in {'PROJECT_FULL_EXPORT.txt'}:
                tree.append(f"{subindent}📄 {file}")

    return "\n".join(tree)


def export_project_with_tree(output_file='PROJECT_FULL_EXPORT.txt'):
    """Экспортирует проект с деревом структуры"""

    text_extensions = {'.py', '.txt', '.md', '.html', '.css', '.js', '.json', '.xml', '.sql', '.bd', '.config', '.ini'}
    ignore_dirs = {'.git', '__pycache__', 'venv', '.idea', 'node_modules'}

    with open(output_file, 'w', encoding='utf-8') as outfile:
        # Записываем дерево проекта
        outfile.write(get_project_tree())
        outfile.write("\n\n" + "=" * 80 + "\n")
        outfile.write("СОДЕРЖИМОЕ ФАЙЛОВ:\n")
        outfile.write("=" * 80 + "\n\n")

        # Записываем содержимое файлов
        for root, dirs, files in os.walk('.'):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]

            for file in files:
                if file == output_file:
                    continue

                _, ext = os.path.splitext(file)
                if ext.lower() in text_extensions:
                    file_path = os.path.join(root, file)

                    try:
                        for encoding in ['utf-8', 'cp1251']:
                            try:
                                with open(file_path, 'r', encoding=encoding) as infile:
                                    content = infile.read()

                                outfile.write(f"\n{'=' * 80}\n")
                                outfile.write(f"📁 ФАЙЛ: {file_path}\n")
                                outfile.write(f"{'=' * 80}\n\n")
                                outfile.write(content)
                                outfile.write("\n")
                                break
                            except UnicodeDecodeError:
                                continue
                    except Exception as e:
                        outfile.write(f"❌ Ошибка чтения {file_path}\n\n")


if __name__ == "__main__":
    export_project_with_tree()
    print("✅ Проект с деревом структуры экспортирован в PROJECT_FULL_EXPORT.txt")