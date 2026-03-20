#!/bin/bash
cd ~/trading_bot
while true; do
    if ! pgrep -f "python3 main.py" > /dev/null; then
        echo "$(date): Restarting bot..." >> logs/watchdog.log
        nohup python3 main.py >> logs/bot.log 2>&1 &
        echo "$(date): Bot restarted PID=$!" >> logs/watchdog.log
    fi
    sleep 60
done
