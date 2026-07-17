#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generar_audio.py — Convierte texto en audio .wav.

Genera archivos WAV en formato PCM 16 kHz mono, usando la voz de macOS (`say`)
y ffmpeg.

Dos formas de usarlo:

1) UN audio:
     python3 generar_audio.py --texto "Buenas tardes, le confirmo su saldo." --salida MI-AUDIO

2) VARIOS audios desde un archivo CSV (columnas: nombre,texto):
     python3 generar_audio.py --lote guiones.csv

Requisitos: una Mac (comando `say`) + ffmpeg (instalar con:  brew install ffmpeg).

Autoría: herramienta interna de pruebas.
"""
from __future__ import annotations

import argparse
import csv
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _fail(msg: str) -> None:
    print(f"\n❌ {msg}\n", file=sys.stderr)
    sys.exit(1)


def revisar_requisitos() -> None:
    """Verifica que estén say + ffmpeg antes de empezar."""
    if platform.system() != "Darwin":
        _fail("Este programa usa el comando `say` de macOS y solo corre en una Mac.")
    if shutil.which("say") is None:
        _fail("No encuentro el comando `say` (¿estás en una Mac?).")
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        _fail("Falta ffmpeg. Instálalo abriendo la Terminal y escribiendo:\n"
              "      brew install ffmpeg\n"
              "   (si no tienes 'brew', instálalo primero desde https://brew.sh)")


def duracion(wav_path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(wav_path)],
        capture_output=True, text=True, check=True,
    )
    return round(float(out.stdout.strip() or 0), 1)


def sintetizar(texto: str, destino: Path, voz: str = "Paulina",
               volumen: float | None = None) -> float:
    """Sintetiza `texto` a un WAV/PCM 16 kHz mono. Devuelve la duración en segundos.

    volumen: factor 0-1 opcional (ej. 0.05 para simular un audio de mala calidad).
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tmp:
        tmp_aiff = Path(tmp.name)
    try:
        subprocess.run(["say", "-v", voz, "-o", str(tmp_aiff), texto], check=True)
        cmd = ["ffmpeg", "-y", "-i", str(tmp_aiff)]
        if volumen is not None:
            cmd += ["-af", f"volume={volumen}"]
        cmd += ["-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
                str(destino), "-loglevel", "error"]
        subprocess.run(cmd, check=True)
    finally:
        tmp_aiff.unlink(missing_ok=True)
    return duracion(destino)


def _nombre_wav(salida: str) -> str:
    base = salida[:-4] if salida.lower().endswith(".wav") else salida
    return base + ".wav"


def modo_uno(args: argparse.Namespace) -> None:
    wav = Path(args.out_dir) / _nombre_wav(args.salida)
    print(f"==> Generando audio con la voz «{args.voz}»…")
    d = sintetizar(args.texto, wav, voz=args.voz, volumen=args.volumen)
    print(f"\n✅ Listo: {wav}   ({d:.0f} segundos)")


def modo_lote(args: argparse.Namespace) -> None:
    """Genera todos los audios de un CSV con columnas: nombre, texto [, volumen]."""
    ruta = Path(args.lote)
    if not ruta.exists():
        _fail(f"No existe el archivo: {ruta}")

    with ruta.open(newline="", encoding="utf-8-sig") as f:
        filas = list(csv.DictReader(f))
    if not filas:
        _fail(f"El archivo {ruta} está vacío o sin encabezados.")

    # Acepta 'nombre' o 'call_id' como columna del nombre del archivo.
    cols = {c.strip().lower() for c in filas[0].keys()}
    col_nombre = "nombre" if "nombre" in cols else ("call_id" if "call_id" in cols else None)
    if col_nombre is None or "texto" not in cols:
        _fail("El CSV necesita al menos las columnas:  nombre,texto\n"
              "   (también acepta 'call_id' en vez de 'nombre').")

    out_dir = Path(args.out_dir)
    generados = 0
    print(f"==> Generando {len(filas)} audio(s) en la carpeta «{out_dir}»…\n")
    for fila in filas:
        row = {k.strip().lower(): (v or "").strip() for k, v in fila.items()}
        nombre = row.get(col_nombre, "")
        texto = row.get("texto", "")
        if not nombre or not texto:
            print(f"   ⚠️  fila incompleta, se omite: {fila}")
            continue
        vol = row.get("volumen") or None
        vol = float(vol) if vol else None
        wav = out_dir / _nombre_wav(nombre)
        d = sintetizar(texto, wav, voz=args.voz, volumen=vol)
        extra = f"  (volumen {vol})" if vol is not None else ""
        print(f"   ✓ {wav.name}   ({d:.0f}s){extra}")
        generados += 1

    if generados == 0:
        _fail("No se generó ningún audio (revisa el CSV).")
    print(f"\n✅ Listo: {generados} audio(s) en «{out_dir}».")


def main() -> None:
    p = argparse.ArgumentParser(
        description="Convierte texto en audio .wav (PCM 16 kHz mono).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--texto", help="El texto a convertir (para un solo audio).")
    p.add_argument("--salida", help="Nombre del archivo, sin .wav (para un solo audio).")
    p.add_argument("--lote", help="Archivo CSV con columnas nombre,texto[,volumen] (para varios).")
    p.add_argument("--out-dir", default="./audios",
                   help="Carpeta donde guardar los audios (por defecto: ./audios).")
    p.add_argument("--voz", default="Paulina",
                   help="Voz a usar (por defecto: Paulina, español México). "
                        "Ver otras:  say -v '?' | grep es_")
    p.add_argument("--volumen", type=float, default=None,
                   help="Factor de volumen 0-1 (ej. 0.05 para audio de baja calidad). Solo con --texto.")
    args = p.parse_args()

    revisar_requisitos()
    if args.lote:
        modo_lote(args)
    elif args.texto and args.salida:
        modo_uno(args)
    else:
        p.error("Usa  --texto y --salida  (un audio)  o  --lote archivo.csv  (varios).")


if __name__ == "__main__":
    main()
