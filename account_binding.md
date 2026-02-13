
#### 9. Roadmap for Bot Not Understanding Account (account_binding.md)

```markdown
# account_binding.md — Фикс привязки бота к аккаунту

Цель: сделать так, чтобы бот знал свой аккаунт.

## Фаза 1 — Binder module
- Добавить bot_account_binder.py — ассоциация bot ID с ником/окном/ROI

## Фаза 2 — Load at start
- Обновить bot_instance.py — загрузка binding при запуске

## Фаза 3 — Тесты
- Тест: 5 ботов → каждый знает свой ник/окно

