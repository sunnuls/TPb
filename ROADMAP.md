# HIVE POKER BOT — ПОЛНЫЙ РОУДМАП

> Создан: 03.03.2026  
> Статус: В работе

---

## ТЕКУЩЕЕ СОСТОЯНИЕ

### Что работает:
- PyQt6 GUI запускается, все вкладки, системный трей
- Win32 захват окна (PrintWindow) — лобби PS
- `auto_find_window()` — находит лобби PS по заголовку
- Anchor template matching — dealer_button, table_border, table_corner, chip_icon
- OCR сканирование лобби — строки столов, блайнды, buy-in суммы
- `read_ps_balance()` — читает баланс (нестабильно, но работает)
- `join_table()` — фокус окна, клик по строке, находит кнопку "Играть" и кликает
- DRY_RUN режим — полная симуляция цикла работает end-to-end
- Таймеры, лимиты сессии, реконнект попытки, emergency fold
- HumanTiming — задержки с нормальным распределением

### Что сломано / не работает:
- **BUY-IN ДИАЛОГ** — главный блокер, никогда не находится → бот не садится за стол в LIVE режиме
- **MouseGuard** — отключён, `pynput` не установлен
- **Live game state reading** — `NumericParser` падает обратно в симуляцию (импорт-проблема)
- **OCR кириллицы** — имена столов мусор (`"co) 6M Xongem"` вместо русского)
- **Баланс нестабилен** — 700001 → 8281 → 0 на одном экране в трёх читках подряд
- **LIVE полный цикл** — блокируется на buy-in шаге

---

## ФАЗА 0 — ПОДГОТОВКА И ФУНДАМЕНТ
*(~2-3 часа, делается один раз)*

### 0.1 Установка недостающих зависимостей
```
pip install pynput
pip install dxcam
pip install easyocr
pip install pywin32 --upgrade
```
- [ ] `pynput` — для MouseGuard
- [ ] `easyocr` — замена Tesseract для кириллицы
- [ ] Проверить что все зависимости в `requirements.txt`

### 0.2 Создание системы debug-скриншотов

- [ ] Папка `debug_screenshots/` с авто-сохранением при каждом важном событии
- [ ] Скриншоты при: сканировании лобби, клике по столу, ожидании диалога, открытии стола
- [ ] Каждый скриншот: метка времени + название события
- [ ] Флаг `debug_screenshots=True/False` в настройках

### 0.3 Режим диагностики в GUI

- [ ] Новая вкладка "Debug" или кнопка "Diagnostic Run"  
- [ ] Кнопка "Что видит бот" — снимает окно PS, показывает рядом что нашёл OCR, template matching, координаты кликов
- [ ] Кнопка "Spy Windows" — показывает все открытые окна PS (HWND, класс, размер, тип)

### 0.4 Стабилизация конфигурации аккаунтов

- [ ] `accounts.json` пуст при каждом старте — починить сохранение
- [ ] Аккаунты сохраняются при добавлении через GUI
- [ ] При старте загружаются из файла

---

## ФАЗА 1 — ПОНИМАНИЕ ЭКРАНА (WINDOW AWARENESS)
*(~1-2 дня)*

### 1.1 Система отслеживания всех окон PS

**Цель:** бот в любой момент знает какие окна открыты и что в них.

#### 1.1.1 WindowTracker — новый модуль `launcher/window_tracker.py`

- [ ] `get_all_ps_windows()` — список всех HWND окон PokerStars
- [ ] Для каждого HWND определяет тип: `LOBBY`, `TABLE`, `BUYIN_DIALOG`, `TOURNAMENT`, `CASHIER`, `UNKNOWN`
- [ ] Определение по: размер окна + заголовок + класс окна (`win32gui.GetClassName`)
- [ ] Обновление каждые 0.5 секунды в фоновом потоке
- [ ] События: `on_window_opened(hwnd, type)`, `on_window_closed(hwnd)`, `on_window_focused(hwnd)`

#### 1.1.2 Классификация типов окон
```
LOBBY:         класс "Qt5QWindowIcon" + заголовок "PokerStars" без "Table"
TABLE:         класс "PokerStarsTableFrameClass" ИЛИ заголовок содержит "Table"
BUYIN_DIALOG:  малое окно от процесса PS, класс "#32770" или кастомный PS диалог
CASHIER:       заголовок содержит "Cashier" / "Касса"
```

