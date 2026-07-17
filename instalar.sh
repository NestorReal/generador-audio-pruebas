#!/usr/bin/env bash
# instalar.sh — Verifica que todo esté listo (macOS) y hace una prueba.
#
# Este programa NO necesita instalar nada extra: usa la voz que ya trae macOS
# (comando `say`) y solo la librería estándar de Python. Este script únicamente
# confirma que todo funcione.
#
# Uso:  ./instalar.sh     (o:  bash instalar.sh)

set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

echo "=================================================="
echo "  Verificando el generador de audio (macOS)"
echo "=================================================="
echo

if [[ "$(uname)" != "Darwin" ]]; then
  echo "❌ Este script es para Mac. En Windows usa:  instalar.ps1"
  echo "   (clic derecho > Ejecutar con PowerShell, o vía la Terminal de Windows)."
  exit 1
fi
echo "✅ Sistema: macOS"

if command -v python3 >/dev/null 2>&1; then
  echo "✅ Python 3: $(python3 --version 2>&1)"
else
  echo "❌ No encuentro Python 3. Instálalo desde https://www.python.org/downloads/"
  exit 1
fi

if command -v say >/dev/null 2>&1; then
  echo "✅ Voz del sistema (say): disponible"
else
  echo "❌ No encuentro el comando 'say' (raro en una Mac)."
  exit 1
fi

echo
echo "==> Prueba rápida…"
if python3 generar_audio.py --texto "Prueba de instalación." \
     --salida _prueba --out-dir _prueba_tmp >/dev/null 2>&1; then
  fmt=$(python3 -c "import wave; w=wave.open('_prueba_tmp/_prueba.wav'); print(f'{w.getframerate()}Hz {w.getnchannels()}ch {w.getsampwidth()*8}bit')")
  rm -rf _prueba_tmp
  echo "✅ Prueba OK — audio generado en formato: $fmt"
else
  rm -rf _prueba_tmp
  echo "❌ La prueba falló."
  exit 1
fi

echo
echo "=================================================="
echo "  ✅ TODO LISTO"
echo "=================================================="
echo
echo "Ejemplos:"
echo '  python3 generar_audio.py --texto "Buenas tardes." --salida MI-AUDIO'
echo "  python3 generar_audio.py --lote guiones_ejemplo.csv"
echo "  python3 generar_audio.py --conversacion conversacion_ejemplo.csv --salida MI-LLAMADA"
echo
echo "Ver tus voces:  python3 generar_audio.py --listar-voces"
echo "Más detalles en LEEME.txt"
