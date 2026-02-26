# Deployment Guide

Complete step-by-step instructions to run the CarSensor Auto Listings Service on **Windows (local)** and a **fresh Ubuntu/Debian server**.

---

## 1. Obtain API Keys

Before deploying, you need two keys: a **Telegram Bot Token** and a **Gemini API Key**.

### 1.1 Telegram Bot Token

1. Open Telegram and search for **@BotFather**
2. Start a chat and send `/newbot`
3. Follow the prompts:
   - Enter a **display name** for your bot (e.g. `CarSensor Bot`)
   - Enter a **username** ending in `bot` (e.g. `carsensor_listings_bot`)
4. BotFather will reply with your **bot token** — a string like `7123456789:AAH...`. Copy it.
5. You can also send `/setdescription` to BotFather to add a description to your bot.

### 1.2 Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Select an existing Google Cloud project or create a new one
5. Copy the generated API key (starts with `AIza...`)

> **Note**: The free tier of Gemini API is sufficient for this project.

---

## 2. Deploy on Windows (Local)

**Prerequisites**: Docker Desktop installed and running.

### Step-by-step

```powershell
# 1. Open a terminal (PowerShell or CMD) and navigate to the project
cd F:\projects\fl\mm-tt

# 2. Copy the example environment file
copy .env.example .env

# 3. Open .env in any text editor and fill in:
#    TELEGRAM_BOT_TOKEN=<your token from step 1.1>
#    GEMINI_API_KEY=<your key from step 1.2>
notepad .env

# 4. Build and start all services
docker-compose up --build
```

### What happens

1. **MySQL 8** starts and waits for healthcheck
2. **Backend** (FastAPI) waits for DB, runs Alembic migrations, seeds admin user, starts scraper on schedule
3. **Frontend** (Vite + React) builds and is served via Nginx
4. **Bot** (aiogram + Gemini) connects to Telegram and starts polling

### Access

| Service  | URL                        |
|----------|----------------------------|
| Frontend | http://localhost:3000       |
| API      | http://localhost:8000       |
| API Docs | http://localhost:8000/docs  |

**Admin login**: `admin` / `admin123`

### Troubleshooting (Windows)

- **Port 3306 already in use**: You have a local MySQL running. Stop it or change the port mapping in `docker-compose.yml` (e.g. `"3307:3306"`)
- **Port 3000 or 8000 in use**: Another app is using the port. Stop it or change the mapping.
- **Docker Desktop not running**: Make sure Docker Desktop is started (check system tray).
- **"docker-compose" not found**: Use `docker compose` (with a space) instead — newer Docker Desktop versions use the plugin syntax.

---

## 3. Deploy on Server (Ubuntu/Debian)

**Prerequisites**: SSH access to a fresh Ubuntu 22.04/24.04 or Debian 12 server.

### 3.1 Install Docker Engine

```bash
# SSH into your server
ssh root@<your-server-ip>

# Update packages
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine + Compose plugin
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# (Optional) Allow running docker without sudo
sudo usermod -aG docker $USER
# Log out and back in for group change to take effect
exit
ssh root@<your-server-ip>

# Verify installation
docker --version
docker compose version
```

> **Debian users**: Replace `ubuntu` with `debian` in the repository URL above.

### 3.2 Get the Project

**Option A — Git clone** (if repo is public):
```bash
sudo apt-get install -y git
git clone https://github.com/<your-username>/mm-tt.git
cd mm-tt
```

**Option B — Upload from local machine** (from your Windows terminal):
```powershell
# From your local machine
scp -r F:\projects\fl\mm-tt root@<your-server-ip>:/root/mm-tt
```
Then on the server:
```bash
cd /root/mm-tt
```

### 3.3 Configure and Start

```bash
# 1. Create .env from example
cp .env.example .env

# 2. Edit .env — fill in TELEGRAM_BOT_TOKEN and GEMINI_API_KEY
nano .env

# 3. Build and start all services in detached mode
docker compose up --build -d

# 4. Watch the logs to confirm everything starts
docker compose logs -f
# Press Ctrl+C to stop following logs (services keep running)
```