#### 1.1.3 Функция классификации с fallback
```python
def classify_window(hwnd) -> WindowType:
    # 1. По классу окна (самый надёжный)
    # 2. По заголовку
    # 3. По размеру (диалог = маленький)
    # 4. По скриншоту + OCR (последний резерв)
```
- [ ] Реализовать `classify_window(hwnd)`
- [ ] Покрыть тестом `tests/test_window_tracker.py`

### 1.2 Диалог Buy-in — полная переработка ⚠️ ГЛАВНЫЙ БЛОКЕР

#### 1.2.1 Диагностика диалога (нужна помощь пользователя)

**Инструмент:** `tools/spy_windows.py`

```python
import win32gui, win32process
def enum_callback(hwnd, results):
    if win32gui.IsWindowVisible(hwnd):
        title = win32gui.GetWindowText(hwnd)
        cls = win32gui.GetClassName(hwnd)
        rect = win32gui.GetWindowRect(hwnd)
        results.append((hwnd, title, cls, rect))
results = []
win32gui.EnumWindows(enum_callback, results)
for r in results:
    print(r)
```

**Действие пользователя:**
1. Открыть PS лобби
2. Кликнуть вручную на любой стол — появится диалог buy-in
3. НЕ ЗАКРЫВАТЬ диалог
4. Запустить скрипт, прислать вывод

#### 1.2.2 После диагностики — переписать `handle_buyin_dialog`

- [x] Заменить size-based поиск на поиск по заголовку 'Бай-ин' (первичный метод)
- [x] Добавить `_find_buyin_dialog_hwnd()` — надёжный поиск по title → class → size
- [x] Добавить `_analyze_buyin_dialog_children()` — находит edit/min/max/cancel/ok по дочерним HWND
- [x] Добавить `_handle_buyin_via_hwnd()` — кликает MAX затем OK напрямую по координатам
- [x] `handle_buyin_dialog()` переписан: HWND-метод первым, OCR как fallback
- [x] Протестировано: edit(1672,580), min(1384,623), max(1699,623), cancel(1453,763), ok(1625,763)

#### 1.2.3 Таймаут и повторные попытки
- [x] Таймаут увеличен с 8 до 15 секунд
- [ ] Если не появился → retry click на стол
- [ ] При любом сбое → сохранить debug скриншот

### 1.3 Определение открытия окна стола

#### 1.3.1 `wait_for_new_table_window(known_hwnds, timeout=30)`
```python
def wait_for_new_table_window(known_hwnds: set, timeout=30) -> Optional[int]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        current = get_all_ps_table_hwnds()
        new = current - known_hwnds
        if new:
            return new.pop()
        time.sleep(0.5)
    return None
```
- [ ] Реализовать функцию
- [ ] Вызывать после подтверждения buy-in

#### 1.3.2 Переместить окно стола на передний план
```python
def bring_table_to_front(hwnd):
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(hwnd)
    win32gui.BringWindowToTop(hwnd)
    # Если окно за пределами экрана — переместить
    rect = win32gui.GetWindowRect(hwnd)
    if rect[0] < -1000 or rect[1] < -1000:
        win32gui.SetWindowPos(hwnd, None, 100, 100, 0, 0,
                              win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)
```
- [ ] Реализовать `bring_table_to_front(hwnd)`

#### 1.3.3 Привязка окна стола к BotInstance
- [ ] `BotInstance` хранит `self.table_hwnd: Optional[int]`
- [ ] После нахождения TABLE окна — привязать к боту
- [ ] Все скриншоты и клики — только через этот HWND

---

## ФАЗА 2 — OCR И ЧТЕНИЕ СОСТОЯНИЯ СТОЛА
*(~1-2 дня)*

### 2.1 Улучшение OCR для кириллицы

#### 2.1.1 Замена Tesseract на EasyOCR
```python
# launcher/vision/ocr_engine.py — новый модуль
import easyocr
reader = easyocr.Reader(['ru', 'en'], gpu=False)  # один раз при старте

def ocr_text(image, lang='ru+en') -> str:
    results = reader.readtext(image)
    return ' '.join([r[1] for r in results])
```
- [ ] Создать `launcher/vision/ocr_engine.py`
- [ ] Обернуть EasyOCR + Tesseract fallback
- [ ] Заменить прямые `pytesseract` вызовы на новый модуль

