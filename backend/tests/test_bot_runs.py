"""
Бот запускается.

Остальное из бывшего test_screen.py — про публикацию объявлений
перепиской с ботом: пошаговые экраны, кнопки под сообщением, живое
сообщение, которое переписывается. Эта механика снесена, публикация
идёт через WebApp-публикатор, и те тесты проверяли код, которого нет.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

def test_bot_can_actually_start():
    """
    Перестановка обработчиков однажды вырезала запуск целиком: бот
    стартовал и через шесть секунд завершался без ошибки, потому что
    слушать было нечем.
    """
    from app.bot import publisher

    assert hasattr(publisher, "main")
    source = (Path(__file__).resolve().parents[1]
              / "app" / "bot" / "publisher.py").read_text()
    assert "await dp.start_polling(bot)" in source
    assert 'if __name__ == "__main__":' in source

