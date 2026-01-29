# ru-corrector — Russian Text Correction Service

Production-ready Russian text correction service with clean layered architecture: FastAPI API layer, correction engine, provider layer, and optional Telegram bot.

## Features

- ✅ **OpenAI Integration**: Advanced text correction and voice transcription with GPT-4 and Whisper
- ✅ **Multiple Correction Modes**: Minimal (min), Business (biz), Academic (acad), Typography-only (typo), Diff view
- ✅ **Voice Message Support**: Transcribe and correct voice messages via Whisper API
- ✅ **Intelligent Fallback**: Works without OpenAI key using local typography rules
- ✅ **Layered Architecture**: Clean separation between API, engine, and providers
- ✅ **Spelling & Grammar**: Powered by OpenAI GPT or LanguageTool (fallback)
- ✅ **Russian Typography**: Proper quotes («»), em-dashes (—), ellipsis (…), spacing
- ✅ **FastAPI**: Modern async API with automatic documentation
- ✅ **Telegram Bot**: Production-ready standalone bot
- ✅ **Docker Ready**: Production-ready containerized deployment
- ✅ **systemd Service**: Easy deployment on Ubuntu/Linux servers
- ✅ **Structured Logging**: Request tracking and error monitoring
- ✅ **Comprehensive Tests**: 82+ unit and integration tests with OpenAI mocking
- ✅ **No Import-Time Failures**: Graceful degradation when services unavailable

## Architecture

```
ru-corrector-bot/
├── src/ru_corrector/
│   ├── api/                    # API layer
│   │   ├── schemas.py          # Request/response models
│   │   └── __init__.py
│   ├── core/                   # Core engine layer
│   │   ├── engine.py           # Main correction pipeline
│   │   ├── models.py           # Internal data models
│   │   └── __init__.py
│   ├── providers/              # Provider layer
│   │   ├── languagetool.py     # LanguageTool adapter
│   │   ├── mock.py             # Mock provider for testing
│   │   └── __init__.py
│   ├── telegram/               # Telegram bot (optional)
│   │   ├── bot.py              # Bot implementation
│   │   └── __init__.py
│   ├── app.py                  # FastAPI application
│   ├── config.py               # Configuration (Pydantic Settings)
│   └── logging_config.py       # Logging setup
├── tests/                      # Test suite
│   ├── test_api.py            # API endpoint tests
│   ├── test_engine.py         # Core engine tests
│   ├── test_core_corrector.py # Legacy tests
│   └── test_typograph.py      # Typography tests
├── pyproject.toml             # Project configuration
├── .env.example               # Environment variables template
└── README.md
```

## Quick Start

### Using Docker Compose (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/vanserokok-arch/ru-corrector-bot.git
cd ru-corrector-bot
```

2. Copy the environment file:
```bash
cp .env.example .env
```

3. Start the services:
```bash
docker-compose up -d
```

4. The API will be available at `http://localhost:8000`

### Local Development

1. **Install Python 3.11+**:
```bash
python --version  # Should be 3.11 or higher
```

2. **Create virtual environment**:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install in editable mode**:
```bash
pip install -e .
```

4. **Set up environment variables**:
```bash
cp .env.example .env
# Edit .env and set LT_URL to public API or local server
```

5. **Run the service**:
```bash
# Using uvicorn with app-dir (preserves import structure)
python -m uvicorn --app-dir src ru_corrector.app:app --host 127.0.0.1 --port 8000 --reload

# Or directly
python -m ru_corrector.app
```

## API Usage

### Interactive Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Health Check

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

### Text Correction

#### Basic correction (legal mode by default):
```bash
curl -X POST http://localhost:8000/correct \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Он сказал \"привет\" и ушел... Это случилось в г. 2025"
  }'
```

**Response:**
```json
{
  "result": "Он сказал «привет» и ушёл… Это случилось в г.\u00a02025",
  "edits": [
    {
      "offset": 10,
      "length": 8,
      "original": "\"привет\"",
      "replacement": "«привет»",
      "message": "Convert to Russian quotes"
    }
  ],
  "stats": {
    "chars_count": 52,
    "edits_count": 3,
    "processing_time_ms": 123.45
  }
}
```

#### Different modes:

**Base mode** (LanguageTool only):
```bash
curl -X POST http://localhost:8000/correct \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Простой текст с ошибками",
    "mode": "base"
  }'
```

