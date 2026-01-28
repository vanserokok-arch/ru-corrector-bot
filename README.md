# ru-corrector — Russian Text Correction Service

Production-ready Russian text correction service using LanguageTool and custom typography rules.

## Features

- ✅ **Spelling & Grammar**: Powered by LanguageTool
- ✅ **Typography**: Russian typography rules (quotes, dashes, spaces, ellipsis)
- ✅ **FastAPI**: Modern async API with automatic documentation
- ✅ **Multiple Modes**: Minimal, Business, Academic correction styles
- ✅ **Diff View**: HTML diff showing changes
- ✅ **Docker Ready**: Production-ready containerized deployment
- ✅ **Structured Logging**: Request tracking and performance monitoring
- ✅ **Health Checks**: Built-in health monitoring
- ✅ **Tested**: Comprehensive unit and integration tests

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

1. Install Python 3.11+:
```bash
python --version  # Should be 3.11 or higher
```

2. Create virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and set LT_URL to public API or local server
```

5. Run the service:
```bash
python -m uvicorn ru_corrector.app:app --reload --host 0.0.0.0 --port 8000
```

Or using the module directly:
```bash
cd src
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

Response:
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

### Text Correction

**Basic correction:**
```bash
curl -X POST http://localhost:8000/correct \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Он сказал \"привет\" и ушел... Это случилось в г. 2025"
  }'
```

**With diff view:**
```bash
curl -X POST http://localhost:8000/correct \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Простой текст с ошибками...",
    "show_diff": true
  }'
```

**Different modes:**
```bash
curl -X POST http://localhost:8000/correct \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Деловой текст для проверки",
    "mode": "biz"
  }'
```

Available modes:
- `min` - Minimal corrections (spelling, grammar, punctuation)
- `biz` - Business style (gentle corrections)
- `acad` - Academic style (gentle corrections)

### Response Format

```json
{
  "original": "Он сказал \"привет\" и ушел...",
  "corrected": "Он сказал «привет» и ушёл…",
  "diff": "<html diff or null>",
  "stats": {
    "length": 28,
    "changes": 5,
    "processing_time_ms": 234.56
  }
}
```

## Configuration

All configuration is done via environment variables. See `.env.example` for all options:

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `ru-corrector` | Application name |
| `HOST` | `0.0.0.0` | Host to bind to |
| `PORT` | `8000` | Port to bind to |
| `DEBUG` | `false` | Enable debug mode |
| `MAX_TEXT_LEN` | `15000` | Maximum text length |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LT_URL` | `https://api.languagetool.org` | LanguageTool server URL |

## Testing

Run the test suite:

```bash
# Install dev dependencies
pip install pytest pytest-asyncio httpx

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_api.py

# Run with coverage
pytest --cov=src/ru_corrector
```

## Code Quality

The project uses modern Python tooling:

```bash
# Install dev tools
pip install ruff black mypy

# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/
```

## Project Structure

```
ru-corrector-bot/
├── src/
│   └── ru_corrector/
│       ├── __init__.py
│       ├── app.py              # FastAPI application
│       ├── config.py           # Configuration from ENV
│       ├── logging_config.py   # Structured logging
│       └── services/
│           ├── __init__.py
│           ├── core_corrector.py   # Main correction logic
│           ├── typograph_ru.py     # Typography rules
│           └── diff_view.py        # HTML diff generator
├── tests/
│   ├── __init__.py
│   ├── test_api.py
│   ├── test_core_corrector.py
│   └── test_typograph.py
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
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

## Telegram Bot (Legacy)

The original Telegram bot functionality is preserved but separated. To run the bot:

1. Set `BOT_TOKEN` in your `.env` file
2. Run the legacy bot script (if maintained separately)

The API is designed to be easily integrated with any Telegram bot or other clients.

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Support

For issues and questions:
- GitHub Issues: https://github.com/vanserokok-arch/ru-corrector-bot/issues

---

Made with ❤️ for the Russian language
