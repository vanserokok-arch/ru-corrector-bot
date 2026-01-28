# ru-corrector — Russian Text Correction Service

Production-ready Russian text correction service with clean layered architecture: FastAPI API layer, correction engine, provider layer, and optional Telegram bot.

## Features

- ✅ **Layered Architecture**: Clean separation between API, engine, and providers
- ✅ **Spelling & Grammar**: Powered by LanguageTool
- ✅ **Legal Document Formatting**: Russian quotes («»), em-dashes (—), proper spacing
- ✅ **Typography**: Russian typography rules (quotes, dashes, spaces, ellipsis)
- ✅ **Multiple Modes**: Base, Legal, Strict correction modes
- ✅ **FastAPI**: Modern async API with automatic documentation
- ✅ **Telegram Bot**: Optional standalone bot (run separately)
- ✅ **Docker Ready**: Production-ready containerized deployment
- ✅ **Structured Logging**: Request tracking and performance monitoring
- ✅ **Health Checks**: Built-in health monitoring
- ✅ **Tested**: Comprehensive unit and integration tests (65 tests)

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
