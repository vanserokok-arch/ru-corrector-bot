# Production Deployment Guide: ru-corrector-bot on Ubuntu 22.04

This guide provides step-by-step instructions for deploying the ru-corrector-bot as a production systemd service on Ubuntu 22.04.

## Prerequisites

- Ubuntu 22.04 LTS server with sudo access
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)
- OpenAI API Key from [OpenAI Platform](https://platform.openai.com/) (optional but recommended)
- Internet connectivity

## Quick Deployment Commands

```bash
# 1. System setup
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.11 python3.11-venv python3-pip ffmpeg git

# 2. Create deployment user
sudo useradd -r -s /bin/bash -d /opt/ru-corrector-bot -m botuser

# 3. Clone repository
cd /opt
sudo git clone https://github.com/vanserokok-arch/ru-corrector-bot.git
sudo chown -R botuser:botuser /opt/ru-corrector-bot

# 4. Install as botuser
sudo -u botuser bash << 'EOF'
cd /opt/ru-corrector-bot
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
EOF

# 5. Configure environment
sudo -u botuser bash << 'EOF'
cd /opt/ru-corrector-bot
cat > .env << 'ENVEOF'
# Required
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN_HERE
OPENAI_API_KEY=YOUR_OPENAI_API_KEY_HERE

# Optional (defaults shown)
DEFAULT_MODE=min
OPENAI_TEXT_MODEL=gpt-4o-mini
OPENAI_TRANSCRIBE_MODEL=whisper-1
OPENAI_TIMEOUT_SECONDS=60
MAX_TEXT_LEN=15000
ENVEOF
EOF

# 6. Edit .env with your actual tokens
sudo -u botuser nano /opt/ru-corrector-bot/.env

# 7. Install systemd service
sudo cp /opt/ru-corrector-bot/ru-corrector-bot.service /etc/systemd/system/
sudo mkdir -p /var/log/ru-corrector-bot
sudo chown botuser:botuser /var/log/ru-corrector-bot

# 8. Start service
sudo systemctl daemon-reload
sudo systemctl enable ru-corrector-bot
sudo systemctl start ru-corrector-bot

# 9. Check status
sudo systemctl status ru-corrector-bot
```

## Environment Variables

Create `/opt/ru-corrector-bot/.env` with these variables:

```bash
# ============================================
# REQUIRED
# ============================================

# Telegram bot token from @BotFather
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz123456789

# OpenAI API key (optional but recommended)
# Without this key:
# - Text commands use fallback (local typography only)
# - Voice messages return an error
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx

# ============================================
# OPTIONAL (with defaults)
# ============================================

# Default correction mode: min, biz, acad, typo
DEFAULT_MODE=min

# OpenAI model for text correction
# Recommended: gpt-4o-mini (cost-effective)
# Alternative: gpt-4-turbo, gpt-3.5-turbo
OPENAI_TEXT_MODEL=gpt-4o-mini

# OpenAI model for voice transcription
OPENAI_TRANSCRIBE_MODEL=whisper-1

# API timeout in seconds
OPENAI_TIMEOUT_SECONDS=60

# Maximum text length to process
MAX_TEXT_LEN=15000
```

## Service Management

```bash
# Start service
sudo systemctl start ru-corrector-bot

# Stop service
sudo systemctl stop ru-corrector-bot

# Restart service
sudo systemctl restart ru-corrector-bot

# Check status
sudo systemctl status ru-corrector-bot

# View logs (live)
sudo journalctl -u ru-corrector-bot -f

# View logs (last 100 lines)
sudo journalctl -u ru-corrector-bot -n 100

# View log files
tail -f /var/log/ru-corrector-bot/bot.log
tail -f /var/log/ru-corrector-bot/error.log
```

## Update Procedure

```bash
# 1. Stop service
sudo systemctl stop ru-corrector-bot

# 2. Switch to bot user and update
sudo -u botuser bash << 'EOF'
cd /opt/ru-corrector-bot
git pull
source .venv/bin/activate
pip install -r requirements.txt
EOF

# 3. Restart service
sudo systemctl start ru-corrector-bot

# 4. Check status
sudo systemctl status ru-corrector-bot
```

## Testing the Bot

1. **Start conversation** with your bot on Telegram (search for bot username)

2. **Test basic text correction**:
   ```
   Он не пришол "сегодня" - а я ждал
   ```
   Expected: Corrected with proper spelling and typography

3. **Test commands**:
   ```
   /min Текст с ошибкой
   /biz Привет! Можем обсудить?
   /acad Результаты показали что метод работает
   /typo "Кавычки" и - тире
   ```

4. **Test voice** (requires OPENAI_API_KEY):
   - Send a voice message
   - Bot transcribes and corrects it

## Troubleshooting

### Bot doesn't start

```bash
# Check logs
sudo journalctl -u ru-corrector-bot -n 50

# Check BOT_TOKEN
sudo -u botuser cat /opt/ru-corrector-bot/.env | grep BOT_TOKEN

# Test manual start
sudo -u botuser bash << 'EOF'
cd /opt/ru-corrector-bot
source .venv/bin/activate
python3 app.py
EOF
```

### Voice messages don't work

```bash
# 1. Check OPENAI_API_KEY is set
sudo -u botuser cat /opt/ru-corrector-bot/.env | grep OPENAI_API_KEY

# 2. Check ffmpeg is installed
which ffmpeg

# 3. Check logs for OpenAI errors
sudo journalctl -u ru-corrector-bot | grep -i openai
```

### Text correction doesn't work

**Without OPENAI_API_KEY**: Bot uses fallback mode (typography only)
- This is expected behavior
- To enable AI corrections, add OPENAI_API_KEY

**With OPENAI_API_KEY**: Check logs for errors
```bash
sudo journalctl -u ru-corrector-bot | grep -i error
```

### Service keeps restarting

```bash
# View crash logs
sudo journalctl -u ru-corrector-bot -n 200 --no-pager

# Common issues:
# - Invalid BOT_TOKEN
# - Python import errors
# - Permission issues

# Check file permissions
ls -la /opt/ru-corrector-bot/
ls -la /var/log/ru-corrector-bot/
```

## Security Checklist

- ✅ `.env` file permissions: `chmod 600 /opt/ru-corrector-bot/.env`
- ✅ Bot user has minimal permissions (no sudo)
- ✅ Logs don't contain API keys (verified in code)
- ✅ systemd service runs with `NoNewPrivileges=true`
- ✅ Service uses `PrivateTmp=true`

## Performance Notes

- **Memory**: ~150-300 MB (depends on traffic)
- **CPU**: Minimal (polling-based)
- **Network**: Outbound to Telegram and OpenAI APIs
- **Storage**: Minimal (no persistent data, only logs)

## Monitoring

```bash
# Check service health
sudo systemctl is-active ru-corrector-bot

# Monitor resource usage
sudo systemctl status ru-corrector-bot

# Check bot responsiveness
# Send a message to the bot on Telegram
```

## Backup Recommendations

Only need to backup:
- `/opt/ru-corrector-bot/.env` - Configuration with API keys

**Automated backup script**:
```bash
#!/bin/bash
# /opt/backup-bot-env.sh
sudo cp /opt/ru-corrector-bot/.env /opt/backups/ru-corrector-bot.env.$(date +%Y%m%d)
sudo chmod 600 /opt/backups/ru-corrector-bot.env.*
```

## Production Checklist

Before going live:

- [ ] BOT_TOKEN configured and tested
- [ ] OPENAI_API_KEY configured (if using AI features)
- [ ] Service starts successfully
- [ ] Service auto-starts on reboot (`systemctl is-enabled ru-corrector-bot`)
- [ ] Logs are accessible and rotated
- [ ] Bot responds to test messages
- [ ] Voice transcription works (if using OpenAI)
- [ ] Monitoring set up (optional: systemd status, log alerts)
- [ ] .env file backed up securely
- [ ] Team knows how to restart/update the bot

## Support

- **Logs**: `/var/log/ru-corrector-bot/` and `journalctl -u ru-corrector-bot`
- **Issues**: https://github.com/vanserokok-arch/ru-corrector-bot/issues
- **Status**: `sudo systemctl status ru-corrector-bot`