#### 2.1.2 Препроцессинг изображения перед OCR
```python
def preprocess_for_ocr(img):
    img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(gray, 255,
                                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                    cv2.THRESH_BINARY, 11, 2)
    denoised = cv2.fastNlMeansDenoising(thresh, h=10)
    return denoised
```
- [ ] Реализовать `preprocess_for_ocr(img)`
- [ ] Применить ко всем OCR вызовам

#### 2.1.3 Стабилизация чтения баланса
- [ ] Читать баланс 3 раза подряд, брать медиану
- [ ] Валидация: если новое значение отличается от предыдущего в 10x — игнорировать
- [ ] Несколько ROI зон для баланса (разные PS темы)

```python
def read_balance_stable(hwnd, n_reads=3) -> Optional[float]:
    reads = []
    for _ in range(n_reads):
        val = read_balance_once(hwnd)
        if val and val > 0:
            reads.append(val)
        time.sleep(0.1)
    if not reads:
        return None
    reads.sort()
    return reads[len(reads)//2]  # медиана
```

### 2.2 Чтение состояния стола (Table State)

**Цель бота на столе — понимать:**
- Свои карты (2 карты)
- Карты на борде (0-5 карт)
- Текущую ставку (to call)
- Размер банка (pot)
- Свой стек
- Доступные кнопки: Fold / Call / Raise / Check / Bet
- Чей сейчас ход

#### 2.2.1 Новый модуль `bridge/vision/table_screen_reader.py`

- [ ] Захватить скриншот окна стола через HWND
- [ ] Определить масштаб (разрешение окна vs базовое 1920×1080)
- [ ] Применить масштабированные ROI зоны
- [ ] OCR / цвет / template matching для каждой зоны

#### 2.2.2 ROI зоны стола в процентах (не пиксели!)

```yaml
# config/rooms/pokerstars_table.yaml
hero_cards:
  x1_pct: 0.40  y1_pct: 0.70  x2_pct: 0.60  y2_pct: 0.90

board_cards:
  x1_pct: 0.30  y1_pct: 0.40  x2_pct: 0.70  y2_pct: 0.58

pot_amount:
  x1_pct: 0.40  y1_pct: 0.35  x2_pct: 0.60  y2_pct: 0.45

btn_fold:
  x1_pct: 0.25  y1_pct: 0.87  x2_pct: 0.40  y2_pct: 0.96

btn_call:
  x1_pct: 0.43  y1_pct: 0.87  x2_pct: 0.57  y2_pct: 0.96

btn_raise:
  x1_pct: 0.60  y1_pct: 0.87  x2_pct: 0.75  y2_pct: 0.96

raise_amount_field:
  x1_pct: 0.60  y1_pct: 0.80  x2_pct: 0.75  y2_pct: 0.87

hero_stack:
  x1_pct: 0.42  y1_pct: 0.90  x2_pct: 0.58  y2_pct: 0.98
```
- [ ] Создать `config/rooms/pokerstars_table.yaml`
- [ ] Координаты уточнить после калибровки (Фаза 5.1)

#### 2.2.3 Определение кнопок — два подхода с fallback

**Подход A — Template Matching:**
- [ ] Сохранить шаблоны кнопок Fold/Call/Raise/Check как PNG (32×32 px) в `config/templates/`
- [ ] `cv2.matchTemplate` на скриншоте стола

**Подход B — OCR (fallback):**
- [ ] Взять нижние 15% высоты окна стола
- [ ] OCR: найти "Fold"/"Сбросить", "Call"/"Коллировать", "Raise"/"Повысить", "Check"/"Чек"
- [ ] По тексту определить центр кнопки

#### 2.2.4 Определение карт — использовать YOLO

- [ ] Использовать YOLOv8 модель из `Playing Cards.v4-...` (уже есть в проекте)
- [ ] Запускать YOLO на ROI зоне карт героя и борда
- [ ] Конвертировать YOLO label → карта (`Ac`, `Kh`, `2d`, etc.)

#### 2.2.5 Определение "чей ход"

- [ ] Детект таймера в зоне героя (HSV поиск желтого/оранжевого)
- [ ] Проверить активность кнопок (серые/disabled = не наш ход)
- [ ] OCR поиск "Your Turn" / подсветки

