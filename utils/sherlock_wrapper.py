import subprocess
import sys

def buscar_en_fuentes(username):
    try:
        comando = [
            sys.executable,
            "-m", "sherlock_project",
            username,
            "--print-found",
            "--no-color"
        ]

        resultado = subprocess.run(
            comando,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=300
        )

        if resultado.returncode != 0:
            raise RuntimeError(f"Sherlock error: {resultado.stderr}")

        salida = resultado.stdout.strip()
        if not salida:
            return []

        perfiles = []
        for linea in salida.splitlines():
            if ": https://" in linea:
                try:
                    fuente, url = linea.split(": https://", 1)
                    perfiles.append({
                        "fuente": fuente.strip(),
                        "url": f"https://{url.strip()}",
                        "contenido": url.strip(),
                        "origen": "sherlock"
                    })
                except Exception as e:
                    print(f"[ERROR] No se pudo parsear línea: {linea} – {e}")
        return perfiles

    except Exception as e:
        print(f"[ERROR] Sherlock falló: {e}")
        return [{
            "fuente": "simulado",
            "url": f"https://example.com/{username}",
            "contenido": f"{username} perfil simulado",
            "origen": "simulado"
        }]