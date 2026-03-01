# docker-compose.yml (Development)

The `docker-compose.yml` file defines the local development environment. It runs three containers: PostgreSQL, Django, and Nginx.

---

## Full File

```yaml
services:

  db:
    image: postgres:16-alpine
    container_name: blog_postgres
    restart: unless-stopped
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB:       blog_db
      POSTGRES_USER:     bloguser
      POSTGRES_PASSWORD: blogpass123
    expose:
      - "5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U bloguser -d blog_db"]
      interval: 10s
      timeout: 5s
      retries: 5

  web:
    build: .
    container_name: blog_django
    restart: unless-stopped
    env_file: .env
    volumes:
      - static_volume:/app/staticfiles
    expose:
      - "8000"
    depends_on:
      db:
        condition: service_healthy

  nginx:
    image: nginx:1.27-alpine
    container_name: blog_nginx
    restart: unless-stopped
    ports:
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - static_volume:/vol/static:ro
    depends_on:
      - web

volumes:
  postgres_data:
  static_volume:
```

---

## Service: db (PostgreSQL)

```yaml
db:
  image: postgres:16-alpine
  container_name: blog_postgres
  restart: unless-stopped
  volumes:
    - postgres_data:/var/lib/postgresql/data
  environment:
    POSTGRES_DB:       blog_db
    POSTGRES_USER:     bloguser
    POSTGRES_PASSWORD: blogpass123
  expose:
    - "5432"
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U bloguser -d blog_db"]
    interval: 10s
    timeout: 5s
    retries: 5
```

| Setting | Explanation |
|---------|-------------|
| `image: postgres:16-alpine` | Uses the official lightweight Alpine-based Postgres 16 image |
| `container_name: blog_postgres` | Fixed name so other containers can reference it reliably |
| `restart: unless-stopped` | Automatically restarts if it crashes, but not if manually stopped |
| `postgres_data:/var/lib/postgresql/data` | Named volume so database data persists across `docker compose down` (without `-v`) |
| `environment` | Credentials are hardcoded for local dev — no `.env` file needed |
| `expose: "5432"` | Makes port 5432 available to other containers on the same network, but **not** to the host machine |
| `healthcheck` | Runs `pg_isready` every 10s to check if Postgres is accepting connections. Other services use this to wait before starting |

---

## Service: web (Django + Gunicorn)

```yaml
web:
  build: .
  container_name: blog_django
  restart: unless-stopped
  env_file: .env
  volumes:
    - static_volume:/app/staticfiles
  expose:
    - "8000"
  depends_on:
    db:
      condition: service_healthy
```

| Setting | Explanation |
|---------|-------------|
| `build: .` | Builds the image from the `Dockerfile` in the current directory. In dev we build locally instead of pulling from Docker Hub |
| `env_file: .env` | Loads all variables from `.env` into the container's environment (SECRET_KEY, DB settings, etc.) |
| `static_volume:/app/staticfiles` | Shared named volume — `collectstatic` writes here, Nginx reads from here |
| `expose: "8000"` | Available to other containers (Nginx) but not directly to the host |
| `depends_on: condition: service_healthy` | Waits until Postgres passes its healthcheck before starting. Prevents Django crashing on startup because the DB isn't ready yet |

---

## Service: nginx

```yaml
nginx:
  image: nginx:1.27-alpine
  container_name: blog_nginx
  restart: unless-stopped
  ports:
    - "80:80"
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    - static_volume:/vol/static:ro
  depends_on:
    - web
```

| Setting | Explanation |
|---------|-------------|
| `ports: "80:80"` | Binds host port 80 to container port 80 — this is the only container accessible from your browser |
| `./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro` | Mounts the local config file into Nginx. `:ro` means read-only — Nginx cannot modify it |
| `static_volume:/vol/static:ro` | Shares the same volume as `web`. Nginx serves static files directly without going through Django |
| `depends_on: web` | Starts after the web container (though this is a soft dependency — doesn't wait for Django to be ready) |

---

## Volumes

```yaml
volumes:
  postgres_data:
  static_volume:
```

Named volumes managed by Docker:

| Volume | Purpose |
|--------|---------|
| `postgres_data` | Persists the PostgreSQL database files between restarts |
| `static_volume` | Shared between `web` (writes) and `nginx` (reads) for static assets |

---

## Key Difference from Production

The main difference in dev is `build: .` vs `image:` — dev builds the image locally from source, production pulls a pre-built image from Docker Hub. Also in dev, Nginx binds directly to port 80 on the host (`ports: "80:80"`), whereas in production it uses `expose` only and sits behind a shared proxy.

---

## Common Commands

```bash
# Start everything
docker compose up -d

# Rebuild after code changes
docker compose up -d --build

# View logs
docker compose logs -f web

# Stop and remove containers (keeps volumes)
docker compose down

# Stop and remove containers AND volumes (wipes database)
docker compose down -v

# Run a Django management command
docker exec -it blog_django python manage.py createsuperuser
```