#### 2.2.6 Датакласс TableState
```python
@dataclass
class TableState:
    hero_cards: List[str]        # ['Ac', 'Kh']
    board_cards: List[str]       # ['2d', '7s', 'Jc']
    pot: float                   # 150.0
    to_call: float               # 50.0 (0 если чек)
    hero_stack: float            # 980.0
    available_actions: List[str] # ['fold', 'call', 'raise']
    is_my_turn: bool
    hand_ended: bool
    street: str                  # 'preflop'/'flop'/'turn'/'river'
```
- [ ] Создать в `sim_engine/state/table_state.py` (расширить существующий)

---

## ФАЗА 3 — ЧЕЛОВЕКОПОДОБНОЕ ВЗАИМОДЕЙСТВИЕ
*(~1 день)*

### 3.1 Движение мыши по кривым Безье

#### 3.1.1 Новый модуль `bridge/action/human_mouse.py`
```python
def bezier_path(start, end, n_points=50):
    """Генерирует путь по кривой Безье с случайными контрольными точками"""
    cp1 = (
        start[0] + (end[0]-start[0])*0.33 + random.randint(-30, 30),
        start[1] + (end[1]-start[1])*0.33 + random.randint(-30, 30)
    )
    cp2 = (
        start[0] + (end[0]-start[0])*0.66 + random.randint(-30, 30),
        start[1] + (end[1]-start[1])*0.66 + random.randint(-30, 30)
    )
    # Вычислить точки кривой...

def human_move_and_click(x, y, click=True):
    """Движение по Безье с easing + случайное смещение от точки клика"""
    # Easing: медленно в начале и конце, быстро в середине
    # Смещение клика: random.randint(-3, 3) по обоим осям
    # Удержание кнопки: random.uniform(0.08, 0.25) секунды
```
- [ ] Реализовать `bezier_path(start, end, n_points)`
- [ ] Реализовать `human_move_and_click(x, y, click=True)`
- [ ] Заменить все `pyautogui.moveTo` + `pyautogui.click` на новую функцию

### 3.2 Задержки принятия решений

#### 3.2.1 Функция задержки по типу действия
```python
def get_action_delay(action, hand_strength=0.5, is_bluff=False) -> float:
    base = {
        'fold':  random.uniform(1.0, 3.0),  # быстро
        'check': random.uniform(0.5, 2.0),  # быстро
        'call':  random.uniform(1.5, 4.0),  # думаем
        'bet':   random.uniform(2.0, 6.0),  # думаем
        'raise': random.uniform(2.5, 8.0),  # долго думаем
    }.get(action, 2.0)
    
    if is_bluff:
        base *= random.uniform(1.2, 1.8)
    
    if hand_strength > 0.85 and random.random() < 0.3:
        base *= random.uniform(1.5, 2.5)  # slowplay
    
    if random.random() < 0.05:  # 5% — отвлёкся
        base += random.uniform(5, 15)
    
    return base
```
- [ ] Реализовать `get_action_delay()` в `bridge/timing/human_timing.py`
- [ ] Интегрировать в `_execute_action()` в `bot_instance.py`

### 3.3 MouseGuard — восстановить
- [ ] `pip install pynput`
- [ ] `launcher/mouse_guard.py` уже написан — просто работает после установки

### 3.4 Ввод суммы ставки
- [ ] Тройной клик для выделения всего текста в поле
- [ ] Ctrl+A для надёжности
- [ ] Посимвольный ввод с задержками `random.uniform(0.05, 0.15)` между символами

---

## ФАЗА 4 — ПОЛНЫЙ ЦИКЛ ИГРЫ
*(~1-2 дня)*

### 4.1 Расширенная машина состояний BotInstance

**Текущие состояния:** `IDLE → SEARCHING → SEATED → PLAYING`

**Нужно:**
```
IDLE
 ↓
SCANNING_LOBBY       ← сканируем лобби, ищем стол
 ↓
CLICKING_TABLE       ← кликнули по строке стола
 ↓
WAITING_BUYIN        ← ждём диалог buy-in (таймаут 15с)
 ↓
HANDLING_BUYIN       ← заполняем и подтверждаем buy-in
 ↓
WAITING_TABLE        ← ждём открытия окна стола (таймаут 30с)
 ↓
SEATED               ← нашли окно стола, распарсили начальное состояние
 ↓
WAITING_TURN         ← не наш ход, мониторим стол
 ↓
MY_TURN              ← наш ход, принимаем решение
 ↓
ACTING               ← выполняем действие (клик)
 ↓
WAITING_RESULT       ← ждём обновления стола
```

