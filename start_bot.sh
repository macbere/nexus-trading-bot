#!/bin/bash
cd ~/trading_bot
if ! pgrep -f "python3 main.py" > /dev/null; then
    echo "$(date): Starting bot..." >> logs/watchdog.log
    nohup python3 main.py >> logs/bot.log 2>&1 &
    echo "$(date): Bot started PID=$!" >> logs/watchdog.log
else
    echo "$(date): Bot already running" >> logs/watchdog.log
fi
