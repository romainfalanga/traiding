#!/bin/bash
# ============================================
# Macro Pulse — Script de deploiement automatique
# A executer sur un serveur Ubuntu (Oracle Cloud Free Tier)
# ============================================

set -e

echo "================================================"
echo "  MACRO PULSE — Installation automatique"
echo "================================================"
echo ""

# 1. Mise a jour systeme
echo "[1/6] Mise a jour du systeme..."
sudo apt update && sudo apt upgrade -y

# 2. Installation Python 3.11
echo "[2/6] Installation de Python 3.11..."
sudo apt install -y python3.11 python3.11-venv python3.11-dev git curl

# 3. Clone du repo
echo "[3/6] Clone du projet..."
cd ~
if [ -d "traiding" ]; then
    echo "  -> Dossier existant, mise a jour..."
    cd traiding && git pull origin main
else
    git clone https://github.com/romainfalanga/traiding.git
    cd traiding
fi

# 4. Setup Python
echo "[4/6] Installation des dependances Python..."
cd bot
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install setuptools==69.5.1
pip install --ignore-installed PyJWT
pip install -r requirements.txt

# 5. Verification du .env
echo "[5/6] Verification de la configuration..."
if [ ! -f .env ]; then
    echo ""
    echo "============================================"
    echo "  ATTENTION : Fichier .env manquant !"
    echo "============================================"
    echo ""
    echo "Cree le fichier .env avec :"
    echo "  nano ~/traiding/bot/.env"
    echo ""
    echo "Et colle le contenu suivant (adapte tes cles) :"
    echo ""
    cat <<'ENVTEMPLATE'
# IA — Cle unique pour TOUT
OPENROUTER_API_KEY=sk-or-v1-XXXXXXXXXXXXXXXXXXXXXXXX

# Modeles des 3 agents
AGENT_QUANT_MODEL=deepseek/deepseek-r1
AGENT_MACRO_MODEL=deepseek/deepseek-r1:online
AGENT_CONTRARIAN_MODEL=meta-llama/llama-3.1-8b-instruct:free
MODEL_LIGHT=meta-llama/llama-3.1-8b-instruct:free
MODEL_SEARCH=perplexity/sonar

# Donnees
FINNHUB_API_KEY=XXXXXXXXXXXXXXXXXXXXXXXX
WHALE_ALERT_API_KEY=

# Base de donnees
SUPABASE_URL=https://XXXXXXXX.supabase.co
SUPABASE_SERVICE_KEY=eyXXXXXXXXXXXX

# Trading
INITIAL_BALANCE=10000
TRADING_FEE_PCT=0.075

# Consensus Multi-Agent
MIN_CONSENSUS=2
MIN_CONFIDENCE_AVG=0.6

# Risk Management
MAX_POSITION_PCT=5
MAX_CONCURRENT_TRADES=3
MIN_RR_RATIO=1.5
MIN_MTF_CONFLUENCE=2
CIRCUIT_BREAKER_CONSECUTIVE_LOSSES=3
CIRCUIT_BREAKER_DRAWDOWN_PAUSE=10
CIRCUIT_BREAKER_DRAWDOWN_STOP=15
CORRELATION_THRESHOLD=0.75
POST_EVENT_COOLDOWN_MINUTES=30

# Logging
LOG_LEVEL=INFO
ENVTEMPLATE
    echo ""
    echo "Puis relance ce script."
    exit 1
fi

echo "  -> .env trouve OK"

# 6. Creation du service systemd
echo "[6/6] Creation du service systemd..."
WORKDIR="$(pwd)"
PYTHON_PATH="$WORKDIR/venv/bin/python"
USER="$(whoami)"

sudo tee /etc/systemd/system/macropulse.service > /dev/null <<EOF
[Unit]
Description=Macro Pulse Trading Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$WORKDIR
ExecStart=$PYTHON_PATH main.py
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable macropulse
sudo systemctl start macropulse

echo ""
echo "================================================"
echo "  MACRO PULSE est lance !"
echo "================================================"
echo ""
echo "Commandes utiles :"
echo "  sudo journalctl -u macropulse -f     # Voir les logs en direct"
echo "  sudo systemctl status macropulse      # Verifier le statut"
echo "  sudo systemctl restart macropulse     # Redemarrer"
echo "  sudo systemctl stop macropulse        # Arreter"
echo ""
echo "Le bot va maintenant :"
echo "  - Collecter les donnees macro, marche, DeFi, options"
echo "  - Detecter le regime de marche"
echo "  - Faire voter les 3 agents IA"
echo "  - Executer des trades paper"
echo "  - Alimenter ton dashboard en temps reel"
echo ""
echo "Ton dashboard : va sur ton URL Vercel pour voir les donnees arriver"
echo "================================================"
