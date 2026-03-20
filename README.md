# igs-proxy

[Русский](#русский) | [English](#english)

---

## Русский

Простой reverse proxy для gm-donate API. Поднимается в докере, пробрасывает все запросы на upstream и возвращает ответ как есть.

### Зачем

Нужен был прокси чтобы не светить реальный эндпоинт и иметь возможность ограничить доступ по IP.

### Запуск

```bash
# сначала отредактируй .env, потом:
docker-compose up -d
```

Слушает на `http://localhost:8000`.

### Конфиг (.env)

| Переменная | По умолчанию | Описание |
|---|---|---|
| `API_ENDPOINT` | `https://gm-donate.net/api` | Куда проксировать запросы |
| `PROXY_TIMEOUT` | `30.0` | Таймаут в секундах |
| `ALLOWED_IPS` | пусто | Whitelist IP/CIDR, пусто = все разрешены |

Примеры `ALLOWED_IPS`:
```
ALLOWED_IPS=1.2.3.4                          # один IP
ALLOWED_IPS=1.2.3.4,5.6.7.8                  # несколько
ALLOWED_IPS=10.0.0.0/8,192.168.1.0/24        # диапазоны
ALLOWED_IPS=                                  # отключить whitelist
```

### Интеграция с igs-core

В `config_sv.lua` укажи адрес прокси как эндпоинт API:

```lua
IGS_API_ENDPOINT = "https://127.0.0.1:8000/"
```

### Стек

- FastAPI + uvicorn
- httpx с HTTP/2
- Python 3.11


## English

Simple reverse proxy for the gm-donate API. Runs in Docker, forwards all requests to upstream and returns the response as-is.

### Why

Needed a proxy to hide the real endpoint and restrict access by IP if necessary.

### Usage

```bash
# edit .env first, then:
docker-compose up -d
```

Listens on `http://localhost:8000`.

### Config (.env)

| Variable | Default | Description |
|---|---|---|
| `API_ENDPOINT` | `https://gm-donate.net/api` | Upstream to proxy requests to |
| `PROXY_TIMEOUT` | `30.0` | Request timeout in seconds |
| `ALLOWED_IPS` | empty | IP/CIDR whitelist, empty = allow all |

`ALLOWED_IPS` examples:
```
ALLOWED_IPS=1.2.3.4                          # single IP
ALLOWED_IPS=1.2.3.4,5.6.7.8                  # multiple IPs
ALLOWED_IPS=10.0.0.0/8,192.168.1.0/24        # CIDR ranges
ALLOWED_IPS=                                  # disable whitelist
```

### Integration with igs-core

In `config_sv.lua` set the proxy address as the API endpoint:

```lua
IGS_API_ENDPOINT = "https://127.0.0.1:8000/"
```

### Stack

- FastAPI + uvicorn
- httpx with HTTP/2
- Python 3.11

---

