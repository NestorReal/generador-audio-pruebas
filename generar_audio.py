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
import json
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Voces distintas que se reparten automáticamente entre los hablantes de una
# conversación (en orden de aparición). Todas verificadas en español.
VOCES_CONVERSACION = ["Paulina", "Juan", "Mónica", "Diego", "Jorge", "Reed"]


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


def _silencio(destino: Path, segundos: float) -> None:
    """Genera un WAV de silencio (mismo formato) para separar los turnos."""
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
         "-t", f"{segundos}", "-c:a", "pcm_s16le", str(destino), "-loglevel", "error"],
        check=True,
    )


def _parse_voces(spec: str | None) -> dict:
    """Convierte 'AGENTE=Paulina,CLIENTE=Juan' en un dict."""
    if not spec:
        return {}
    m = {}
    for par in spec.split(","):
        if "=" in par:
            k, v = par.split("=", 1)
            m[k.strip().upper()] = v.strip()
    return m


def modo_conversacion(args: argparse.Namespace) -> None:
    """Genera UN audio de conversación entre varios hablantes, cada uno con voz
    distinta, más un archivo de referencia (quién habló y en qué segundo).

    El CSV de entrada tiene columnas:  speaker,texto  (un renglón por turno).
    Ejemplo conversacion.csv:
        speaker,texto
        AGENTE,"Buenas tardes, le atiende Ana. ¿En qué le puedo ayudar?"
        CLIENTE,"Hola, quiero consultar el saldo de mi contrato."
        AGENTE,"Con gusto. Le confirmo que su saldo es de diez mil pesos."
    """
    ruta = Path(args.conversacion)
    if not ruta.exists():
        _fail(f"No existe el archivo: {ruta}")
    with ruta.open(newline="", encoding="utf-8-sig") as f:
        turnos = list(csv.DictReader(f))
    if not turnos:
        _fail(f"El archivo {ruta} está vacío o sin encabezados.")
    cols = {c.strip().lower() for c in turnos[0].keys()}
    if "speaker" not in cols or "texto" not in cols:
        _fail("El CSV de conversación necesita las columnas:  speaker,texto")

    if not args.salida:
        _fail("Falta --salida (nombre del audio de la conversación).")

    # Asigna una voz por hablante: primero lo que diga --voces, luego auto.
    voces_fijas = _parse_voces(args.voces_conv)
    asignacion: dict = {}
    libres = [v for v in VOCES_CONVERSACION if v not in voces_fijas.values()]
    idx = 0
    for t in turnos:
        spk = (t.get("speaker") or "").strip().upper()
        if not spk or spk in asignacion:
            continue
        if spk in voces_fijas:
            asignacion[spk] = voces_fijas[spk]
        else:
            asignacion[spk] = libres[idx % len(libres)] if libres else "Paulina"
            idx += 1

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    gap = args.pausa

    print(f"==> Generando conversación «{args.salida}» ({len(turnos)} turnos)")
    print(f"    Hablantes: " + ", ".join(f"{s}→{v}" for s, v in asignacion.items()))

    tmp = Path(tempfile.mkdtemp(prefix="conv_"))
    silencio = tmp / "_silencio.wav"
    _silencio(silencio, gap)

    lista = tmp / "lista.txt"
    referencia = []
    cursor = 0.0
    partes = []
    for i, t in enumerate(turnos, 1):
        row = {k.strip().lower(): (v or "").strip() for k, v in t.items()}
        spk = row["speaker"].strip().upper()
        texto = row["texto"]
        if not spk or not texto:
            continue
        voz = asignacion[spk]
        seg = tmp / f"turno_{i:03d}.wav"
        dur = sintetizar(texto, seg, voz=voz)
        inicio = round(cursor, 2)
        fin = round(cursor + dur, 2)
        referencia.append({
            "n": i, "speaker": spk, "voz": voz,
            "inicio_seg": inicio, "fin_seg": fin, "texto": texto,
        })
        partes.append(seg)
        cursor = fin + gap  # el silencio va después de cada turno

    # Arma el WAV final concatenando turno + silencio + turno + …
    with lista.open("w", encoding="utf-8") as f:
        for i, seg in enumerate(partes):
            f.write(f"file '{seg}'\n")
            if i < len(partes) - 1:
                f.write(f"file '{silencio}'\n")

    wav = out_dir / _nombre_wav(args.salida)
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lista),
         "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav), "-loglevel", "error"],
        check=True,
    )
    total = duracion(wav)

    # Referencia en JSON (ground truth para comparar con la diarización)
    ref_json = out_dir / f"{wav.stem}.referencia.json"
    ref_json.write_text(json.dumps({
        "audio": wav.name,
        "duracion_total_seg": total,
        "hablantes": asignacion,
        "turnos": referencia,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # Referencia legible en texto
    ref_txt = out_dir / f"{wav.stem}.referencia.txt"
    lineas = [f"Conversación: {wav.name}   ({total:.0f}s, {len(referencia)} turnos)",
              "Hablantes: " + ", ".join(f"{s} = voz {v}" for s, v in asignacion.items()), ""]
    for r in referencia:
        lineas.append(f"[{r['inicio_seg']:>6.2f}s - {r['fin_seg']:>6.2f}s]  {r['speaker']}: {r['texto']}")
    ref_txt.write_text("\n".join(lineas) + "\n", encoding="utf-8")

    shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n✅ Conversación lista: {wav}   ({total:.0f}s)")
    print(f"   Referencia (quién habló y cuándo):")
    print(f"     {ref_json.name}   (JSON, para comparar con la diarización)")
    print(f"     {ref_txt.name}    (texto legible)")


def main() -> None:
    p = argparse.ArgumentParser(
        description="Convierte texto en audio .wav (PCM 16 kHz mono).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--texto", help="El texto a convertir (para un solo audio).")
    p.add_argument("--salida", help="Nombre del archivo, sin .wav (para un solo audio).")
    p.add_argument("--lote", help="Archivo CSV con columnas nombre,texto[,volumen] (para varios).")
    p.add_argument("--conversacion", help="CSV con columnas speaker,texto: genera UNA conversación "
                                          "entre varios hablantes (voz distinta c/u) + su referencia. "
                                          "Requiere --salida.")
    p.add_argument("--voces-conv", help="Asignar voces a mano en conversación, ej: "
                                        "\"AGENTE=Paulina,CLIENTE=Juan\". Por defecto se reparten solas.")
    p.add_argument("--pausa", type=float, default=0.4,
                   help="Segundos de silencio entre turnos de la conversación (default: 0.4).")
    p.add_argument("--out-dir", default="./audios",
                   help="Carpeta donde guardar los audios (por defecto: ./audios).")
    p.add_argument("--voz", default="Paulina",
                   help="Voz a usar (por defecto: Paulina, español México). "
                        "Ver otras:  say -v '?' | grep es_")
    p.add_argument("--volumen", type=float, default=None,
                   help="Factor de volumen 0-1 (ej. 0.05 para audio de baja calidad). Solo con --texto.")
    args = p.parse_args()

    revisar_requisitos()
    if args.conversacion:
        modo_conversacion(args)
    elif args.lote:
        modo_lote(args)
    elif args.texto and args.salida:
        modo_uno(args)
    else:
        p.error("Elige un modo:\n"
                "  • un audio:      --texto \"...\" --salida NOMBRE\n"
                "  • varios:        --lote archivo.csv\n"
                "  • conversación:  --conversacion archivo.csv --salida NOMBRE")


if __name__ == "__main__":
    main()
