
#### 4. Roadmap for Scaling 5/10 (scaling.md)

```markdown
# scaling.md — Масштабирование на 100+ ботов

Цель: стабильный запуск 100+ без крашей.

## Фаза 1 — Proxy pool
- Добавить proxy_manager.py — ротация IPs (proxychains or requests)

## Фаза 2 — Fingerprint spoofing
- Добавить device_emulation.py — stubs for fingerprint (browser headers if web)

## Фаза 3 — Auto-restart
- Добавить monitoring + restart failed bots in launcher/
- Тест: 100 ботов 24 часа (test_config.py adapt)

