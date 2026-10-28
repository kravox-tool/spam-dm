#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FLASH :: Envia mensajes a un usuario o a todo el servidor y los borra rapido.
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

bot.modo = "usuario"          # "usuario" o "servidor"
bot.target_id = None
bot.mensaje_ataque = ""
bot.cantidad_mensajes = 1
bot.delay_borrado = 0.0
bot._salida_instalada = False
bot._lanzado = False


async def enviar_y_borrar(destino, texto, delay):
    """Envia el mensaje y lo borra enseguida. Devuelve True si se entrego."""
    try:
        msg = await destino.send(texto)
    except discord.errors.Forbidden:
        return False
    except discord.errors.HTTPException as e:
        if e.status == 429:
            await asyncio.sleep(float(getattr(e, "retry_after", 2)) + 0.5)
        return False
    except Exception:
        return False

    try:
        if delay > 0:
            await asyncio.sleep(delay)
        await msg.delete()
    except Exception:
        pass
    return True


async def lanzar_flash():
    # --- Resolver objetivos ---
    if bot.modo == "usuario":
        try:
            objetivo = await bot.fetch_user(bot.target_id)
        except Exception:
            print(f"\n{core.RED}{core.BOLD}[X] ID de usuario invalida.{core.RESET}")
            await asyncio.sleep(4)
            await core.salir(bot)
            return
        objetivos = [objetivo]
    else:
        guild = None
        try:
            guild = bot.get_guild(bot.target_id)
            if guild is None:
                guild = await bot.fetch_guild(bot.target_id)
        except Exception:
            print(f"\n{core.RED}{core.BOLD}[X] ID de servidor invalida.{core.RESET}")
            print(f"{core.GRAY}[i] Verifica que la ID sea la del servidor y que el bot este dentro.{core.RESET}")
            await asyncio.sleep(4)
            await core.salir(bot)
            return

        print(f"\n{core.YELLOW}[*] Servidor: {guild.name} ({guild.id}){core.RESET}")
        print(f"{core.YELLOW}[*] Obteniendo miembros...{core.RESET}")

        try:
            objetivos = await core.obtener_miembros(guild, incluir_bots=False)
        except Exception as e:
            print(f"\n{core.RED}[X] Error obteniendo miembros: {e}{core.RESET}")
            objetivos = []

        objetivos = [m for m in objetivos if m.id != bot.user.id]

    if not objetivos:
        print(f"\n{core.RED}{core.BOLD}[X] No hay objetivos disponibles.{core.RESET}")
        print(f"{core.GRAY}[i] Revisa que el intent 'Server Members' este activado en el portal.{core.RESET}")
        await asyncio.sleep(4)
        await core.salir(bot)
        return

    print(f"\n{core.RED}{core.BOLD}{core.SEP}")
    print(f"[>] OBJETIVOS: {len(objetivos)}")
    print(f"[>] MENSAJES POR OBJETIVO: {bot.cantidad_mensajes}")
    print(f"[>] BORRADO: {'inmediato' if bot.delay_borrado == 0 else str(bot.delay_borrado) + 's'}")
    print(f"{core.SEP}{core.RESET}\n")

    total = 0
    for i, objetivo in enumerate(objetivos, 1):
        enviados_obj = 0
        for _ in range(bot.cantidad_mensajes):
            if await enviar_y_borrar(objetivo, bot.mensaje_ataque, bot.delay_borrado):
                total += 1
                enviados_obj += 1
        print(f"{core.GREEN}[+] [{i}/{len(objetivos)}] {objetivo.name} -> "
              f"{enviados_obj} flash{core.RESET}")
        await asyncio.sleep(0.3)

    print(f"\n{core.GREEN}{core.BOLD}{core.SEP}")
    print(f"[OK] FINALIZADO | Mensajes enviados y borrados: {total}")
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
        asyncio.create_task(lanzar_flash())


def main():
    core.pantalla("FLASH :: ENVIAR Y BORRAR")

    core.titulo("[ CONFIGURACION DE CONEXION ]")
    token = core.pedir("Coloca el token del bot")

    core.titulo("[ DESTINO ]")
    print(f" {core.WHITE}[1]{core.RESET} Un usuario (por ID)")
    print(f" {core.WHITE}[2]{core.RESET} Todos los usuarios de un servidor (por ID)")
    opcion = input(f"{core.neon('-> ')}{core.neon('Elige 1 o 2')}{core.neon(': ')}").strip()
    bot.modo = "usuario" if opcion != "2" else "servidor"

    if bot.modo == "usuario":
        bot.target_id = core.pedir_int("ID del usuario destino")
    else:
        bot.target_id = core.pedir_int("ID del servidor destino")

    core.titulo("[ CONFIGURACION DEL MENSAJE ]")
    bot.mensaje_ataque = core.pedir("Escribe tu mensaje", permitir_salir=False)

    core.titulo("[ CONFIGURACION DE CANTIDAD ]")
    bot.cantidad_mensajes = core.pedir_int("Cuantos mensajes enviar? (ENTER = 1)", defecto=1)

    core.titulo("[ TIEMPO DE BORRADO ]")
    seg = core.pedir_int("Segundos antes de borrar (0 = inmediato)", defecto=0)
    bot.delay_borrado = float(seg)

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