**Legal mode** (default - LanguageTool + legal formatting):
```bash
curl -X POST http://localhost:8000/correct \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Договор \"купли-продажи\" от 01.01.2026",
    "mode": "legal"
  }'
```

**Strict mode** (legal + aggressive normalization):
```bash
curl -X POST http://localhost:8000/correct \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Текст   с   пробелами.\n\n\n\nНовая строка",
    "mode": "strict"
  }'
```

#### Without edits list:
```bash
curl -X POST http://localhost:8000/correct \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Простой текст",
    "return_edits": false
  }'
```

### Correction Modes

| Mode | Description | Features |
|------|-------------|----------|
| `base` | Minimal corrections | LanguageTool only (spelling, grammar, punctuation) |
| `legal` | Legal document formatting (default) | Base + Russian quotes, em-dashes, proper spacing, abbreviation handling |
| `strict` | Aggressive normalization | Legal + strict whitespace/punctuation normalization |

## Telegram Bot (Optional)

The Telegram bot runs **separately** from the API and uses the same correction engine.

### Setup

1. Get your bot token from [@BotFather](https://t.me/botfather)

2. Set the token in `.env`:
```bash
TG_BOT_TOKEN=your_bot_token_here
```

3. Run the bot:
```bash
python -m ru_corrector.telegram.bot
```

### Bot Commands

- `/start` or `/help` - Show help
- `/base <text>` - Base mode correction
- `/legal <text>` - Legal mode correction (default)
- `/strict <text>` - Strict mode correction
- Send text without command - Uses default mode (legal)

## Configuration

All configuration is done via environment variables (`.env` file or environment).

See `.env.example` for all options:

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `ru-corrector` | Application name |
| `HOST` | `0.0.0.0` | Host to bind to |
| `PORT` | `8000` | Port to bind to |
| `DEBUG` | `false` | Enable debug mode |
| `MAX_TEXT_LEN` | `15000` | Maximum text length |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LT_URL` | `https://api.languagetool.org` | LanguageTool server URL |
| `ENABLE_YO_REPLACEMENT` | `false` | Enable ё replacement (experimental) |
| `TG_BOT_TOKEN` | - | Telegram bot token (optional) |
| `DEFAULT_MODE` | `legal` | Default correction mode for Telegram bot |

## Testing

### Run All Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_api.py
pytest tests/test_engine.py
```

### Test Coverage

The project has 65+ tests covering:
- API endpoints (health, correct, validation, error handling)
- Core engine (normalization, edit application, deduplication)
- Legal rules (quotes, dashes, spacing, abbreviations)
- Strict rules (whitespace, punctuation)
- Typography (ellipsis, units, NBSP)
- Correction modes (base, legal, strict)
- Deterministic behavior

**All tests are fast** - no external API calls are made (LanguageTool is mocked).

### Smoke Tests

Quick manual tests to verify everything works:

```bash
# 1. Health check
curl http://localhost:8000/health

# 2. Basic correction
curl -X POST http://localhost:8000/correct \
  -H "Content-Type: application/json" \
  -d '{"text": "Простой текст"}'

# 3. Legal mode with quotes
curl -X POST http://localhost:8000/correct \
  -H "Content-Type: application/json" \
  -d '{"text": "Он сказал \"привет\"", "mode": "legal"}'

# 4. Check edits are returned
curl -X POST http://localhost:8000/correct \
  -H "Content-Type: application/json" \
  -d '{"text": "Текст \"в кавычках\"", "return_edits": true}' | jq '.edits'
```

## Development

### Code Quality

The project uses modern Python tooling:

```bash
# Install dev tools
pip install -e ".[dev]"

# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/
```

### Project Structure

- **API Layer** (`src/ru_corrector/api/`): Request/response schemas, API contracts
- **Core Layer** (`src/ru_corrector/core/`): Correction engine, text processing pipeline
- **Provider Layer** (`src/ru_corrector/providers/`): LanguageTool adapter, provider interface
- **Telegram Layer** (`src/ru_corrector/telegram/`): Optional Telegram bot
- **Configuration** (`config.py`): Pydantic Settings-based configuration
- **Logging** (`logging_config.py`): Structured logging with request IDs

### Adding a New Provider

1. Create a new file in `src/ru_corrector/providers/`
2. Implement the `CorrectionProvider` interface:
```python
from ru_corrector.providers import CorrectionProvider
from ru_corrector.core.models import TextEdit

class MyProvider(CorrectionProvider):
    def check(self, text: str) -> list[TextEdit]:
        # Your implementation
        return []
```
3. Use it in the engine:
```python
from ru_corrector.core.engine import CorrectionEngine
from my_provider import MyProvider

engine = CorrectionEngine(provider=MyProvider())
```

## Deployment

### Docker

Build and run:
```bash
docker build -t ru-corrector .
docker run -p 8000:8000 --env-file .env ru-corrector
```

### Docker Compose

Production deployment:
```bash
docker-compose up -d
```

Check logs:
```bash
docker-compose logs -f api
```

Stop services:
```bash
docker-compose down
```

### Production Considerations

1. **LanguageTool Server**: For production, run your own LanguageTool server instead of using the public API
2. **Resource Limits**: Set appropriate memory/CPU limits in docker-compose.yml
3. **Rate Limiting**: Consider adding rate limiting middleware
4. **Monitoring**: Integrate with monitoring tools (Prometheus, Grafana, etc.)
5. **Reverse Proxy**: Use nginx or similar for SSL/TLS termination

## How to Run

### Quick Start (Development)

```bash
# 1. Clone and setup
git clone https://github.com/vanserokok-arch/ru-corrector-bot.git
cd ru-corrector-bot
python -m venv .venv
source .venv/bin/activate

# 2. Install
pip install -e .

# 3. Run API
python -m uvicorn --app-dir src ru_corrector.app:app --host 127.0.0.1 --port 8000 --reload

# 4. In another terminal, run tests
pytest
```

### Production

```bash
# 1. Clone and setup
git clone https://github.com/vanserokok-arch/ru-corrector-bot.git
cd ru-corrector-bot

# 2. Configure
cp .env.example .env
# Edit .env with production settings

# 3. Deploy with Docker
docker-compose up -d

# 4. Verify
curl http://localhost:8000/health
```

## Telegram Bot Deployment

### Quick Start (Bot)

1. **Get a Telegram Bot Token**:
   - Message [@BotFather](https://t.me/BotFather) on Telegram
   - Create a new bot with `/newbot`
   - Copy the token provided

2. **Get OpenAI API Key** (required for voice and advanced corrections):
   - Sign up at [OpenAI](https://platform.openai.com/)
   - Create an API key at https://platform.openai.com/api-keys
   - Copy the key (starts with `sk-`)

3. **Configure Environment**:
```bash
cp .env.example .env
# Edit .env and set:
# BOT_TOKEN=your_telegram_bot_token
# OPENAI_API_KEY=your_openai_api_key
```

4. **Run the Bot**:
```bash
# Install dependencies
pip install -r requirements.txt

# Run bot
python3 app.py
```

### Production Deployment on Ubuntu 22.04

#### 1. Prerequisites

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11+ and dependencies
sudo apt install -y python3.11 python3.11-venv python3-pip ffmpeg git

# Create deployment user (optional but recommended)
sudo useradd -r -s /bin/bash -d /opt/ru-corrector-bot -m botuser
```

#### 2. Install Application

```bash
# Switch to bot user
sudo su - botuser

# Clone repository
cd /opt
sudo git clone https://github.com/vanserokok-arch/ru-corrector-bot.git
sudo chown -R botuser:botuser /opt/ru-corrector-bot
cd /opt/ru-corrector-bot

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

#### 3. Configure Environment

```bash
# Copy and edit configuration
cp .env.example .env
nano .env
```

Set the following variables in `.env`:

```bash
# Required
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz123456789
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx

# Optional (with defaults)
DEFAULT_MODE=min
OPENAI_TEXT_MODEL=gpt-4o-mini
OPENAI_TRANSCRIBE_MODEL=whisper-1
OPENAI_TIMEOUT_SECONDS=60
MAX_TEXT_LEN=15000
```

**Important Environment Variables:**

- `BOT_TOKEN`: Get from [@BotFather](https://t.me/BotFather) (required)
- `OPENAI_API_KEY`: OpenAI API key (required for voice and AI corrections)
- `DEFAULT_MODE`: Default correction mode - `min` (minimal), `biz` (business), `acad` (academic), `typo` (typography only)
- `OPENAI_TEXT_MODEL`: Model for text corrections (default: `gpt-4o-mini` for cost efficiency)
- `OPENAI_TRANSCRIBE_MODEL`: Model for voice transcription (default: `whisper-1`)

**Fallback Mode**: If `OPENAI_API_KEY` is not set:
- Text commands use local typography rules (quotes, dashes, spaces)
- Voice messages return an error asking for API key configuration

#### 4. Set Up systemd Service

```bash
# Exit from botuser
exit

# Copy systemd service file
sudo cp /opt/ru-corrector-bot/ru-corrector-bot.service /etc/systemd/system/

# Create log directory
sudo mkdir -p /var/log/ru-corrector-bot
sudo chown botuser:botuser /var/log/ru-corrector-bot

# Reload systemd
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable ru-corrector-bot
sudo systemctl start ru-corrector-bot

# Check status
sudo systemctl status ru-corrector-bot
```

#### 5. Monitor and Manage

```bash
# View logs
sudo journalctl -u ru-corrector-bot -f

# Or view log files directly
tail -f /var/log/ru-corrector-bot/bot.log
tail -f /var/log/ru-corrector-bot/error.log

# Restart service
sudo systemctl restart ru-corrector-bot

# Stop service
sudo systemctl stop ru-corrector-bot

# Check service status
sudo systemctl status ru-corrector-bot
```

#### 6. Update Application

```bash
# Switch to bot user
sudo su - botuser
cd /opt/ru-corrector-bot

# Pull latest changes
git pull

# Activate virtual environment
source .venv/bin/activate

# Update dependencies if needed
pip install -r requirements.txt

# Exit and restart service
exit
sudo systemctl restart ru-corrector-bot
```

### Testing the Bot

1. **Start a conversation** with your bot on Telegram
2. **Test text correction**:
   - Send: `Он не пришол "сегодня" - а я ждал`
   - Expected: Corrected text with proper spelling and typography
3. **Test modes**:
   - `/min Текст с ошибкой` - minimal corrections
   - `/biz Привет! Можем обсудить?` - business style
   - `/acad Результаты показали что метод работает` - academic style
   - `/typo "Кавычки" и - тире` - typography only
4. **Test voice** (requires OPENAI_API_KEY):
   - Send a voice message
   - Bot will transcribe and correct it

### Troubleshooting

**Bot doesn't start:**
```bash
# Check logs
sudo journalctl -u ru-corrector-bot -n 50

# Check if BOT_TOKEN is set correctly
sudo cat /opt/ru-corrector-bot/.env | grep BOT_TOKEN

# Test bot manually
sudo su - botuser
cd /opt/ru-corrector-bot
source .venv/bin/activate
BOT_TOKEN="your_token" python3 app.py
```

**Voice messages don't work:**
- Verify `OPENAI_API_KEY` is set in `.env`
- Check ffmpeg is installed: `which ffmpeg`
- Check logs for OpenAI errors

**Text correction doesn't work:**
- If OPENAI_API_KEY is not set, bot uses fallback (basic typography)
- Check OpenAI API key is valid
- Check internet connectivity to OpenAI API
- Monitor for rate limit errors in logs

**Service keeps restarting:**
```bash
# View recent errors
sudo journalctl -u ru-corrector-bot -n 100 --no-pager

# Check if port is already in use
# (Bot uses Telegram polling, not HTTP ports)

# Verify Python environment
sudo su - botuser
cd /opt/ru-corrector-bot
source .venv/bin/activate
python3 -c "import aiogram; print('OK')"
```

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BOT_TOKEN` | Yes | - | Telegram bot token from @BotFather |
| `OPENAI_API_KEY` | No* | - | OpenAI API key (*required for voice & AI corrections) |
| `DEFAULT_MODE` | No | `min` | Default correction mode (min/biz/acad/typo) |
| `OPENAI_TEXT_MODEL` | No | `gpt-4o-mini` | OpenAI model for text correction |
| `OPENAI_TRANSCRIBE_MODEL` | No | `whisper-1` | OpenAI model for voice transcription |
| `OPENAI_TIMEOUT_SECONDS` | No | `60` | Timeout for OpenAI API calls |
| `MAX_TEXT_LEN` | No | `15000` | Maximum text length to process |
| `LT_URL` | No | `https://api.languagetool.org` | LanguageTool API URL (fallback) |
| `LT_LANGUAGE` | No | `ru-RU` | Language for LanguageTool (fallback) |

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass (`pytest`)
5. Format code (`black src/ tests/`)
6. Submit a pull request

## Support

For issues and questions:
- GitHub Issues: https://github.com/vanserokok-arch/ru-corrector-bot/issues

---

Made with ❤️ for the Russian language
