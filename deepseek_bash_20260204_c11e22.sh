#!/bin/bash
# Auto-update script for TGhelper bot
# Script name: update_bot.sh

echo "======================================="
echo "Starting TGhelper bot update process..."
echo "======================================="

# Go to bot directory
cd /bots/TGhelper || {
    echo "ERROR: Cannot change directory to /bots/TGhelper"
    exit 1
}

# Stop the bot service
echo "1. Stopping bot service..."
sudo systemctl stop tg-helper-bot
sleep 2

# Check if process stopped
if pgrep -f "Helpus.py" > /dev/null; then
    echo "WARNING: Bot process still running. Force stopping..."
    pkill -f "Helpus.py"
    sleep 2
fi

# Backup current .env file (important!)
echo "2. Backing up .env file..."
if [ -f .env ]; then
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
    echo "   .env backed up successfully"
else
    echo "   WARNING: .env file not found!"
fi

# Pull latest code from GitHub
echo "3. Pulling latest code from GitHub..."
git pull origin main

# Check if pull was successful
if [ $? -ne 0 ]; then
    echo "ERROR: Git pull failed!"
    echo "Restoring .env from backup..."
    # Find latest backup
    latest_backup=$(ls -t .env.backup.* 2>/dev/null | head -1)
    if [ -f "$latest_backup" ]; then
        cp "$latest_backup" .env
        echo "   .env restored from backup"
    fi
    exit 1
fi

# Restore .env if it was overwritten
echo "4. Ensuring .env file is intact..."
if [ ! -f .env ] && [ -f .env.backup.* ]; then
    latest_backup=$(ls -t .env.backup.* | head -1)
    cp "$latest_backup" .env
    echo "   .env restored from backup"
elif [ -f .env.backup.* ] && [ -f .env ]; then
    # Compare if .env was changed during pull
    latest_backup=$(ls -t .env.backup.* | head -1)
    if ! cmp -s .env "$latest_backup"; then
        echo "   WARNING: .env was modified during update"
        echo "   Keeping current .env"
    fi
fi

# Update Python dependencies
echo "5. Updating Python dependencies..."
if [ -d "venv" ]; then
    source venv/bin/activate
    pip install -r requirements.txt --upgrade
    echo "   Dependencies updated"
else
    echo "   ERROR: Virtual environment not found!"
    exit 1
fi

# Start the bot service
echo "6. Starting bot service..."
sudo systemctl start tg-helper-bot
sleep 3

# Check if bot started successfully
echo "7. Verifying bot status..."
if sudo systemctl is-active --quiet tg-helper-bot; then
    echo "   SUCCESS: Bot service is running"
else
    echo "   ERROR: Bot service failed to start"
    echo "   Checking logs..."
    sudo journalctl -u tg-helper-bot -n 10 --no-pager
    exit 1
fi

# Clean up old backups (keep last 5)
echo "8. Cleaning up old backups..."
ls -t .env.backup.* 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null

echo "======================================="
echo "Update process completed!"
echo "Bot should be running with latest code."
echo "Check logs: sudo journalctl -u tg-helper-bot -f"
echo "======================================="