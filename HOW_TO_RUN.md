# How to Run - ru-corrector

This guide provides step-by-step instructions for running the ru-corrector service in different scenarios.

## Prerequisites

- Python 3.11 or higher
- pip (Python package installer)
- Git

## Installation Methods

### Method 1: Editable Install (Recommended for Development)

This is the primary method as specified in requirements.

```bash
# 1. Clone the repository
git clone https://github.com/vanserokok-arch/ru-corrector-bot.git
cd ru-corrector-bot

# 2. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install in editable mode
pip install -e .

# 4. Copy environment file and configure
cp .env.example .env
# Edit .env if needed (use default values for testing)

# 5. Verify installation
python -c "import ru_corrector; print('Installation successful!')"
```

### Method 2: Docker Compose (Production)

```bash
# 1. Clone and configure
git clone https://github.com/vanserokok-arch/ru-corrector-bot.git
cd ru-corrector-bot
cp .env.example .env

# 2. Start services
docker-compose up -d

# 3. Check status
docker-compose ps

# 4. View logs
docker-compose logs -f api
```

## Running the API Server

### Using uvicorn (Required Command)

The service **must** support this exact command:

```bash
python -m uvicorn --app-dir src ru_corrector.app:app --host 127.0.0.1 --port 8000 --reload
```

**Why `--app-dir src`?**
- Keeps the import structure clean: `from ru_corrector.app import app`
- Allows `pip install -e .` to work correctly
- Maintains package structure without path hacks

### Alternative Methods

```bash
# 1. Direct module execution
cd src
python -m ru_corrector.app

# 2. Production mode (no reload)
python -m uvicorn --app-dir src ru_corrector.app:app --host 0.0.0.0 --port 8000

# 3. Custom host/port
python -m uvicorn --app-dir src ru_corrector.app:app --host 0.0.0.0 --port 8080 --reload
```

## Running Tests

### Run All Tests

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_api.py
pytest tests/test_engine.py
```

### Test Results

Expected output:
```
======================== test session starts =========================
platform linux -- Python 3.12.3, pytest-9.0.2, pluggy-1.6.0
rootdir: /path/to/ru-corrector-bot
configfile: pyproject.toml
plugins: asyncio-1.3.0, anyio-4.12.1
collected 65 items

tests/test_api.py ................                           [ 24%]
tests/test_core_corrector.py .............                   [ 44%]
tests/test_engine.py ..........................               [ 84%]
tests/test_typograph.py ..........                           [100%]

======================== 65 passed in 0.52s ==========================
```

## Smoke Tests

### 1. Health Check

```bash
curl http://localhost:8000/health
```

**Expected output:**
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

### 2. Basic Correction (Legal Mode - Default)

```bash
curl -X POST http://localhost:8000/correct \
  -H "Content-Type: application/json" \
  -d '{"text": "Он сказал \"привет\""}'
```

**Expected output:**
```json
{
  "result": "Он сказал «привет»",
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
    "chars_count": 20,
    "edits_count": 1,
    "processing_time_ms": 45.23
  }
}
```

### 3. Base Mode (LanguageTool Only)

```bash
curl -X POST http://localhost:8000/correct \
  -H "Content-Type: application/json" \
  -d '{"text": "Простой текст", "mode": "base"}'
```

### 4. Strict Mode

```bash
curl -X POST http://localhost:8000/correct \
  -H "Content-Type: application/json" \
  -d '{"text": "Текст   с   пробелами", "mode": "strict"}'
```

### 5. Without Edits

```bash
curl -X POST http://localhost:8000/correct \
  -H "Content-Type: application/json" \
  -d '{"text": "Тест", "return_edits": false}'
```

### 6. Request ID Header

```bash
curl -v -X POST http://localhost:8000/correct \
  -H "Content-Type: application/json" \
  -d '{"text": "Тест"}' 2>&1 | grep "X-Request-ID"
```

**Expected output:**
```
< X-Request-ID: abc123de-f456-7890-gh12-ijklmnop3456
```

## Running the Telegram Bot (Optional)

The Telegram bot is **optional** and runs **separately** from the API.

### Setup

```bash
# 1. Get your bot token from @BotFather
# 2. Add to .env file
echo "TG_BOT_TOKEN=your_bot_token_here" >> .env

# 3. Run the bot
python -m ru_corrector.telegram.bot
```

**Expected output:**
```
2026-01-28 10:00:00,000 | INFO | ru_corrector.telegram.bot | Starting Telegram bot...
```

## Demo Script

To see the engine in action without needing an external LanguageTool server:

```bash
python demo.py
```

This demonstrates:
- Base, legal, and strict modes
- Quote conversion
- Dash conversion  
- Typography rules
- Abbreviation preservation
- Deterministic behavior

## Troubleshooting

### Import Errors

If you get import errors:
```bash
# Ensure you installed in editable mode
pip install -e .

# Or check your Python path
python -c "import sys; print('\n'.join(sys.path))"
```

### Port Already in Use

If port 8000 is in use:
```bash
# Find the process
lsof -i :8000

# Use a different port
python -m uvicorn --app-dir src ru_corrector.app:app --host 127.0.0.1 --port 8080 --reload
```

### LanguageTool Connection Error

In production, you need a LanguageTool server. Options:

1. **Use public API** (default in .env.example):
   ```bash
   LT_URL=https://api.languagetool.org
   ```

2. **Run local server**:
   ```bash
   # Start LanguageTool server (Docker)
   docker run -p 8010:8010 erikvl87/languagetool

   # Update .env
   LT_URL=http://localhost:8010
   ```

3. **For testing only** (tests use mock):
   ```bash
   pytest  # Tests don't need real LanguageTool
   ```

## Verification Checklist

After installation, verify:

- [ ] `pip install -e .` completed successfully
- [ ] `pytest` runs and all 65 tests pass
- [ ] `python -m uvicorn --app-dir src ru_corrector.app:app --host 127.0.0.1 --port 8000` starts server
- [ ] `curl http://localhost:8000/health` returns `{"status": "ok"}`
- [ ] API documentation available at http://localhost:8000/docs
- [ ] `python demo.py` runs successfully

## Next Steps

1. **Explore the API**: Visit http://localhost:8000/docs for interactive documentation
2. **Run Tests**: Execute `pytest -v` to see all tests
3. **Try the Demo**: Run `python demo.py` to see the engine in action
4. **Set Up Telegram Bot**: (Optional) Configure and run the Telegram bot
5. **Deploy**: Use Docker Compose for production deployment

## Support

If you encounter issues:
1. Check the logs: `docker-compose logs api` (if using Docker)
2. Verify environment variables: `cat .env`
3. Check Python version: `python --version` (must be 3.11+)
4. Review the README.md for detailed documentation
5. Open an issue on GitHub
