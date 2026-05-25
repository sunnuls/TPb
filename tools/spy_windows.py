"""
Диагностика окон PokerStars.
Запускать пока открыт диалог buy-in (или любое другое окно PS).
"""
import win32gui
import win32process
import win32api
import psutil


def get_process_name(hwnd):
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc = psutil.Process(pid)
        return proc.name()
    except Exception:
        return "?"


def enum_callback(hwnd, results):
    if not win32gui.IsWindowVisible(hwnd):
        return
    title = win32gui.GetWindowText(hwnd)
    cls = win32gui.GetClassName(hwnd)
    rect = win32gui.GetWindowRect(hwnd)
    w = rect[2] - rect[0]
    h = rect[3] - rect[1]
    proc = get_process_name(hwnd)
    results.append({
        "hwnd": hwnd,
        "title": title,
        "class": cls,
        "rect": rect,
        "size": f"{w}x{h}",
        "process": proc,
    })


def main():
    print("=" * 80)
    print("SPY WINDOWS — все видимые окна на экране")
    print("=" * 80)

    results = []
    win32gui.EnumWindows(enum_callback, results)

    # Сначала показать только окна PokerStars
    ps_windows = [r for r in results if "pokerstars" in r["process"].lower()
                  or "pokerstars" in r["title"].lower()]

    print(f"\n[ ОКНА POKERSTARS — найдено: {len(ps_windows)} ]\n")
    for r in ps_windows:
        print(f"  HWND:    {r['hwnd']}")
        print(f"  Заголовок: {repr(r['title'])}")
        print(f"  Класс:   {r['class']}")
        print(f"  Размер:  {r['size']}  Позиция: {r['rect']}")
        print(f"  Процесс: {r['process']}")
        print("-" * 60)

    # Потом все остальные окна (маленькие — потенциальные диалоги)
    small_windows = [r for r in results
                     if r not in ps_windows
                     and (rect_w(r) < 800 or rect_h(r) < 600)
                     and r["title"]]

    if small_windows:
        print(f"\n[ МАЛЕНЬКИЕ ОКНА (потенциальные диалоги) — найдено: {len(small_windows)} ]\n")
        for r in small_windows:
            print(f"  HWND:    {r['hwnd']}")
            print(f"  Заголовок: {repr(r['title'])}")
            print(f"  Класс:   {r['class']}")
            print(f"  Размер:  {r['size']}  Позиция: {r['rect']}")
            print(f"  Процесс: {r['process']}")
            print("-" * 60)

    print("\n[ ВСЕ ОКНА ]\n")
    for r in results:
        if r["title"]:
            print(f"  {r['hwnd']:>8}  {r['size']:>10}  {r['class']:<40}  {repr(r['title'])[:50]}  [{r['process']}]")

    print("\n" + "=" * 80)
    print("Скопируй и пришли весь этот вывод.")
    print("=" * 80)


def rect_w(r):
    return r["rect"][2] - r["rect"][0]


def rect_h(r):
    return r["rect"][3] - r["rect"][1]


if __name__ == "__main__":
    main()
