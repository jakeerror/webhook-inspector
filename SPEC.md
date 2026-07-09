# SPEC.md — Webhook Inspector

Инструмент для отладки вебхуков: создаёшь временный endpoint («bin»), получаешь
публичный URL, направляешь туда вебхуки (Stripe, GitHub, Telegram и т.д.) и
видишь входящие запросы **в реальном времени** — с заголовками, телом, метаданными.
Можно переслать (replay) захваченный запрос на свой адрес.

> Spec-first: код не пишется, пока не зафиксирован этот документ. v1-границы ниже.

---

## 1. Назначение и границы

**В границах v1:**
- Создание bin (анонимно, без регистрации) → публичный URL `/in/{binId}`.
- Захват запросов **любым HTTP-методом** на `/in/{binId}` и `/in/{binId}/{путь...}`:
  метод, путь-суффикс, query, заголовки, тело (raw + попытка распарсить JSON), IP, размер, время.
- Просмотр истории запросов bin и деталей одного запроса.
- **Live-tail** новых запросов через WebSocket (без перезагрузки).
- **Replay** — сервер повторяет захваченный запрос на указанный `target_url` (со SSRF-защитой).
- TTL: bin и его запросы живут N дней (по умолчанию 7), потом удаляются фоновой задачей.
- Лимиты: размер тела (256 KB), число запросов на bin (кольцевое, 500), rate limit на ingest и создание bins.

**Вне границ v1 (осознанно):**
- Аутентификация/аккаунты (модель анонимная, как webhook.site — знание `binId` = доступ; ADR-001).
- Кастомные ответы bin (bin всегда отвечает `200 {"ok":true}`), проксирование в реальном времени.
- Поиск/фильтры по телу, экспорт, командный доступ.

---

## 2. Доменная модель

### Bin
| Поле | Тип | Описание |
|------|-----|----------|
| id | str(16) PK | случайный URL-safe slug (напр. `a1b2c3d4e5`) |
| created_at | timestamptz | |
| expires_at | timestamptz, indexed | момент истечения (created_at + TTL) |
| request_count | int | счётчик захваченных (для кольцевого лимита) |

### CapturedRequest
| Поле | Тип | Описание |
|------|-----|----------|
| id | bigint PK | |
| bin_id | FK→Bin, ondelete CASCADE, indexed | |
| method | str(10) | GET/POST/… |
| path | str(1024) | суффикс после `/in/{binId}` (может быть пустым) |
| query | json | параметры строки запроса |
| headers | json | заголовки (как словарь; чувствительные не маскируем в v1) |
| content_type | str(255), nullable | |
| body | text | тело, усечённое до лимита |
| body_truncated | bool | было ли тело обрезано |
| source_ip | str(64) | IP отправителя |
| size_bytes | int | исходный размер тела |
| created_at | timestamptz, indexed | |

---

## 3. API (префикс `/api/v1`, кроме ingest и ws)

### Bins
| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/v1/bins` | Создать bin → `{id, url, expires_at}`. **Rate limited** |
| GET | `/api/v1/bins/{id}` | Метаданные bin (404 если нет/истёк) |
| DELETE | `/api/v1/bins/{id}` | Удалить bin и его запросы |
| GET | `/api/v1/bins/{id}/requests?limit=&before=` | История захваченных (новые первыми) |
| GET | `/api/v1/bins/{id}/requests/{rid}` | Детали одного запроса |
| POST | `/api/v1/bins/{id}/requests/{rid}/replay` | Переслать запрос на `{target_url}`; SSRF-guard → возвращает `{status, duration_ms}` |

### Ingest (захват — публичный, любой метод)
| Метод | Путь | Описание |
|-------|------|----------|
| ANY | `/in/{id}` и `/in/{id}/{path:path}` | Захватить запрос → сохранить → опубликовать в live → ответить `200 {"ok":true, "request_id": ...}`. **Rate limited.** 404 если bin нет/истёк; 413 если тело > лимита |

### Live
| Путь | Описание |
|------|----------|
| WS `/ws/bins/{id}` | При подключении — подтверждение; далее события о новых запросах |

### Service
| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/health` | Liveness: БД + Redis |

---

## 4. WebSocket-протокол

Клиент подключается к `/ws/bins/{id}`. Сервер шлёт JSON-сообщения:
```jsonc
{ "type": "connected", "bin_id": "a1b2c3d4e5" }
{ "type": "request", "data": { /* CapturedRequest в кратком виде: id, method, path, content_type, size_bytes, created_at */ } }
```
Полные детали запроса клиент при желании догружает через `GET /requests/{rid}`.
Реализация live: новый запрос → публикация в Redis pub/sub канал `bin:{id}` → все api-инстансы,
у которых есть подписанные сокеты на этот bin, рассылают событие. Без Redis — рассылка в пределах процесса (graceful degradation).

---

## 5. Безопасность — SSRF-защита при replay (ключевая изюминка)

Replay заставляет **сервер** сделать исходящий запрос на пользовательский `target_url` —
классический вектор SSRF. Политика:
1. Разрешены только схемы `http`/`https`.
2. Хост резолвится в IP; **запрещены** приватные/служебные диапазоны:
   `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16` (link-local, в т.ч. cloud metadata `169.254.169.254`), `::1`, `fc00::/7`, `fe80::/10`, `0.0.0.0/8`.
3. Таймаут (5с), запрет редиректов (иначе можно увести на приватный адрес), лимит размера ответа.
4. Все проверки покрыты тестами (параметризованный список запрещённых адресов).

---

## 6. Ошибки

Единый формат `{"detail": "..."}` (FastAPI-стиль).

| Код | Когда |
|-----|-------|
| 400 | Некорректный запрос (битый `target_url`) |
| 404 | Bin/запрос не найден или bin истёк |
| 413 | Тело запроса превышает лимит |
| 422 | Ошибка валидации тела (Pydantic) — напр. `target_url` не URL |
| 429 | Превышен rate limit |
| 502 | Replay: целевой сервер недоступен |
| 403 | Replay: `target_url` заблокирован SSRF-политикой |

---

## 7. Использование Redis
1. **Live pub/sub** — канал `bin:{id}` для рассылки событий по WebSocket между инстансами.
2. **Rate limiting** — ingest (напр. 120/min на IP) и создание bins (20/min на IP), INCR+EXPIRE, fail-open.
3. (Кэш метаданных bin — опционально; в v1 не требуется.)

---

## 8. Стек и структура

Python 3.12 · FastAPI · SQLAlchemy 2.0 async + Alembic · Pydantic v2 · redis.asyncio · httpx (replay) · pytest + fakeredis. Front: React + TS + Vite + TanStack Query. Docker Compose (api, db, redis, web). CI: ruff + pytest / eslint + build / docker compose build.

```
webhook-inspector/
├── backend/  app/{api,core,db,models,schemas,services}/ + alembic/ + tests/
├── frontend/ src/{api,components,pages}/
├── docker-compose.yml   # api, db, redis, web (backend-образ собирается один раз)
├── .github/workflows/ci.yml
├── SPEC.md / DECISIONS.md / README.md / .env.example / .gitignore
```

---

## 9. План (без пауз, самопроверка после каждого шага)
1. SPEC (этот файл). 2. Модели + миграция. 3. API (bins/ingest/replay/health). 4. WebSocket + Redis pub/sub. 5. Тесты (ingest, лимиты, TTL, **SSRF**, replay, WS, rate limit). 6. Фронтенд (создать bin → live-tail → детали → replay). 7. Docker Compose + live E2E. 8. CI. 9. README.
