# CI/CD Pipeline

This document explains the GitHub Actions pipeline defined in `.github/workflows/deploy.yml`.

---

## Overview

The pipeline runs automatically on every push or pull request to the `main` branch. It is split into **3 sequential jobs** — each must pass before the next one starts.

```
push to main
    │
    ▼
┌─────────────┐
│  1. test    │  lint + pytest (runs on every push AND pull request)
└──────┬──────┘
       │ pass
       ▼
┌─────────────┐
│  2. build   │  build Docker image → push to Docker Hub (main branch only)
└──────┬──────┘
       │ pass
       ▼
┌─────────────┐
│  3. deploy  │  SSH into VPS → pull new image → restart containers
└─────────────┘
```

If any job fails, the subsequent jobs are skipped. A broken test means no deploy ever reaches the server.

---

## Triggers

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
```

- **push to main** — runs all 3 jobs (test → build → deploy)
- **pull request to main** — runs only the `test` job (no build/deploy on PRs)

---

## Global Environment Variable

```yaml
env:
  IMAGE_NAME: ${{ secrets.DOCKERHUB_USERNAME }}/inkwell
```

Sets the Docker Hub image name once at the top level so all jobs can reference it without repeating the value. Resolves to something like `youruser/inkwell`.

---

## Job 1 — Lint & Test

```yaml
test:
  name: Lint & Test
  runs-on: ubuntu-latest
  env:
    SECRET_KEY: "test-secret-key-not-for-production"
    DEBUG: "False"
    ALLOWED_HOSTS: "localhost"
    DB_ENGINE: "django.db.backends.sqlite3"
    DB_NAME: ":memory:"
    DB_USER: ""
    DB_PASSWORD: ""
    DB_HOST: ""
    DB_PORT: ""
```

The `env` block injects environment variables into the runner so Django can start without a real `.env` file. Importantly:
- `DB_ENGINE` is set to SQLite instead of PostgreSQL — no database server needed in CI
- `DB_NAME: ":memory:"` — the database lives entirely in RAM and is destroyed after tests finish
- `SECRET_KEY` is a dummy value — fine for tests, never used in production

### Steps

**1. Checkout code**
```yaml
- uses: actions/checkout@v4
```
Clones the repository into the runner.

**2. Set up Python**
```yaml
- uses: actions/setup-python@v5
  with:
    python-version: "3.12"
    cache: pip
```
Installs Python 3.12 and caches pip packages between runs to speed up future jobs.

**3. Install dependencies**
```yaml
- name: Install dependencies
  run: pip install -r requirements.txt flake8
```
Installs all project dependencies plus `flake8` (linter). flake8 is not in `requirements.txt` because it's a dev-only tool not needed in the Docker image.

**4. Lint**
```yaml
- name: Lint (flake8)
  run: |
    flake8 blog/ user/ blog_project/ \
      --max-line-length=120 \
      --exclude=migrations,settings_test.py \
      --extend-ignore=E501
```
Checks code style. Fails the job if any errors are found.
- `--max-line-length=120` — allows longer lines than the default 79
- `--exclude=migrations` — skips auto-generated migration files
- `--extend-ignore=E501` — ignores line-too-long warnings (already covered by max-line-length)

**5. Run tests**
```yaml
- name: Run tests
  run: pytest --tb=short -v
```
Runs all pytest tests. `pytest.ini` tells pytest to use `blog_project.settings_test` which points the database at SQLite in-memory.
- `--tb=short` — shorter traceback output on failure
- `-v` — verbose, shows each test name as it runs

---

## Job 2 — Build & Push

```yaml
build:
  name: Build & Push
  needs: test
  runs-on: ubuntu-latest
  if: github.ref == 'refs/heads/main' && github.event_name == 'push'
```

- `needs: test` — only starts if the `test` job passed
- `if:` condition — skips this job on pull requests (only runs on direct pushes to `main`)

### Steps

**1. Log in to Docker Hub**
```yaml
- name: Log in to Docker Hub
  uses: docker/login-action@v3
  with:
    username: ${{ secrets.DOCKERHUB_USERNAME }}
    password: ${{ secrets.DOCKERHUB_TOKEN }}