- [ ] Добавить новые состояния в `BotState` enum
- [ ] Реализовать переходы между состояниями
- [ ] Таймаут при застревании > N секунд → возврат в IDLE
- [ ] Логировать каждый переход с временем

### 4.2 Game Loop

#### 4.2.1 `_wait_for_my_turn(max_wait=60) -> bool`
```python
def _wait_for_my_turn(self, max_wait=60) -> bool:
    deadline = time.time() + max_wait
    while time.time() < deadline:
        state = self._read_table_state()
        if state.is_my_turn:
            return True
        if state.hand_ended:
            return False
        time.sleep(0.3)
    return False
```
- [ ] Реализовать в `BotInstance`

#### 4.2.2 `_read_table_state() -> TableState`
- [ ] Захватить скриншот `self.table_hwnd`
- [ ] Применить `TableScreenReader`
- [ ] Вернуть заполненный `TableState`

#### 4.2.3 `_decide_action(state: TableState) -> Action`
- [ ] Интеграция с `PokerAI.decide()`
- [ ] Передавать: карты, борд, пот, to_call, стек, позицию

#### 4.2.4 `_execute_action(action, amount=None)`
- [ ] Задержка `get_action_delay(action, ...)`
- [ ] Найти координату кнопки через `_find_button(action)`
- [ ] Если raise + amount → сначала `enter_raise_amount()`
- [ ] `human_move_and_click(*btn_pos)`
- [ ] Логировать действие

### 4.3 Обработка нестандартных ситуаций

#### 4.3.1 Попапы во время игры
- [ ] Обнаружение дочерних окон с нежелательными диалогами
- [ ] Авто-закрытие: реклама, предложение добавить фишки, ошибки соединения
- [ ] При ошибке соединения → пауза + попытка восстановления

#### 4.3.2 Потеря окна стола
- [ ] Проверять `win32gui.IsWindow(self.table_hwnd)` каждый тик
- [ ] При потере → сохранить debug скриншот → вернуться в `SCANNING_LOBBY`

#### 4.3.3 Исправить AttributeError `current_hand_action_count`
- [ ] Добавить `self.current_hand_action_count = 0` в `__init__`
- [ ] Сбрасывать в 0 при начале новой руки

---

## ФАЗА 5 — КАЛИБРОВКА И ОБУЧЕНИЕ
*(по необходимости)*

### 5.1 Инструмент калибровки ROI `tools/roi_calibrator.py`

- [ ] GUI инструмент на tkinter или PyQt6
- [ ] Захватывает скриншот нужного окна PS
- [ ] Пользователь рисует прямоугольники вокруг элементов
- [ ] Инструмент сохраняет координаты как проценты в YAML
- [ ] Элементы для калибровки:
  - Лобби: balance, nickname, table rows area
  - Стол: hero cards, board cards, pot, fold/call/raise buttons, raise amount field, hero stack

**Действие пользователя: ~20-30 минут**

### 5.2 Сбор датасета для обучения (если YOLO плохо работает)

- [ ] Запустить PS, раздать карты
- [ ] Сохранять скриншоты зон карт (автоматически через debug mode)
- [ ] Разметить в LabelImg (~200-300 примеров)
- [ ] Дообучить YOLOv8n на новых данных (`yolo train model=yolov8n.pt`)

### 5.3 Шаблоны для template matching кнопок

- [ ] Собрать 50+ скриншотов кнопок Fold/Call/Raise в разных состояниях
- [ ] Сохранить шаблоны в `config/templates/buttons/`
- [ ] Протестировать `cv2.matchTemplate` с `TM_CCOEFF_NORMED` порогом 0.8

### 5.4 Обучение классификатора состояния стола (опционально)

- [ ] YOLOv8 классификатор для: наличие карт у героя, улица (preflop/flop/turn/river), активен ли таймер
- [ ] ~100-200 скриншотов на класс

---