### 3.4 Open Firewall Ports

```bash
# If UFW is active
sudo ufw allow 3000/tcp   # Frontend
sudo ufw allow 8000/tcp   # Backend API
sudo ufw reload

# If using iptables directly
sudo iptables -A INPUT -p tcp --dport 3000 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT
```

### Access

| Service  | URL                              |
|----------|----------------------------------|
| Frontend | http://\<server-ip\>:3000        |
| API      | http://\<server-ip\>:8000        |
| API Docs | http://\<server-ip\>:8000/docs   |

**Admin login**: `admin` / `admin123`

> **Telegram bot**: Works without a domain — it uses polling, not webhooks. As long as the container has internet access, the bot will respond in Telegram.

---

## 4. Verification Checklist

Run through this after deployment to confirm everything works:

```bash
# Check all 4 services are running
docker compose ps
```

Expected output: 4 services (`db`, `backend`, `frontend`, `bot`) with status `Up` or `running`.

| # | Check | How |
|---|-------|-----|
| 1 | **All services running** | `docker compose ps` — 4 services with `Up` status |
| 2 | **Health endpoint** | `curl http://localhost:8000/api/health` → `{"status":"ok"}` |
| 3 | **Frontend loads** | Open `http://localhost:3000/login` in browser |
| 4 | **Admin login works** | Login with `admin` / `admin123` → redirects to cars table |
| 5 | **API docs load** | Open `http://localhost:8000/docs` in browser |
| 6 | **Scraper runs** | `docker compose logs backend` — look for `[scraper]` log lines |
| 7 | **Telegram bot responds** | Open your bot in Telegram, send "Find Toyota" |
| 8 | **Gemini integration** | Bot should reply with filtered car results (or "No cars found") |

> **Note**: On the server, replace `localhost` with your server IP.

---

## 5. Common Commands

```bash
# Start all services (detached)
docker compose up --build -d

# Stop all services
docker compose down

# View logs (all services)
docker compose logs -f

# View logs for a specific service
docker compose logs -f backend
docker compose logs -f bot
docker compose logs -f frontend

# Rebuild and restart a single service
docker compose up --build -d backend

# Reset everything (including database data)
docker compose down -v

# Check running services
docker compose ps

# Enter a running container
docker compose exec backend bash
docker compose exec bot bash

# Run a one-off command in backend container
docker compose exec backend python -c "from app.database import SessionLocal; print('DB OK')"
```

---

## 6. Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MYSQL_ROOT_PASSWORD` | Yes | `rootpassword` | MySQL root password |
| `MYSQL_DATABASE` | Yes | `carsensor` | Database name |
| `MYSQL_USER` | Yes | `app` | Database user |
| `MYSQL_PASSWORD` | Yes | `apppassword` | Database user password |
| `DATABASE_URL` | Yes | `mysql+pymysql://app:apppassword@db:3306/carsensor` | SQLAlchemy connection string |
| `JWT_SECRET` | Yes | `change-me-to-random-string` | **Change this** in production |
| `ADMIN_USERNAME` | Yes | `admin` | Default admin username |
| `ADMIN_PASSWORD` | Yes | `admin123` | Default admin password |
| `SCRAPE_INTERVAL_MINUTES` | Yes | `60` | How often the scraper runs (minutes) |
| `BACKEND_API_BASE_URL` | Yes | `http://backend:8000` | Internal backend URL used by bot for on-demand scrape trigger/status |
| `BOT_FRESH_WAIT_SECONDS` | Yes | `180` | How long bot waits for live scrape completion before showing cached results |
| `BOT_STATUS_POLL_INTERVAL_SECONDS` | Yes | `5` | How often bot polls backend scrape job status during waiting window |
| `TELEGRAM_BOT_TOKEN` | **Yes** | _(empty)_ | From @BotFather (see section 1.1) |
| `GEMINI_API_KEY` | **Yes** | _(empty)_ | From Google AI Studio (see section 1.2) |

> **Security**: For the server, change `MYSQL_ROOT_PASSWORD`, `MYSQL_PASSWORD`, `JWT_SECRET`, and `ADMIN_PASSWORD` to strong random values.
