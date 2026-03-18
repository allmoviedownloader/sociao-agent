#!/data/data/com.termux/files/usr/bin/bash
# ============================================
# Termux Auto-Setup Script for Instagram Repost Agent
# Run this ONCE after copying project to phone
# ============================================

echo "🚀 Instagram Repost Agent - Termux Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Step 1: Setup storage access
echo ""
echo "📁 Step 1: Setting up storage access..."
termux-setup-storage 2>/dev/null
sleep 2

# Step 2: Copy project from sdcard to Termux home
echo "📋 Step 2: Copying project files..."
if [ -d "/sdcard/social2.0" ]; then
    cp -r /sdcard/social2.0 ~/social2.0
    echo "✅ Files copied from /sdcard/social2.0"
elif [ -d "/sdcard/Download/social2.0" ]; then
    cp -r /sdcard/Download/social2.0 ~/social2.0
    echo "✅ Files copied from /sdcard/Download/social2.0"
elif [ -d "$(pwd)" ] && [ -f "$(pwd)/bot/main.py" ]; then
    echo "✅ Already in project directory"
else
    echo "❌ Project folder not found!"
    echo "   Copy 'social2.0' folder to phone storage first"
    echo "   Then run this script again"
    exit 1
fi

cd ~/social2.0 || exit 1

# Step 3: Install Python packages
echo ""
echo "📦 Step 3: Installing Python dependencies..."
echo "   (This may take 2-5 minutes...)"
pkg install -y python rust binutils 2>/dev/null
pip install --upgrade pip
pip install aiogram instagrapi requests apscheduler aiosqlite python-dotenv aiohttp aiofiles Pillow google-generativeai

# Step 4: Create necessary directories
echo ""
echo "📂 Step 4: Creating directories..."
mkdir -p downloads data logs

# Step 5: Disable battery optimization prompt
echo ""
echo "🔋 Step 5: Battery optimization..."
echo "   ⚠️  IMPORTANT: Go to phone Settings:"
echo "   Settings → Apps → Termux → Battery → Unrestricted"
echo "   This prevents Android from killing the bot!"
echo ""

# Step 6: Show status
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Setup Complete!"
echo ""
echo "📋 To START the bot, run:"
echo "   cd ~/social2.0"
echo "   tmux new -s bot"
echo "   python -m bot.main"
echo ""
echo "📋 To DETACH (bot keeps running):"
echo "   Press: Ctrl+B, then D"
echo ""
echo "📋 To REATTACH later:"
echo "   tmux attach -t bot"
echo ""
echo "🔄 To AUTO-START on boot:"
echo "   Install Termux:Boot from F-Droid"
echo "   mkdir -p ~/.termux/boot"
echo "   cp ~/social2.0/termux_boot.sh ~/.termux/boot/"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
