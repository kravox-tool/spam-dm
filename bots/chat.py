#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CHAT :: Chat en vivo por consola con una ID.
Descarga multimedia, guarda historial y permite salir al panel en cualquier momento.
"""

import asyncio
import os
import sys
import json
import urllib.request

import discord
from discord.ext import commands
import discord.errors

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.formatted_text import FormattedText, ANSI
from prompt_toolkit import print_formatted_text

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=".", intents=intents)

# Colores ANSI
CYAN = "\033[1;36m"
GREEN = "\033[1;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[1;34m"
MAGENTA = "\033[1;35m"
RED = "\033[1;31m"
GRAY = "\033[0;90m"
WHITE = "\033[1;37m"
BOLD = "\033[1m"
RESET = "\033[0m"

bot.target_user_id = None
bot.target_user_obj = None

HISTORIAL_FILE = "historial_chats.json"
CARPETA_MEDIA = "/sdcard/Download/Chat_Media/"

BANNER_LINES = [
    "██████╗ ███╗   ███╗      ███████╗██████╗  █████╗ ███╗   ███╗",
    "██╔══██╗████╗ ████║      ██╔════╝██╔══██╗██╔══██╗████╗ ████║",
    "██║  ██║██╔████╔██║█████╗███████╗██████╔╝███████║██╔████╔██║",
    "██║  ██║██║╚██╔╝██║╚════╝╚════██║██╔═══╝ ██╔══██║██║╚██╔╝██║",
    "██████╔╝██║ ╚═╝ ██║      ███████║██║     ██║  ██║██║ ╚═╝ ██║",
    "╚═════╝ ╚═╝     ╚═╝      ╚══════╝╚═╝     ╚═╝  ╚═╝╚═╝     ╚═╝",
]


def clear_screen():
    os.system('clear')


def banner():
    print_formatted_text(ANSI(f"{RED}{BOLD}"))
    for linea in BANNER_LINES:
        print_formatted_text(ANSI(linea))
    print_formatted_text(ANSI(f"{RESET}"))


def enter_chat_layout():
    clear_screen()
    print_formatted_text(ANSI(f"{CYAN}╔════════════════════════════════════════════════════════════╗{RESET}"))
    print_formatted_text(ANSI(f"{CYAN}║ {WHITE}CHAT EN VIVO: {GREEN}{bot.target_user_obj.name.upper()}{RESET}"))
    print_formatted_text(ANSI(f"{CYAN}║ {WHITE}ID OBJETIVO:  {YELLOW}{bot.target_user_obj.id}{RESET}"))
    print_formatted_text(ANSI(f"{CYAN}║ {GRAY}Comando para salir: /salir  (o escribe: salir){RESET}"))
    print_formatted_text(ANSI(f"{CYAN}╚════════════════════════════════════════════════════════════╝{RESET}\n"))


def guardar_en_historial(user_name, user_id, remitente, mensaje):
    data = {}
    if os.path.exists(HISTORIAL_FILE):
        try:
            with open(HISTORIAL_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

    str_id = str(user_id)
    if str_id not in data:
        data[str_id] = {"name": user_name, "logs": []}

    data[str_id]["logs"].append(f"[{remitente}]: {mensaje}")

    with open(HISTORIAL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def ver_historial_consola(user_id):
    clear_screen()
    print_formatted_text(ANSI(f"{BLUE}╔════ REGISTRO DE CONVERSACION GUARDADA ════════════════════╗{RESET}\n"))
    if not os.path.exists(HISTORIAL_FILE):
        print_formatted_text(ANSI(f"{YELLOW}  [!] No hay historial registrado aun.{RESET}\n"))
        print_formatted_text(ANSI(f"{BLUE}╚════════════════════════════════════════════════════════════╝{RESET}"))
        return False

    with open(HISTORIAL_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    str_id = str(user_id)
    if str_id not in data or not data[str_id]["logs"]:
        print_formatted_text(ANSI(f"{YELLOW}  [!] No hay registros con la ID {user_id}.{RESET}\n"))
        print_formatted_text(ANSI(f"{BLUE}╚════════════════════════════════════════════════════════════╝{RESET}"))
        return False

    for log in data[str_id]["logs"]:
        if "[Tu (Bot)]" in log:
            print_formatted_text(ANSI(f"  {GREEN}{log}{RESET}"))
        else:
            print_formatted_text(ANSI(f"  {YELLOW}{log}{RESET}"))
    print_formatted_text(ANSI(f"\n{BLUE}╚════════════════════════════════════════════════════════════╝{RESET}"))
    return True


def descargar_archivo_multimedia(url, nombre_archivo):
    try:
        if not os.path.exists(CARPETA_MEDIA):
            os.makedirs(CARPETA_MEDIA, exist_ok=True)
        ruta_completa = os.path.join(CARPETA_MEDIA, nombre_archivo)
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response, open(ruta_completa, 'wb') as out_file:
            out_file.write(response.read())
        return ruta_completa
    except Exception:
        return None


async def terminal_input_loop():
    session = PromptSession()
    prompt_texto = FormattedText([('ansigreen bold', '-> Tu (Bot): ')])

    with patch_stdout():
        while True:
            try:
                user_input = await session.prompt_async(prompt_texto)
                user_input = user_input.strip()

                if not user_input:
                    continue

                if user_input.lower() in ("/salir", "salir", "exit", "0"):
                    print_formatted_text(ANSI(f"\n{RED}[-] Volviendo al panel...{RESET}"))
                    await bot.close()
                    os._exit(0)

                if bot.target_user_obj:
                    try:
                        await bot.target_user_obj.send(content=user_input)
                        guardar_en_historial(bot.target_user_obj.name, bot.target_user_id, "Tu (Bot)", user_input)
                        print("")
                    except discord.errors.Forbidden:
                        print_formatted_text(ANSI(f"\n{RED}┌── [X] ERROR DE ENVIO ────────────────────────────┐{RESET}"))
                        print_formatted_text(ANSI(f"{RED}│ El usuario te bloqueo o cerro sus mensajes DMs.  │{RESET}"))
                        print_formatted_text(ANSI(f"{RED}└──────────────────────────────────────────────────┘{RESET}\n"))
                    except Exception as e:
                        print_formatted_text(ANSI(f"\n{RED}┌── [X] ERROR DESCONOCIDO ─────────────────────────┐{RESET}"))
                        print_formatted_text(ANSI(f"{RED}│ {e}{RESET}"))
                        print_formatted_text(ANSI(f"{RED}└──────────────────────────────────────────────────┘{RESET}\n"))
            except (KeyboardInterrupt, EOFError):
                await bot.close()
                os._exit(0)


@bot.event
async def on_ready():
    try:
        bot.target_user_obj = await bot.fetch_user(bot.target_user_id)
        enter_chat_layout()
    except Exception:
        print_formatted_text(ANSI(f"\n{RED}[X] Error fatal: La ID provista no existe en Discord.{RESET}"))
        await bot.close()
        os._exit(0)

    asyncio.create_task(terminal_input_loop())


@bot.event
async def on_message(message):
    if message.author.id == bot.user.id:
        return

    if message.guild is None and message.author.id == bot.target_user_id:
        if message.content:
            print_formatted_text(ANSI(f"{YELLOW}┌── MENSAJE ENTRANTE: [{message.author.name}] ─────────────────┐{RESET}"))
            print_formatted_text(ANSI(f"{WHITE}│ {message.content}{RESET}"))
            print_formatted_text(ANSI(f"{YELLOW}└──────────────────────────────────────────────────────────────┘{RESET}\n"))
            guardar_en_historial(message.author.name, bot.target_user_id, message.author.name, message.content)

        if message.attachments:
            for adjunto in message.attachments:
                url = adjunto.url
                filename = adjunto.filename
                filename_lower = filename.lower()
                ruta_guardado = descargar_archivo_multimedia(url, filename)

                estado = f"{GREEN}Descargado localmente{RESET}" if ruta_guardado else f"{RED}Error al descargar{RESET}"

                if any(ext in filename_lower for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                    tipo = "IMAGEN"
                elif any(ext in filename_lower for ext in ['.mp3', '.ogg', '.wav', '.m4a', '.oga']):
                    tipo = "AUDIO / NOTA DE VOZ"
                else:
                    tipo = "ARCHIVO / DOCUMENTO"

                print_formatted_text(ANSI(f"{MAGENTA}┌── {tipo} DE [{message.author.name}] ─────────────────────┐{RESET}"))
                print_formatted_text(ANSI(f"{MAGENTA}│ {WHITE}Archivo: {CYAN}{filename}{RESET}"))
                print_formatted_text(ANSI(f"{MAGENTA}│ {WHITE}Estado:  {estado}"))
                print_formatted_text(ANSI(f"{MAGENTA}│ {WHITE}Enlace:  {GRAY}{url}{RESET}"))
                print_formatted_text(ANSI(f"{MAGENTA}└──────────────────────────────────────────────────────────────┘{RESET}\n"))
                guardar_en_historial(message.author.name, bot.target_user_id, message.author.name, f"[{tipo}: {filename}]")


def main():
    clear_screen()
    banner()
    print_formatted_text(ANSI(f"{CYAN}╔════════════════════════════════════════════════════════════╗{RESET}"))
    print_formatted_text(ANSI(f"{CYAN}║ {WHITE}          PARAMETROS DE ACCESO CHAT MEDIA          {CYAN}║{RESET}"))
    print_formatted_text(ANSI(f"{CYAN}╚════════════════════════════════════════════════════════════╝{RESET}\n"))

    print_formatted_text(ANSI(f"{GREEN}┌── PASO 1: TOKEN DEL BOT ──────────────────────────────────┐{RESET}"))
    token = input("│ Ingresa el Token:\n└─> ").strip()
    if not token:
        sys.exit()

    print_formatted_text(ANSI(f"\n{BLUE}┌── PASO 2: ID DEL USUARIO OBJETIVO ─────────────────────────┐{RESET}"))
    id_input = input("│ Ingresa la ID:\n└─> ").strip()
    if not id_input:
        sys.exit()

    try:
        user_id = int(id_input)
        bot.target_user_id = user_id
    except ValueError:
        print_formatted_text(ANSI(f"\n{RED}[X] La ID debe ser un valor numerico.{RESET}"))
        sys.exit()

    print_formatted_text(ANSI(f"\n{MAGENTA}┌── PASO 3: MODO DE SESION ─────────────────────────────────┐{RESET}"))
    print_formatted_text(ANSI(f"{MAGENTA}│ {WHITE}1 -> Entrar directamente al chat en vivo                  {MAGENTA}│{RESET}"))
    print_formatted_text(ANSI(f"{MAGENTA}│ {WHITE}2 -> Consultar historial guardado con esta ID              {MAGENTA}│{RESET}"))
    print_formatted_text(ANSI(f"{MAGENTA}└────────────────────────────────────────────────────────────┘{RESET}"))

    opcion = input("└─> Elige opcion (1 o 2): ").strip()

    if opcion == "2":
        existe_registro = ver_historial_consola(user_id)
        if existe_registro:
            input("\nPresiona ENTER para conectar el chat en vivo...")
        else:
            input("\nPresiona ENTER para continuar...")
        clear_screen()

    print_formatted_text(ANSI(f"\n{YELLOW}[*] Conectando con los servidores de Discord...{RESET}"))
    print_formatted_text(ANSI(f"{GRAY}[*] Escribe 'salir' en cualquier momento para volver al panel.{RESET}"))

    try:
        bot.run(token)
    except discord.errors.LoginFailure:
        print_formatted_text(ANSI(f"\n{RED}[X] ERROR: Token de Discord invalido o vencido.{RESET}"))
        input(f"{GRAY}ENTER para volver al panel...{RESET}")
    except KeyboardInterrupt:
        print_formatted_text(ANSI(f"\n{RED}[-] Script detenido por el usuario.{RESET}"))


if __name__ == '__main__':
    main()
