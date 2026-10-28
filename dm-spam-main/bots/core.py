#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nucleo compartido del panel DM-SPAM.
Todo en rojo neon: banner, prompts, salida al panel y utilidades.
"""

import asyncio
import os
import sys

import discord

# ---------- Paleta ROJA ----------
RED     = "\033[1;38;5;196m"   # rojo neon
GREEN   = "\033[38;5;203m"     # rojo claro
YELLOW  = "\033[38;5;160m"     # rojo oscuro
BLUE    = "\033[1;38;5;196m"
MAGENTA = "\033[38;5;203m"
CYAN    = "\033[1;38;5;196m"
WHITE   = "\033[1;38;5;196m"
GRAY    = "\033[38;5;160m"
BOLD    = "\033[1m"
RESET   = "\033[0m"

ROJO       = "\033[1;38;5;196m"
ROJO_CLARO = "\033[38;5;203m"
ROJO_OSCURO = "\033[38;5;160m"

ANCHO = 66
SEP = "=" * ANCHO

BANNER_LINES = [
    "██████╗ ███╗   ███╗      ███████╗██████╗  █████╗ ███╗   ███╗",
    "██╔══██╗████╗ ████║      ██╔════╝██╔══██╗██╔══██╗████╗ ████║",
    "██║  ██║██╔████╔██║█████╗███████╗██████╔╝███████║██╔████╔██║",
    "██║  ██║██║╚██╔╝██║╚════╝╚════██║██╔═══╝ ██╔══██║██║╚██╔╝██║",
    "██████╔╝██║ ╚═╝ ██║      ███████║██║     ██║  ██║██║ ╚═╝ ██║",
    "╚═════╝ ╚═╝     ╚═╝      ╚══════╝╚═╝     ╚═╝  ╚═╝╚═╝     ╚═╝",
]

SALIR_TOKENS = {"salir", "exit", "quit", "0", "/salir", "q", "volver"}
SALIR_PEDIR = {"salir", "exit", "volver"}


def neon(texto):
    """Todo el texto en rojo neon."""
    if not texto:
        return ""
    return f"{ROJO}{texto}{RESET}"


def titulo(texto):
    print(f"\n{ROJO}{BOLD}{texto}{RESET}")


def clear_screen():
    os.system("clear")


def banner(subtitulo=""):
    print(f"{ROJO}{BOLD}")
    for linea in BANNER_LINES:
        print(linea)
    print(f"{SEP}{RESET}")
    if subtitulo:
        print(f"{ROJO_CLARO}{BOLD}{subtitulo.center(ANCHO)}{RESET}")
        print(f"{ROJO}{BOLD}{SEP}{RESET}")
    print()


def pantalla(subtitulo=""):
    clear_screen()
    banner(subtitulo)


def pedir(texto, obligatorio=True, defecto=None, permitir_salir=True):
    while True:
        prompt = f"{ROJO}{BOLD}-> {texto}: {RESET}"
        valor = input(prompt).strip()
        if permitir_salir and valor.lower() in SALIR_PEDIR:
            print(f"{ROJO}[-] Volviendo al panel...{RESET}")
            sys.exit(0)
        if valor:
            return valor
        if not obligatorio:
            return defecto
        print(f"{ROJO}[X] Este campo es obligatorio.{RESET}")


def pedir_int(texto, defecto=None, permitir_salir=True):
    while True:
        prompt = f"{ROJO}{BOLD}-> {texto}: {RESET}"
        valor = input(prompt).strip()
        if permitir_salir and valor.lower() in SALIR_PEDIR:
            print(f"{ROJO}[-] Volviendo al panel...{RESET}")
            sys.exit(0)
        if not valor:
            if defecto is not None:
                return defecto
            print(f"{ROJO_CLARO}[!] Campo obligatorio.{RESET}")
            continue
        try:
            return int(valor)
        except ValueError:
            print(f"{ROJO_CLARO}[!] Debe ser un numero entero.{RESET}")


async def salir(bot):
    print(f"\n{ROJO}{BOLD}[-] Volviendo al panel...{RESET}")
    try:
        await bot.close()
    except Exception:
        pass
    await asyncio.sleep(0.2)
    os._exit(0)


async def escuchar_salida(bot):
    while True:
        try:
            linea = await asyncio.to_thread(input)
        except (EOFError, KeyboardInterrupt):
            await salir(bot)
            return
        if linea.strip().lower() in SALIR_TOKENS:
            await salir(bot)
            return


def instalar_salida(bot):
    from discord.ext import commands

    if getattr(bot, "_salida_instalada", False):
        return

    @bot.command(name="salir")
    @commands.is_owner()
    async def _salir_cmd(ctx):
        await salir(bot)

    @bot.command(name="exit")
    @commands.is_owner()
    async def _exit_cmd(ctx):
        await salir(bot)

    bot._salida_instalada = True
    asyncio.create_task(escuchar_salida(bot))


# ---------------------------------------------------------------------------
#  UTILIDADES DE ENVIO
# ---------------------------------------------------------------------------

async def enviar_dm(destino, texto, reintentos=3):
    for intento in range(reintentos):
        try:
            await destino.send(texto)
            return True
        except discord.errors.Forbidden:
            return False
        except discord.errors.HTTPException as e:
            if e.status == 429:
                await asyncio.sleep(float(getattr(e, "retry_after", 2)) + 0.5)
                continue
            return False
        except Exception:
            await asyncio.sleep(1)
    return False


async def obtener_miembros(guild, incluir_bots=False):
    miembros = []
    try:
        async for m in guild.fetch_members(limit=None):
            if incluir_bots or not m.bot:
                miembros.append(m)
        if miembros:
            return miembros
    except Exception:
        pass

    try:
        await guild.chunk()
    except Exception:
        pass

    return [m for m in guild.members if incluir_bots or not m.bot]
