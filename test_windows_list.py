"""
Test script to list all windows and auto-find by title/keywords.

Extended for auto_find_window.md Phase 1:
  - list_all_windows(): raw Win32 enumeration
  - auto_find_by_keywords(): uses AutoWindowFinder for smart matching
  - find_poker_windows(): searches for known poker-room patterns
  - find_by_title(): exact/substring/regex title search
  - find_by_process(): search by process name
"""

import win32gui
import win32process

# Graceful import of AutoWindowFinder
try:
    from launcher.auto_window_finder import (
        AutoWindowFinder,
        WindowMatch,
        KNOWN_POKER_TITLES,
        KNOWN_POKER_PROCESSES,
    )
    FINDER_AVAILABLE = True
except Exception:
    FINDER_AVAILABLE = False


def list_all_windows():
    """List ALL windows with minimal filtering."""
    windows = []

    def callback(hwnd, results):
        try:
            # Get title
            title = win32gui.GetWindowText(hwnd)

            # Get visibility
            visible = win32gui.IsWindowVisible(hwnd)

            # Get rect
            rect = win32gui.GetWindowRect(hwnd)
            x, y, right, bottom = rect
            width = right - x
            height = bottom - y

            # Get process
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)

                # Try to get process name
                try:
                    import psutil
                    process = psutil.Process(pid)
                    process_name = process.name()
                except Exception:
                    process_name = f"pid_{pid}"
            except Exception:
                process_name = "unknown"

            results.append({
                'hwnd': hwnd,
                'title': title or "(no title)",
                'visible': visible,
                'size': f"{width}x{height}",
                'process': process_name
            })
        except Exception:
            pass

    win32gui.EnumWindows(callback, windows)
    return windows


# ---------------------------------------------------------------------------
# Auto-find functions (auto_find_window.md Phase 1)
# ---------------------------------------------------------------------------

def auto_find_by_keywords(keywords, visible_only=True, min_size=(200, 150)):
    """Auto-find windows matching any of the given keywords.

    Uses :class:`AutoWindowFinder` for multi-strategy search
    (exact, substring, regex) with ranked scoring.

    Args:
        keywords:     List of title keywords to search for.
        visible_only: Only return visible windows.
        min_size:     Minimum (width, height) to consider.

    Returns:
        List of WindowMatch objects sorted by score.
    """
    if not FINDER_AVAILABLE:
        print("[WARN] AutoWindowFinder not available")
        return []

    finder = AutoWindowFinder()
    if not finder.available:
        print("[WARN] Win32 API not available")
        return []

    all_matches = {}
    for kw in keywords:
        for match in finder.find_all(kw, visible_only=visible_only, min_size=min_size):
            if match.hwnd not in all_matches or match.score > all_matches[match.hwnd].score:
                all_matches[match.hwnd] = match

    return sorted(all_matches.values(), key=lambda m: m.score, reverse=True)


def find_poker_windows():
    """Search for all known poker-room windows on the desktop.

    Returns:
        List of WindowMatch for detected poker clients.
    """
    if not FINDER_AVAILABLE:
        return []
    finder = AutoWindowFinder()
    return finder.find_all_poker()


def find_by_title(title_pattern, visible_only=True):
    """Find windows whose title matches a pattern (substring or regex).

    Args:
        title_pattern: Title text (substring or regex).
        visible_only:  Only return visible windows.

    Returns:
        List of WindowMatch sorted by score.
    """
    if not FINDER_AVAILABLE:
        return []
    finder = AutoWindowFinder()
    return finder.find_all(title_pattern, visible_only=visible_only)


def find_by_process(process_name, visible_only=True):
    """Find windows belonging to a specific process.

    Args:
        process_name: Process executable name (e.g. 'pokerstars.exe').
        visible_only: Only return visible windows.

    Returns:
        List of WindowMatch sorted by score.
    """
    if not FINDER_AVAILABLE:
        return []
    finder = AutoWindowFinder()
    return finder.find_all("", by_process=process_name, visible_only=visible_only)


if __name__ == "__main__":
    print("=" * 80)
    print("WINDOW LIST + AUTO-FIND (auto_find_window.md Phase 1)")
    print("=" * 80)

    # Part 1: Raw listing
    windows = list_all_windows()

    print(f"\nTotal windows found: {len(windows)}")
    print("\nVisible windows with titles:")
    print("-" * 80)

    visible_with_title = [w for w in windows if w['visible'] and w['title'] != "(no title)"]

    for i, w in enumerate(visible_with_title[:50], 1):
        print(f"{i:3}. [{w['size']:12}] {w['title'][:50]:50} | {w['process']}")

    if len(visible_with_title) > 50:
        print(f"\n... and {len(visible_with_title) - 50} more visible windows")

    print(f"\nTotal visible windows with titles: {len(visible_with_title)}")
    print(f"Total all windows: {len(windows)}")

    # Part 2: Auto-find by keywords
    print("\n" + "=" * 80)
    print("AUTO-FIND BY KEYWORDS")
    print("=" * 80)

    test_keywords = ["Chrome", "Explorer", "Notepad", "Code", "Terminal"]
    matches = auto_find_by_keywords(test_keywords)
    print(f"\nKeywords: {test_keywords}")
    print(f"Matches found: {len(matches)}")
    for i, m in enumerate(matches[:10], 1):
        print(
            f"  {i}. [{m.score:.2f}] hwnd={m.hwnd} "
            f"'{m.title[:50]}' ({m.process_name}) "
            f"[{m.zoom_rect.w}x{m.zoom_rect.h}]"
        )

    # Part 3: Poker-room search
    print("\n" + "=" * 80)
    print("POKER ROOM AUTO-FIND")
    print("=" * 80)

    poker = find_poker_windows()
    print(f"\nPoker windows detected: {len(poker)}")
    for m in poker:
        print(
            f"  hwnd={m.hwnd} '{m.title[:50]}' ({m.process_name}) "
            f"score={m.score:.2f}"
        )

    print("\n" + "=" * 80)
    print("Done.")
    print("=" * 80)
