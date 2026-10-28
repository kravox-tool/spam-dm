import sys
import time
import subprocess

# ---------- Paleta ROJA ----------
ROJO        = "\033[1;38;5;196m"
ROJO_CLARO  = "\033[38;5;203m"
ROJO_OSCURO = "\033[38;5;160m"
RED     = ROJO
GREEN   = ROJO_CLARO
YELLOW  = ROJO_OSCURO
CYAN    = ROJO
WHITE   = ROJO
GRAY    = ROJO_OSCURO
BOLD    = "\033[1m"
RESET   = "\033[0m"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOTS_DIR = os.path.join(BASE_DIR, "bots")
ANCHO = 66

BANNER_LINES = [
    "██████╗ ███╗   ███╗      ███████╗██████╗  █████╗ ███╗   ███╗",
    "██╔══██╗████╗ ████║      ██╔════╝██╔══██╗██╔══██╗████╗ ████║",
    "██║  ██║██╔████╔██║█████╗███████╗██████╔╝███████║██╔████╔██║",
    "██║  ██║██║╚██╔╝██║╚════╝╚════██║██╔═══╝ ██╔══██║██║╚██╔╝██║",
    "██████╔╝██║ ╚═╝ ██║      ███████║██║     ██║  ██║██║ ╚═╝ ██║",
    "╚═════╝ ╚═╝     ╚═╝      ╚══════╝╚═╝     ╚═╝  ╚═╝╚═╝     ╚═╝",
]


def neon(texto):
    if not texto:
        return ""
    return f"{ROJO}{texto}{RESET}"


def limpiar():
    os.system("clear")


def banner():
    print(f"{ROJO}{BOLD}")
    for linea in BANNER_LINES:
        print(linea)
    print(RESET)


def barra(texto=""):
    print(f"{ROJO}{BOLD}" + "=" * ANCHO + f"{RESET}")
    if texto:
        print(f"{ROJO_CLARO}{BOLD}{texto.center(ANCHO)}{RESET}")
        print(f"{ROJO}{BOLD}" + "=" * ANCHO + f"{RESET}")


def encabezado():
    limpiar()
    banner()
    barra("TERMUX PANEL")
    print()


def pausa():
    input(f"\n{ROJO_OSCURO}Presiona ENTER para volver al panel...{RESET}")


def menu():
    print(f" {ROJO}{BOLD}[1]{RESET}  {ROJO}{BOLD}DM-SPAM{RESET}   {ROJO_CLARO}rafaga de mensajes directos a una ID{RESET}")
    print(f" {ROJO}{BOLD}[2]{RESET}  {ROJO}{BOLD}CHAT{RESET}      {ROJO_CLARO}chat en vivo por consola con una ID{RESET}")
    print(f" {ROJO}{BOLD}[3]{RESET}  {ROJO}{BOLD}MASIVO{RESET}    {ROJO_CLARO}mensaje x veces a todos los usuarios del servidor{RESET}")
    print(f" {ROJO}{BOLD}[4]{RESET}  {ROJO}{BOLD}FLASH{RESET}     {ROJO_CLARO}enviar a usuario o servidor y borrar rapido{RESET}")
    print(f" {ROJO}{BOLD}[5]{RESET}  {ROJO}{BOLD}INFO{RESET}      {ROJO_CLARO}requisitos, token e intents necesarios{RESET}")
    print(f" {ROJO}{BOLD}[0]{RESET}  {ROJO}{BOLD}SALIR{RESET}     {ROJO_CLARO}cerrar el lanzador{RESET}")
    print()


def lanzar_script(nombre):
    ruta = os.path.join(BOTS_DIR, nombre)
    if not os.path.isfile(ruta):
        print(f"\n{ROJO}[X] Script no encontrado: {ruta}{RESET}")
        pausa()
        return
    try:
        subprocess.run([sys.executable, ruta], cwd=BASE_DIR)
    except KeyboardInterrupt:
        pass
    pausa()


def pantalla_info():
    limpiar()
    banner()
    barra("INFORMACION / REQUISITOS")
    print(f"""
 {ROJO}{BOLD}FUNCIONES DEL PANEL{RESET}
   {ROJO_OSCURO}-{RESET} DM-SPAM  rafaga de DMs a una ID
   {ROJO_OSCURO}-{RESET} CHAT     chat en vivo por consola con una ID
   {ROJO_OSCURO}-{RESET} MASIVO   mensaje x veces a todos los usuarios de un servidor
   {ROJO_OSCURO}-{RESET} FLASH    enviar a un usuario o servidor y borrar rapido

 {ROJO}{BOLD}REQUISITOS{RESET}
   {ROJO_OSCURO}-{RESET} Termux actualizado
   {ROJO_OSCURO}-{RESET} Python 3.10 o superior
   {ROJO_OSCURO}-{RESET} discord.py >= 2.3.2
   {ROJO_OSCURO}-{RESET} prompt_toolkit >= 3.0.43

 {ROJO}{BOLD}INSTALACION{RESET}
   {ROJO_CLARO}bash setup.sh{RESET}

 {ROJO}{BOLD}COMO OBTENER EL TOKEN{RESET}
   {ROJO_OSCURO}-{RESET} Entra a https://discord.com/developers/applications
   {ROJO_OSCURO}-{RESET} New Application > Bot > Reset Token > Copia el token

 {ROJO}{BOLD}INTENTS NECESARIOS (activalos en el portal){RESET}
   {ROJO_OSCURO}-{RESET} Presence Intent
   {ROJO_OSCURO}-{RESET} Server Members Intent
   {ROJO_OSCURO}-{RESET} Message Content Intent

 {ROJO}{BOLD}COMO OBTENER UNA ID{RESET}
   {ROJO_OSCURO}-{RESET} Ajustes de Discord > Avanzado > Modo desarrollador
   {ROJO_OSCURO}-{RESET} Clic derecho sobre el usuario > Copiar ID

 {ROJO}{BOLD}SALIR DESDE ADENTRO DE UNA FUNCION{RESET}
   {ROJO_OSCURO}-{RESET} Escribe 'salir' en la consola para volver al panel
   {ROJO_OSCURO}-{RESET} En Discord usa .salir o .exit
""")
    pausa()


def main():
    while True:
        encabezado()
        menu()
        opcion = input(f"{ROJO}{BOLD}-> Elige una opcion: {RESET}").strip()

        if opcion == "1":
            lanzar_script("dmspam.py")
        elif opcion == "2":
            lanzar_script("chat.py")
        elif opcion == "3":
            lanzar_script("masivo.py")
        elif opcion == "4":
            lanzar_script("flash.py")
        elif opcion == "5":
            pantalla_info()
        elif opcion == "0":
            limpiar()
            banner()
            barra()
            print(f"\n{ROJO_CLARO}[-] Saliendo del panel...{RESET}\n")
            break
        else:
            print(f"\n{ROJO_CLARO}[!] Opcion invalida. Usa 1, 2, 3, 4, 5 o 0.{RESET}")
            time.sleep(1.2)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{ROJO}[-] Panel cerrado por el usuario.{RESET}")
