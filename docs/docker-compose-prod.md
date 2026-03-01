# docker-compose.prod.yml (Production)

The `docker-compose.prod.yml` file defines the production environment running on the Hetzner VPS. It is nearly identical to the dev compose file but with key differences for a multi-project server setup.

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
      POSTGRES_DB:       ${DB_NAME}
      POSTGRES_USER:     ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    expose:
      - "5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 10s
      timeout: 5s
      retries: 5

  web:
    image: ${DOCKERHUB_USERNAME}/inkwell:latest
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
    expose:
      - "80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - static_volume:/vol/static:ro
    depends_on:
      - web
    networks:
      - default
      - proxy_network

volumes:
  postgres_data:
  static_volume:

networks:
  proxy_network:
    external: true
```

---

## Differences from Development

| | `docker-compose.yml` (dev) | `docker-compose.prod.yml` (prod) |
|--|---------------------------|----------------------------------|
| Django image | `build: .` (built locally) | `image: user/inkwell:latest` (pulled from Docker Hub) |
| DB credentials | Hardcoded in file | Read from `.env` via `${VAR}` |
| Nginx port binding | `ports: "80:80"` (direct) | `expose: "80"` (internal only) |
| Networks | Single default network | Default + external `proxy_network` |

---

## Service: db (PostgreSQL)

```yaml
db:
  environment:
    POSTGRES_DB:       ${DB_NAME}
    POSTGRES_USER:     ${DB_USER}
    POSTGRES_PASSWORD: ${DB_PASSWORD}
```

In production, credentials are not hardcoded. The `${VAR}` syntax reads values from the `.env` file in the same directory (`~/inkwell/.env` on the server). This keeps secrets out of the repository.

The `.env` file on the server looks like:
```
DB_NAME=blog_db
DB_USER=bloguser
DB_PASSWORD=a_strong_password_here
```

Everything else (`healthcheck`, `volumes`, `expose`) is the same as dev.

---

## Service: web (Django + Gunicorn)

```yaml
web:
  image: ${DOCKERHUB_USERNAME}/inkwell:latest
```

Instead of building from source, production **pulls a pre-built image** from Docker Hub. This means:
- The server never needs the source code
- Deploys are fast (just a `docker pull`)
- Every deploy runs the exact same image that was tested in CI

The image tag `:latest` always points to the most recent successful build pushed by GitHub Actions.

---

## Service: nginx

```yaml
nginx:
  expose:
    - "80"
  networks:
    - default
    - proxy_network
```

This is the most important production difference.

**`expose` vs `ports`:**

| | `ports: "80:80"` | `expose: "80"` |
|--|-----------------|----------------|
| Accessible from host browser | Yes | No |
| Accessible from other containers | Yes | Yes |
| Use case | Single project on the server | Multiple projects sharing port 80 |

In production, multiple projects run on the same server. If every project bound to port 80, they'd conflict. Instead, a **shared nginx proxy** container owns port 80 and routes traffic by domain name to the correct project's nginx.

**Networks:**

```yaml
networks:
  - default        # internal network shared with db and web
  - proxy_network  # external network shared with the nginx proxy
```

`blog_nginx` is connected to two networks:
- `default` — the compose-internal network so it can reach `web` (Django)
- `proxy_network` — the shared external network so the nginx proxy can reach it

```
Internet
    │
    ▼
nginx_proxy (port 80/443)   ← owns the public ports
    │  proxy_network
    ▼
blog_nginx (expose 80)      ← this project's nginx
    │  default network
    ▼
blog_django (expose 8000)   ← Django app
    │  default network
    ▼
blog_postgres (expose 5432) ← database
```

---

## Networks Section

```yaml
networks:
  proxy_network:
    external: true
```

`external: true` tells Docker Compose that this network was **not created by this compose file** — it already exists on the server and should just be joined. If it doesn't exist, the `docker compose up` command will fail.

The network is created once on the server:
```bash
docker network create proxy_network
```

---

## The `.env` File on the Server

The production `.env` at `~/inkwell/.env` contains all secrets and is never committed to git:

```
SECRET_KEY=your-real-secret-key
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,YOUR_IP,your-domain.nip.io

DB_ENGINE=django.db.backends.postgresql
DB_NAME=blog_db
DB_USER=bloguser
DB_PASSWORD=strong_password
DB_HOST=db
DB_PORT=5432

DOCKERHUB_USERNAME=yourdockeruser
```

Note `DB_HOST=db` — this is the service name from the compose file, which Docker resolves to the `blog_postgres` container's IP automatically via its internal DNS.

---

## Deployment Flow

The CI/CD pipeline deploys by:

1. Copying `docker-compose.prod.yml` and `nginx/nginx.conf` to `~/inkwell/` on the server
2. Running `docker compose -f docker-compose.prod.yml pull web` — pulls the new image
3. Running `docker compose -f docker-compose.prod.yml up -d --remove-orphans` — recreates changed containers

The database and its volume are never touched during a normal deploy.
