# CarSensor Auto Listings Service

Full-stack system for collecting and browsing car listings from carsensor.net, with an admin panel and Telegram bot powered by Gemini AI.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend   │────▶│   Backend   │────▶│   MySQL 8   │
│  Vite+React  │     │   FastAPI   │     │             │
│  nginx:80    │     │  :8000      │     │  :3306      │
└─────────────┘     └──────┬──────┘     └──────▲──────┘
                           │                    │
                    APScheduler          ┌──────┴──────┐
                    (Scraper)            │  Telegram   │
                    BS4 + Playwright     │    Bot      │
                                         │  aiogram    │
                                         └─────────────┘
                                          Gemini LLM
                                          Function Calling
```

**Backend**: FastAPI + SQLAlchemy + Alembic + APScheduler  
**Scraper**: BeautifulSoup (primary) + Playwright (fallback), tenacity retry  
**Frontend**: Vite + React + TypeScript + Tailwind CSS  
**Bot**: aiogram 3.x + Google Gemini function calling, direct DB access  
**Database**: MySQL 8  
**Auth**: JWT (PyJWT)

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Telegram Bot Token (from @BotFather)
- Gemini API Key (from [Google AI Studio](https://aistudio.google.com/app/apikey))

### Run

```bash
# 1. Copy environment file and fill in your keys
cp .env.example .env

# 2. Edit .env — set TELEGRAM_BOT_TOKEN and GEMINI_API_KEY

# 3. Start everything
docker-compose up --build
```

> **📖 Detailed deployment guide**: See [DEPLOY.md](DEPLOY.md) for step-by-step instructions covering Windows, Ubuntu/Debian servers, obtaining API keys, and troubleshooting.

### Access

| Service   | URL                          |
|-----------|------------------------------|
| Frontend  | http://localhost:3000         |
| Backend   | http://localhost:8000         |
| API Docs  | http://localhost:8000/docs    |

### Default Admin Credentials

- **Username**: `admin`
- **Password**: `admin123`

## API Endpoints

| Method | Endpoint       | Auth | Description              |
|--------|----------------|------|--------------------------|
| POST   | `/api/login`   | No   | Login, returns JWT       |
| GET    | `/api/cars`    | JWT  | List cars (with filters) |
| GET    | `/api/health`  | No   | Health check             |

### GET /api/cars Query Parameters

| Parameter   | Type   | Description              |
|-------------|--------|--------------------------|
| brand       | string | Filter by brand (ilike)  |
| model       | string | Filter by model (ilike)  |
| color       | string | Filter by color (ilike)  |
| min_price   | int    | Minimum price (JPY)      |
| max_price   | int    | Maximum price (JPY)      |
| min_year    | int    | Minimum year             |
| max_year    | int    | Maximum year             |
| page        | int    | Page number (default: 1) |
| per_page    | int    | Items per page (max 100) |

## Telegram Bot

Send natural language queries like:
- "Find red BMW under 2 million yen"
- "Найди красную BMW до 2 млн"
- "Show me Toyota cars from 2020"

The bot uses Gemini Function Calling to extract search parameters and queries the database directly.

## Project Structure

```
mm-tt/
├── backend/           # FastAPI + Scraper
│   ├── app/
│   │   ├── main.py           # App + APScheduler
│   │   ├── models.py         # User, Car models
│   │   ├── routers/          # API endpoints
│   │   └── scraper/          # BS4 + Playwright
│   ├── alembic/              # DB migrations
│   └── Dockerfile
├── frontend/          # Vite + React SPA
│   ├── src/
│   │   ├── pages/            # Login, Cars pages
│   │   └── components/       # Shared components
│   ├── nginx.conf
│   └── Dockerfile
├── bot/               # Telegram bot
│   ├── bot/
│   │   ├── main.py           # aiogram entry
│   │   ├── llm.py            # Gemini integration
│   │   └── db.py             # Direct DB queries
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## Environment Variables

See `.env.example` for the full list. Key variables:

| Variable               | Description                        |
|------------------------|------------------------------------|
| MYSQL_ROOT_PASSWORD    | MySQL root password                |
| MYSQL_DATABASE         | Database name                      |
| DATABASE_URL           | SQLAlchemy connection string       |
| JWT_SECRET             | Secret for JWT signing             |
| ADMIN_USERNAME         | Default admin username             |
| ADMIN_PASSWORD         | Default admin password             |
| SCRAPE_INTERVAL_MINUTES| Scraper run interval               |
| TELEGRAM_BOT_TOKEN     | Telegram Bot API token             |
| GEMINI_API_KEY         | Google Gemini API key              |