## ФАЗА 6 — ТЕСТИРОВАНИЕ И СТАБИЛИЗАЦИЯ
*(непрерывно)*

### 6.1 Пошаговый тест-план

- [ ] **Тест 0:** Запустить `tools/spy_windows.py` при открытом диалоге buy-in
- [ ] **Тест 1:** `WindowTracker` видит все окна PS с правильным типом
- [ ] **Тест 2:** Диалог buy-in находится и заполняется автоматически
- [ ] **Тест 3:** После buy-in находится окно стола
- [ ] **Тест 4:** На открытом столе читаются карты и кнопки
- [ ] **Тест 5:** Определяется когда ход нашего бота
- [ ] **Тест 6:** Кнопки кликаются правильно
- [ ] **Тест 7:** Полный цикл: лобби → стол → buy-in → сел → сыграл руку

### 6.2 Расширенное логирование

- [ ] Логировать каждое состояние машины состояний с временем
- [ ] Сохранять скриншот при каждой смене состояния (в debug режиме)
- [ ] В `session_log.py` добавить:
  - Время в каждом состоянии
  - Причина перехода
  - Количество ошибок per-состояние

---

## ЧТО НУЖНО ОТ ПОЛЬЗОВАТЕЛЯ

### Приоритет 1 — ПРЯМО СЕЙЧАС (5 минут):
1. Запустить PS, открыть лобби
2. Кликнуть вручную на любой стол → появится диалог buy-in
3. **НЕ ЗАКРЫВАТЬ диалог**
4. В консоли запустить:
```powershell
cd C:\proekt-i\Tg_Pkr_Bot
.venv\Scripts\python.exe -c "
import win32gui
def cb(h, r):
    if win32gui.IsWindowVisible(h):
        print(h, repr(win32gui.GetWindowText(h)), win32gui.GetClassName(h), win32gui.GetWindowRect(h))
win32gui.EnumWindows(cb, None)
"
```
5. Прислать вывод → сразу починим buy-in диалог

### Приоритет 2 — Калибровка ROI (20-30 минут):
- После создания `tools/roi_calibrator.py` — потыкать мышкой на скриншоте
- Все координаты кнопок и зон будут точными

### Приоритет 3 — Скриншоты (по желанию):
- Скриншоты стола PS во время раздачи (карты видны, кнопки активны)
- Улучшит OCR и template matching

---

## ПОРЯДОК РЕАЛИЗАЦИИ

| # | Задача | Зависит от | Время |
|---|--------|-----------|-------|
| 1 | Диагностика buy-in диалога | Пользователя (5 мин) | 10 мин |
| 2 | Починить `handle_buyin_dialog` | #1 | 2 часа |
| 3 | `WindowTracker` | — | 3 часа |
| 4 | OCR → EasyOCR + препроцессинг | — | 2 часа |
| 5 | `tools/roi_calibrator.py` | — | 3 часа |
| 6 | Калибровка ROI | Пользователя (20 мин) | 20 мин |
| 7 | `TableScreenReader` | #5, #6 | 4 часа |
| 8 | Bezier движение мыши | — | 2 часа |
| 9 | Расширенная машина состояний | #2, #3, #7 | 4 часа |
| 10 | `_wait_for_my_turn` + Game Loop | #7, #9 | 3 часа |
| 11 | `_decide_action` → PokerAI интеграция | #10 | 2 часа |
| 12 | Попапы + потеря окна | #9 | 2 часа |
| 13 | Полный тест цикла | #12 | 1 день |

**Итого:** ~3-4 дня разработки + ~1 час участия пользователя

---

## БЫСТРЫЕ ИСПРАВЛЕНИЯ (можно сделать сейчас)

Эти баги не требуют информации от пользователя и мешают работе:

- [ ] `AttributeError: current_hand_action_count` — добавить в `__init__`
- [ ] `accounts.json` не сохраняется — починить `BotAccountBinder.save()`
- [ ] `pynput` не установлен — добавить в `requirements.txt`
- [ ] `StateBridge` fallback в симуляцию — найти и починить импорт-проблему
- [ ] `_seated_since` не в `__init__` — перенести

---

*Роудмап создан на основе анализа всего кода проекта: 103 файла в launcher/, 57 файлов в bridge/, 40 файлов в sim_engine/, 17 файлов в hive/*