```
Authenticates with Docker Hub using secrets stored in GitHub repository settings. The token must have Read/Write permissions.

**2. Build and push image**
```yaml
- name: Build and push image
  uses: docker/build-push-action@v6
  with:
    context: .
    push: true
    tags: |
      ${{ env.IMAGE_NAME }}:latest
      ${{ env.IMAGE_NAME }}:${{ github.sha }}
```
Builds the Docker image from the `Dockerfile` in the repo root and pushes it to Docker Hub with two tags:
- `:latest` — always points to the most recent build, used by the server to pull
- `:abc1234` (the commit SHA) — immutable tag for that exact commit, useful for rollbacks

---

## Job 3 — Deploy

```yaml
deploy:
  name: Deploy
  needs: build
  runs-on: ubuntu-latest
```

`needs: build` — only starts after the image is successfully pushed to Docker Hub.

### Steps

**1. Prepare directory on server**
```yaml
- name: Prepare deploy directory on server
  uses: appleboy/ssh-action@v1.0.3
  with:
    host: ${{ secrets.SSH_HOST }}
    username: ${{ secrets.SSH_USER }}
    key: ${{ secrets.SSH_PRIVATE_KEY }}
    port: ${{ secrets.SSH_PORT }}
    script: mkdir -p ~/inkwell/nginx
```
SSHes into the VPS and ensures the deploy directory exists. Uses the private SSH key stored as a GitHub secret — the corresponding public key is in `~/.ssh/authorized_keys` on the server.

**2. Copy config files**
```yaml
- name: Copy compose file and nginx config to server
  uses: appleboy/scp-action@v0.1.7
  with:
    host: ${{ secrets.SSH_HOST }}
    username: ${{ secrets.SSH_USER }}
    key: ${{ secrets.SSH_PRIVATE_KEY }}
    port: ${{ secrets.SSH_PORT }}
    source: "docker-compose.prod.yml,nginx/nginx.conf"
    target: "~/inkwell"
    strip_components: 0
```
Copies `docker-compose.prod.yml` and `nginx/nginx.conf` from the repo to `~/inkwell/` on the server via SCP. The server never clones the git repo — only these two config files are transferred.

**3. Pull image and restart**
```yaml
- name: Deploy on server
  uses: appleboy/ssh-action@v1.0.3
  with:
    script: |
      set -e
      cd ~/inkwell

      echo "Pulling latest image..."
      docker compose -f docker-compose.prod.yml pull web

      echo "Restarting services..."
      docker compose -f docker-compose.prod.yml up -d --remove-orphans

      echo "Cleaning up old images..."
      docker image prune -f

      echo "Deploy complete."
```

- `set -e` — exits immediately if any command fails, preventing a broken deploy from continuing silently
- `pull web` — pulls only the `web` service image (the Django app) from Docker Hub; `db` and `nginx` images don't change on every deploy
- `up -d --remove-orphans` — recreates containers that have changed, leaves others running; `--remove-orphans` removes containers for services no longer in the compose file
- `image prune -f` — deletes old untagged images to free up disk space

---

## GitHub Secrets Required

These must be set in **GitHub → Settings → Secrets and variables → Actions**:

| Secret | Value |
|--------|-------|
| `DOCKERHUB_USERNAME` | Your Docker Hub username |
| `DOCKERHUB_TOKEN` | Docker Hub access token (Read/Write/Delete) |
| `SSH_HOST` | VPS IP address |
| `SSH_USER` | SSH username on the VPS (e.g. `deploy`) |
| `SSH_PRIVATE_KEY` | Contents of your `~/.ssh/id_rsa` private key |
| `SSH_PORT` | SSH port (usually `22`) |

---

## Full Pipeline on a Successful Push

```
1. Developer pushes code to main
2. GitHub Actions triggers the workflow
3. test job:
   - Installs dependencies
   - Runs flake8 linter
   - Runs pytest against SQLite in-memory DB
4. build job (only if test passed):
   - Builds Docker image
   - Pushes youruser/inkwell:latest and youruser/inkwell:<sha> to Docker Hub
5. deploy job (only if build passed):
   - SSHes into VPS
   - Creates deploy directory
   - Copies docker-compose.prod.yml and nginx.conf to server
   - Pulls new image from Docker Hub
   - Restarts containers with zero manual intervention
```
