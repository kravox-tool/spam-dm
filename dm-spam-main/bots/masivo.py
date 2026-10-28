#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MASIVO :: Envia un mensaje personalizado N veces a todos los usuarios de un servidor.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import discord
from discord.ext import commands
import core

intents = discord.Intents.default()
intents.guilds = True
intents.guild_messages = True
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=".", intents=intents)

bot.guild_id = None
bot.mensaje_ataque = ""
bot.veces = 1
bot.incluir_bots = False
bot._salida_instalada = False
bot._lanzado = False


async def lanzar_masivo():
    # --- Resolver servidor ---
    guild = None
    try:
        guild = bot.get_guild(bot.guild_id)
        if guild is None:
            guild = await bot.fetch_guild(bot.guild_id)
    except Exception:
        print(f"\n{core.RED}{core.BOLD}[X] No se encontro el servidor con esa ID.{core.RESET}")
        print(f"{core.GRAY}[i] Verifica que la ID sea la del servidor y que el bot este dentro.{core.RESET}")
        await asyncio.sleep(4)
        await core.salir(bot)
        return

    print(f"\n{core.YELLOW}[*] Servidor: {guild.name} ({guild.id}){core.RESET}")
    print(f"{core.YELLOW}[*] Obteniendo miembros...{core.RESET}")

    try:
        miembros = await core.obtener_miembros(guild, incluir_bots=bot.incluir_bots)
    except Exception as e:
        print(f"\n{core.RED}[X] Error obteniendo miembros: {e}{core.RESET}")
        miembros = []

    miembros = [m for m in miembros if m.id != bot.user.id]

    if not miembros:
        print(f"\n{core.RED}{core.BOLD}[X] La lista de miembros vino vacia.{core.RESET}")
        print(f"{core.GRAY}[i] Revisa que el intent 'Server Members' este activado en el portal.{core.RESET}")
        await asyncio.sleep(4)
        await core.salir(bot)
        return

    print(f"\n{core.RED}{core.BOLD}{core.SEP}")
    print(f"[>] SERVIDOR: {guild.name.upper()} ({guild.id})")
    print(f"[>] MIEMBROS OBJETIVO: {len(miembros)}")
    print(f"[>] MENSAJES POR USUARIO: {bot.veces}")
    print(f"{core.SEP}{core.RESET}\n")

    ok, fallidos, enviados = 0, 0, 0

    for i, miembro in enumerate(miembros, 1):
        entrego = True
        for _ in range(bot.veces):
            if await core.enviar_dm(miembro, bot.mensaje_ataque):
                enviados += 1
            else:
                entrego = False
                break

        if entrego:
            ok += 1
            estado = f"{core.GREEN}OK{core.RESET}"
        else:
            fallidos += 1
            estado = f"{core.YELLOW}DMs cerrados{RESET}"

        print(f"{core.GREEN}[+] [{i}/{len(miembros)}] {miembro.name} -> {estado}")
        await asyncio.sleep(0.35)

    print(f"\n{core.GREEN}{core.BOLD}{core.SEP}")
    print(f"[OK] FINALIZADO | Alcanzados: {ok} | Fallidos: {fallidos} | Mensajes: {enviados}")
    print(f"{core.SEP}{core.RESET}")

    await asyncio.sleep(3)
    await core.salir(bot)


@bot.event
async def on_ready():
    core.instalar_salida(bot)
    print(f"\n{core.GREEN}{core.BOLD}[OK] CONECTADO COMO: {bot.user.name.upper()}{core.RESET}")
    print(f"{core.GRAY}[*] Escribe 'salir' para volver al panel.{core.RESET}")

    if not bot._lanzado:
        bot._lanzado = True
        asyncio.create_task(lanzar_masivo())


def main():
    core.pantalla("MASIVO :: TODO EL SERVIDOR")

    core.titulo("[ CONFIGURACION DE CONEXION ]")
    token = core.pedir("Coloca el token del bot")

    core.titulo("[ CONFIGURACION DEL SERVIDOR ]")
    bot.guild_id = core.pedir_int("Coloca la ID del servidor")

    core.titulo("[ CONFIGURACION DEL MENSAJE ]")
    bot.mensaje_ataque = core.pedir("Escribe tu mensaje personalizado", permitir_salir=False)

    core.titulo("[ CONFIGURACION DE CANTIDAD ]")
    bot.veces = core.pedir_int("Cuantos mensajes por usuario? (ENTER = 1)", defecto=1)

    core.titulo("[ OPCIONES ]")
    inc = input(f"{core.neon('-> ')}{core.neon('Incluir bots tambien? (s/N)')}{core.neon(': ')}").strip().lower()
    bot.incluir_bots = inc == "s"

    print(f"\n{core.YELLOW}{core.BOLD}{core.SEP}")
    print("[*] Validando parametros y estableciendo conexion...")
    print(f"{core.SEP}{core.RESET}")
    print(f"{core.GRAY}[*] Escribe 'salir' en cualquier momento para volver al panel.{core.RESET}")

    try:
        bot.run(token)
    except discord.errors.LoginFailure:
        print(f"\n{core.RED}{core.BOLD}[X] ERROR: El token ingresado es incorrecto o expiro.{core.RESET}")
        input(f"{core.GRAY}ENTER para volver al panel...{core.RESET}")
    except KeyboardInterrupt:
        print(f"\n{core.RED}{core.BOLD}[-] Script cerrado por el usuario.{core.RESET}")


if __name__ == '__main__':
    main()
