# SSL Certificate Setup with Let's Encrypt

This guide documents how to obtain and configure a free SSL certificate using Let's Encrypt and Certbot for a Dockerized application behind an Nginx reverse proxy.

---

## Overview

**Let's Encrypt** is a free, automated Certificate Authority (CA). It issues certificates valid for 90 days and supports automatic renewal.

**Certbot** is the official CLI tool that communicates with Let's Encrypt to obtain and renew certificates.

The flow looks like this:

```
Browser ──HTTPS──► Nginx Proxy (port 443) ──HTTP──► App Container
                        │
                   /etc/letsencrypt/
                   (cert files mounted)
```

---

## Prerequisites

- A VPS with a public IP address
- A domain name pointing to that IP (e.g. `inkwell.YOUR_IP_ADDR.nip.io`)
- Port 80 and 443 open on the firewall
- Docker and Docker Compose installed

---

## Step 1 — Configure UFW Firewall

Before anything else, make sure the required ports are open:

```bash
sudo ufw allow 22/tcp    # SSH (never block this)
sudo ufw allow 80/tcp    # HTTP (needed for cert challenge + redirect)
sudo ufw allow 443/tcp   # HTTPS

sudo ufw --force enable
sudo ufw status
```

Expected output:
```
Status: active

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW       Anywhere
80/tcp                     ALLOW       Anywhere
443/tcp                    ALLOW       Anywhere
```

---

## Step 2 — Install Certbot

```bash
sudo apt-get update && sudo apt-get install -y certbot
```

---

## Step 3 — Obtain the Certificate

Certbot supports several "challenge" methods to prove you own the domain. We use **standalone mode**, which spins up a temporary HTTP server on port 80 to answer the challenge.

Since our Nginx proxy already owns port 80, we must stop it first:

```bash
cd ~/nginx-proxy && docker compose down
```

Now run Certbot:

```bash
sudo certbot certonly --standalone \
  -d your-domain.nip.io \
  --non-interactive \
  --agree-tos \
  -m your@email.com
```

Flag breakdown:
| Flag | Meaning |
|------|---------|
| `certonly` | Get the cert only, don't modify any web server config |
| `--standalone` | Certbot runs its own temporary HTTP server on port 80 |
| `-d` | Domain name to issue the cert for |
| `--non-interactive` | Don't prompt for input |
| `--agree-tos` | Auto-accept Let's Encrypt Terms of Service |
| `-m` | Email for expiry notifications |

On success, certificates are saved to:
```
/etc/letsencrypt/live/your-domain.nip.io/
├── fullchain.pem   ← certificate + intermediate chain (use this in nginx)
├── privkey.pem     ← private key
├── cert.pem        ← certificate only
└── chain.pem       ← intermediate chain only
```

---

## Step 4 — Mount Certs into the Nginx Proxy Container

Update `~/nginx-proxy/docker-compose.yml` to expose port 443 and mount the Let's Encrypt directory:

```yaml
services:
  nginx_proxy:
    image: nginx:1.27-alpine
    container_name: nginx_proxy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./conf.d:/etc/nginx/conf.d:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro   # mount certs as read-only
    networks:
      - proxy_network

networks:
  proxy_network:
    external: true
```

The `/etc/letsencrypt` directory is mounted read-only — the container can read the certs but cannot modify them.

---

## Step 5 — Configure Nginx for HTTPS

Update the vhost config for your app (`~/nginx-proxy/conf.d/inkwell.conf`):

```nginx
# Redirect all HTTP traffic to HTTPS
server {
    listen 80;
    server_name your-domain.nip.io;
    return 301 https://$host$request_uri;
}

# HTTPS server block
server {
    listen 443 ssl;
    server_name your-domain.nip.io;

    ssl_certificate     /etc/letsencrypt/live/your-domain.nip.io/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.nip.io/privkey.pem;

    location / {
        proxy_pass         http://blog_nginx:80;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }
}
```

Two server blocks explained:
- **Port 80 block** — catches all plain HTTP requests and issues a `301 Moved Permanently` redirect to the HTTPS version
- **Port 443 block** — serves HTTPS using the Let's Encrypt cert and proxies traffic to the app

The `X-Forwarded-Proto $scheme` header tells the upstream app that the original request was HTTPS (important for Django, Rails, etc. to generate correct URLs).

---

## Step 6 — Restart the Proxy

```bash
cd ~/nginx-proxy && docker compose up -d
```

Verify it's running:

```bash
docker ps --filter name=nginx_proxy
```

Test HTTPS:
```bash
curl -I https://your-domain.nip.io
# Should return: HTTP/2 200
```

Test HTTP redirect:
```bash
curl -I http://your-domain.nip.io
# Should return: HTTP/1.1 301 Moved Permanently
#                Location: https://your-domain.nip.io/
```

---

## Certificate Renewal

Let's Encrypt certificates expire after **90 days**. Renew with:

```bash
# Test renewal (dry run, no actual changes)
sudo certbot renew --dry-run

# Actual renewal
sudo certbot renew
```

After renewal, restart the proxy so it picks up the new cert files:
```bash
cd ~/nginx-proxy && docker compose restart
```

### Automate renewal with a cron job

```bash
sudo crontab -e
```

Add this line to run renewal check every Monday at 3am:
```
0 3 * * 1 certbot renew --quiet && cd /home/deploy/nginx-proxy && docker compose restart
```

---

## Troubleshooting

**Port 80 already in use when running certbot**
```bash
# Find what's using port 80
sudo ss -tlnp | grep :80

# Stop the nginx proxy temporarily
cd ~/nginx-proxy && docker compose down
```

**Certificate not trusted / browser warning**
- Make sure you're using `fullchain.pem` not `cert.pem` in nginx — the chain file includes the intermediate certificate that browsers need

**Django returning 400 Bad Request after HTTPS**
- Add the domain to `ALLOWED_HOSTS` in your `.env` file:
```
ALLOWED_HOSTS=localhost,127.0.0.1,your-ip,your-domain.nip.io
```
- Restart the Django container: `docker compose restart web`
