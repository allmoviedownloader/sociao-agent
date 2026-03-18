#!/data/data/com.termux/files/usr/bin/bash
# Termux:Boot script - Auto-starts the bot when phone reboots
cd ~/social2.0
tmux new-session -d -s bot "python -m bot.main"
