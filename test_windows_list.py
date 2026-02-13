image.png"""
Test script to list all windows without any filters.
"""

import win32gui
import win32process

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
                except:
                    process_name = f"pid_{pid}"
            except:
                process_name = "unknown"
            
            results.append({
                'hwnd': hwnd,
                'title': title or "(no title)",
                'visible': visible,
                'size': f"{width}x{height}",
                'process': process_name
            })
        except Exception as e:
            pass
    
    win32gui.EnumWindows(callback, windows)
    return windows

if __name__ == "__main__":
    print("=" * 80)
    print("ALL WINDOWS (NO FILTERS)")
    print("=" * 80)
    
    windows = list_all_windows()
    
    print(f"\nTotal windows found: {len(windows)}")
    print("\nVisible windows with titles:")
    print("-" * 80)
    
    visible_with_title = [w for w in windows if w['visible'] and w['title'] != "(no title)"]
    
    for i, w in enumerate(visible_with_title[:50], 1):  # Show first 50
        print(f"{i:3}. [{w['size']:12}] {w['title'][:50]:50} | {w['process']}")
    
    if len(visible_with_title) > 50:
        print(f"\n... and {len(visible_with_title) - 50} more visible windows")
    
    print(f"\nTotal visible windows with titles: {len(visible_with_title)}")
    print(f"Total all windows: {len(windows)}")
    print("=" * 80)
