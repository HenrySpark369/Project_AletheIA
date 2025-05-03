import subprocess
import sys
import os

def instalar_sherlock():
    print("[INFO] Sherlock no encontrado. Instalando desde GitHub...")
    subprocess.check_call([
        sys.executable,
        "-m", "pip",
        "install", "git+https://github.com/sherlock-project/sherlock.git"
    ])
    print("[INFO] Sherlock instalado correctamente.")

def encontrar_script_sherlock():
    base = os.path.join(sys.prefix, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages", "sherlock_project", "sherlock.py")
    return base if os.path.isfile(base) else None

def buscar_en_fuentes(username):
    try:
        ruta_script = encontrar_script_sherlock()
        if not ruta_script:
            instalar_sherlock()
            ruta_script = encontrar_script_sherlock()
            if not ruta_script:
                raise RuntimeError("Sherlock fue instalado pero no se encontró el script sherlock.py")

        resultado = subprocess.run(
            [sys.executable, ruta_script, username, "--print-found", "--no-color"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=300
        )

        if resultado.returncode != 0:
            raise RuntimeError(f"Sherlock error: {resultado.stderr.strip()}")

        perfiles = []
        for linea in resultado.stdout.strip().splitlines():
            if ": https://" in linea:
                fuente, url = linea.split(": https://", 1)
                perfiles.append({
                    "fuente": fuente.strip(),
                    "url": f"https://{url.strip()}",
                    "contenido": url.strip(),
                    "origen": "sherlock"
                })
        return perfiles

    except Exception as e:
        print(f"[ERROR] Sherlock falló: {e}")
        return [{
            "fuente": "simulado",
            "url": f"https://example.com/{username}",
            "contenido": f"{username} perfil simulado",
            "origen": "simulado"
        }]