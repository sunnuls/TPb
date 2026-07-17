# HIVE — этапы до рабочей сетки ботов

## Этап 0 — Чистка и политика ✅
- Удалить debug/temp артефакты, устаревшие отчёты
- Переписать POLICY под обычный продукт без «ILLEGAL / educational only»
- Убрать красные баннеры и стартовые диалоги-страшилки в launcher
- Разблокировать realtime poker в coach_app policy

## Этап 1 — Один живой бот (desktop или MuMu) 🔧
- Стабильный захват экрана + ROI (Win32 / ADB MuMu)
- Чтение карт / пота / кнопок без simulation fallback в LIVE
  - `NumericParser` — реальный pytesseract OCR
  - `StateBridge` — fail-closed (None), без подстановки симуляции
- Клик fold/call/raise в LIVE (desktop + emulator backend)
- Buy-in / посадка за стол на одном клиенте
  - `AutoSeating` → реальный `NavigationManager.join_table`
  - Stage 1: `min_team_size=1` (launcher), HIVE до 3
  - PS buy-in dialog + CP Take Seat / короткий buy-in wait
  - `LobbyTable.room` для CoinPoker и PokerStars

## Этап 2 — Три бота за одним столом
- Рассадка команды 3 ботов (уже не placeholder)
- Обмен картами влияет на решение (не solo PokerAI)
- ManipulationEngine в live-цикле
- CentralHub / in-process sharing end-to-end

## Этап 3 — Эмуляторный парк
- EmulatorManager в GUI (discover / bind / health)
- Мобильный ROI под PokerStars/другой клиент
- 3–10 инстансов MuMu на одной машине

## Этап 4 — Масштаб сетки
- Оркестрация команд N×3
- Proxy / fingerprint на инстанс
- Мониторинг и auto-restart

---

**Критерий готовности идеи:** этап 2 закрыт на живом клиенте.
