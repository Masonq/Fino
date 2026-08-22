"""
Показ хода долгой работы в консоли.

Заход по трём чатам длится минуты и раньше не печатал ничего до самого
конца — со стороны это неотличимо от зависания, и первый же большой заход
приняли за него.

В терминале строка обновляется на месте, в журнале — печатается раз в
несколько секунд отдельными строками, иначе файл заполняется мусором из
управляющих символов.
"""
import sys
import time


class Progress:
    def __init__(self, title: str, every: float = 1.0):
        self.title = title
        self.every = every
        self.counters: dict[str, int] = {}
        self.started = time.monotonic()
        self._last = 0.0
        self._tty = sys.stdout.isatty()

    def bump(self, name: str, count: int = 1) -> None:
        self.counters[name] = self.counters.get(name, 0) + count

    def line(self) -> str:
        parts = [f"{name} {value}" for name, value in self.counters.items() if value]
        elapsed = int(time.monotonic() - self.started)
        return f"{self.title}: {', '.join(parts) or 'начинаем'} — {elapsed} с"

    def show(self, force: bool = False) -> None:
        now = time.monotonic()
        # В журнал пишем реже: он читается потом целиком, и строка раз в
        # секунду превратила бы его в простыню.
        interval = self.every if self._tty else max(self.every, 5.0)
        if not force and now - self._last < interval:
            return
        self._last = now
        if self._tty:
            sys.stdout.write("\r\033[K" + self.line())
            sys.stdout.flush()
        else:
            print(self.line(), flush=True)

    def done(self) -> None:
        self.show(force=True)
        if self._tty:
            sys.stdout.write("\n")
            sys.stdout.flush()
