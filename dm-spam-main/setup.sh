#!/data/data/com.termux/files/usr/bin/bash
# Instalador automatico para Termux
echo "[*] Actualizando paquetes..."
pkg update -y && pkg upgrade -y

echo "[*] Instalando Python..."
pkg install -y python

echo "[*] Actualizando pip..."
pip install --upgrade pip

echo "[*] Instalando dependencias..."
pip install -r requirements.txt

echo "[*] Solicitando acceso al almacenamiento..."
termux-setup-storage

echo ""
echo "[OK] Instalacion completa. Ejecuta: python main.py"
