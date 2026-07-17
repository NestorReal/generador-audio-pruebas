#!/usr/bin/env bash
# instalar.sh — Deja listo el generador de audio: revisa e instala lo que hace
# falta (ffmpeg) y hace una prueba para confirmar que todo funciona.
#
# Uso:  ./instalar.sh     (o:  bash instalar.sh)

set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

echo "=================================================="
echo "  Preparando el generador de audio de prueba"
echo "=================================================="
echo

falta=0

# 1) macOS ------------------------------------------------------------------
if [[ "$(uname)" != "Darwin" ]]; then
  echo "❌ Este programa solo funciona en Mac (usa la voz 'say' de macOS)."
  echo "   En Windows o Linux no se puede usar tal cual."
  exit 1
fi
echo "✅ Sistema: macOS"

# 2) Python 3 ---------------------------------------------------------------
if command -v python3 >/dev/null 2>&1; then
  echo "✅ Python 3: $(python3 --version 2>&1)"
else
  echo "❌ No encuentro Python 3."
  echo "   Instálalo desde:  https://www.python.org/downloads/"
  falta=1
fi

# 3) comando say (viene con macOS) ------------------------------------------
if command -v say >/dev/null 2>&1; then
  echo "✅ Voz del sistema (say): disponible"
else
  echo "❌ No encuentro el comando 'say' (raro en una Mac)."
  falta=1
fi

# 4) ffmpeg -----------------------------------------------------------------
if command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1; then
  echo "✅ ffmpeg: $(ffmpeg -version 2>/dev/null | head -1 | awk '{print $1, $3}')"
else
  echo "•  ffmpeg no está instalado. Intentando instalarlo…"
  if command -v brew >/dev/null 2>&1; then
    echo "   Ejecutando:  brew install ffmpeg"
    if brew install ffmpeg; then
      echo "✅ ffmpeg instalado."
    else
      echo "❌ No se pudo instalar ffmpeg con brew. Intenta a mano:  brew install ffmpeg"
      falta=1
    fi
  else
    echo "❌ No tienes 'brew' (Homebrew), que sirve para instalar ffmpeg."
    echo "   1) Instala Homebrew copiando esta línea en la Terminal:"
    echo '        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    echo "   2) Cierra y vuelve a abrir la Terminal."
    echo "   3) Vuelve a correr:  ./instalar.sh"
    falta=1
  fi
fi

if [[ "$falta" -ne 0 ]]; then
  echo
  echo "⚠️  Falta algo de lo de arriba. Resuélvelo y vuelve a correr ./instalar.sh"
  exit 1
fi

# 5) Prueba de humo ---------------------------------------------------------
echo
echo "==> Haciendo una prueba rápida…"
if python3 generar_audio.py --texto "Prueba de instalación correcta." \
     --salida _prueba_instalacion --out-dir _prueba_tmp >/dev/null 2>&1; then
  info=$(ffprobe -v error -show_entries stream=codec_name,sample_rate,channels \
         -of csv=p=0 _prueba_tmp/_prueba_instalacion.wav 2>/dev/null)
  rm -rf _prueba_tmp
  echo "✅ Prueba OK — se generó un audio en formato: $info"
else
  rm -rf _prueba_tmp
  echo "❌ La prueba falló. Revisa los mensajes de arriba."
  exit 1
fi

echo
echo "=================================================="
echo "  ✅ TODO LISTO"
echo "=================================================="
echo
echo "Ya puedes generar audios. Ejemplos:"
echo
echo "  • Un audio:"
echo '      python3 generar_audio.py --texto "Buenas tardes." --salida MI-AUDIO'
echo
echo "  • Varios desde un CSV (edita guiones_ejemplo.csv con tus textos):"
echo "      python3 generar_audio.py --lote guiones_ejemplo.csv"
echo
echo "Los audios quedan en la carpeta 'audios'. Más detalles en LEEME.txt"
