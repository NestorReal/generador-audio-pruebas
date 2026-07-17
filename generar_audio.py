#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generar_audio.py — Convierte texto en audio .wav (Mac y Windows).

Genera archivos WAV en formato PCM 16 kHz mono, que es lo que esperan los
pipelines de reconocimiento de voz.

Usa el sintetizador de voz que YA TRAE el sistema operativo:
  - macOS   -> el comando `say`
  - Windows -> System.Speech (SAPI) vía PowerShell

NO necesita instalar nada extra (ni ffmpeg): solo la librería estándar de Python.

Tres formas de usarlo:

1) UN audio:
     python generar_audio.py --texto "Buenas tardes, le confirmo su saldo." --salida MI-AUDIO

2) VARIOS audios desde un CSV (columnas: nombre,texto):
     python generar_audio.py --lote guiones.csv

3) Una CONVERSACION entre varias personas (voz distinta c/u), desde un CSV
   (columnas: speaker,texto), con archivo de referencia:
     python generar_audio.py --conversacion conversacion.csv --salida MI-LLAMADA

Ver las voces disponibles en tu equipo:
     python generar_audio.py --listar-voces
"""
from __future__ import annotations

import argparse
import array
import csv
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

SISTEMA = platform.system()          # 'Darwin' (Mac) | 'Windows' | 'Linux'
ES_MAC = SISTEMA == "Darwin"
ES_WIN = SISTEMA == "Windows"

# Formato de salida (lo que espera el pipeline)
RATE = 16000
ANCHO = 2      # bytes por muestra (16 bits)
CANALES = 1    # mono

# Voces que se reparten entre los hablantes de una conversación, por sistema.
# En Windows dependen de los paquetes de idioma instalados; se filtran contra
# las que de verdad existan (ver voces_disponibles()).
VOCES_MAC = ["Paulina", "Juan", "Mónica", "Diego", "Jorge", "Reed"]
VOCES_WIN = ["Microsoft Sabina Desktop", "Microsoft Raul Desktop",
             "Microsoft Helena Desktop", "Microsoft Pablo Desktop"]
VOZ_DEFECTO = "Paulina" if ES_MAC else ""   # "" = voz por defecto del sistema


def _fail(msg: str) -> None:
    print(f"\n❌ {msg}\n", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Requisitos
# ---------------------------------------------------------------------------

def revisar_requisitos() -> None:
    if ES_MAC:
        if shutil.which("say") is None:
            _fail("No encuentro el comando `say` (¿es una Mac?).")
    elif ES_WIN:
        if shutil.which("powershell") is None and shutil.which("pwsh") is None:
            _fail("No encuentro PowerShell, que se usa para la voz en Windows.")
    else:
        _fail("Este programa funciona en macOS y Windows.\n"
              "   En Linux no hay un sintetizador de voz integrado equivalente.")


def _powershell() -> str:
    return shutil.which("powershell") or shutil.which("pwsh") or "powershell"


# ---------------------------------------------------------------------------
# Síntesis de voz (una por sistema) -> WAV 16 kHz mono
# ---------------------------------------------------------------------------

def _sintetizar_mac(texto: str, destino: Path, voz: str) -> None:
    cmd = ["say"]
    if voz:
        cmd += ["-v", voz]
    cmd += ["-o", str(destino), "--data-format=LEI16@16000", "--file-format=WAVE", texto]
    subprocess.run(cmd, check=True)


# El texto, la voz y la ruta de salida se pasan por variables de entorno para
# evitar problemas de comillas/acentos. El script se escribe a un .ps1 temporal
# (más robusto que pasarlo en una sola línea con -Command).
_PS_SINTESIS = (
    "Add-Type -AssemblyName System.Speech\n"
    "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer\n"
    "if ($env:TTS_VOICE -and $env:TTS_VOICE.Trim() -ne '') {\n"
    "  try { $s.SelectVoice($env:TTS_VOICE) }\n"
    "  catch { Write-Error \"No se encontro la voz '$($env:TTS_VOICE)'. Usa --listar-voces.\"; exit 3 }\n"
    "}\n"
    "$bits = [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen\n"
    "$mono = [System.Speech.AudioFormat.AudioChannel]::Mono\n"
    "$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, $bits, $mono)\n"
    "$s.SetOutputToWaveFile($env:TTS_OUT, $fmt)\n"
    "$s.Speak($env:TTS_TEXT)\n"
    "$s.Dispose()\n"
)


def _correr_powershell(script: str, extra_env: dict | None = None) -> subprocess.CompletedProcess:
    """Escribe `script` a un .ps1 temporal y lo corre. Devuelve el CompletedProcess."""
    env = dict(os.environ, **(extra_env or {}))
    tmp = Path(tempfile.gettempdir()) / f"_tts_{os.getpid()}.ps1"
    tmp.write_text(script, encoding="utf-8")
    try:
        return subprocess.run(
            [_powershell(), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(tmp)],
            env=env, capture_output=True, text=True,
        )
    finally:
        tmp.unlink(missing_ok=True)


def _sintetizar_windows(texto: str, destino: Path, voz: str) -> None:
    r = _correr_powershell(_PS_SINTESIS,
                           {"TTS_TEXT": texto, "TTS_VOICE": voz or "", "TTS_OUT": str(destino)})
    if r.returncode != 0:
        _fail(f"Falló la síntesis de voz en Windows.\n   {r.stderr.strip()}")


def _aplicar_volumen(wav_path: Path, factor: float) -> None:
    """Escala el volumen de un WAV (solo stdlib). factor 0-1."""
    with wave.open(str(wav_path), "rb") as w:
        params = w.getparams()
        frames = w.readframes(w.getnframes())
    muestras = array.array("h")
    muestras.frombytes(frames)
    for i in range(len(muestras)):
        muestras[i] = max(-32768, min(32767, int(muestras[i] * factor)))
    with wave.open(str(wav_path), "wb") as w:
        w.setparams(params)
        w.writeframes(muestras.tobytes())


def sintetizar(texto: str, destino: Path, voz: str = "", volumen: float | None = None) -> float:
    """Sintetiza `texto` a un WAV 16 kHz mono en `destino`. Devuelve la duración (s)."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    if ES_MAC:
        _sintetizar_mac(texto, destino, voz)
    elif ES_WIN:
        _sintetizar_windows(texto, destino, voz)
    else:
        _fail("Sistema no soportado.")
    if volumen is not None:
        _aplicar_volumen(destino, volumen)
    return duracion(destino)


# ---------------------------------------------------------------------------
# Utilidades de audio (solo stdlib: módulo wave)
# ---------------------------------------------------------------------------

def duracion(wav_path: Path) -> float:
    with wave.open(str(wav_path), "rb") as w:
        return round(w.getnframes() / w.getframerate(), 1)


def _silencio(destino: Path, segundos: float) -> None:
    n = int(RATE * segundos)
    with wave.open(str(destino), "wb") as w:
        w.setnchannels(CANALES)
        w.setsampwidth(ANCHO)
        w.setframerate(RATE)
        w.writeframes(b"\x00" * (n * ANCHO * CANALES))


def _concatenar(secuencia: list[Path], destino: Path) -> None:
    """Une varios WAV (mismo formato) en uno solo."""
    with wave.open(str(destino), "wb") as out:
        out.setnchannels(CANALES)
        out.setsampwidth(ANCHO)
        out.setframerate(RATE)
        for parte in secuencia:
            with wave.open(str(parte), "rb") as w:
                out.writeframes(w.readframes(w.getnframes()))


# ---------------------------------------------------------------------------
# Voces disponibles
# ---------------------------------------------------------------------------

def voces_disponibles() -> list[str]:
    """Lista las voces instaladas en el sistema."""
    try:
        if ES_MAC:
            out = subprocess.run(["say", "-v", "?"], capture_output=True, text=True).stdout
            voces = []
            for linea in out.splitlines():
                # formato: "Paulina   es_MX   # ¡Hola!..."
                nombre = linea[:20].strip()
                if nombre:
                    voces.append(nombre)
            return voces
        elif ES_WIN:
            ps = ("Add-Type -AssemblyName System.Speech\n"
                  "(New-Object System.Speech.Synthesis.SpeechSynthesizer)."
                  "GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name }\n")
            out = _correr_powershell(ps).stdout
            return [l.strip() for l in out.splitlines() if l.strip()]
    except Exception:
        pass
    return []


def _voces_para_conversacion() -> list[str]:
    """Voces a repartir entre hablantes, filtradas a las que de verdad existen."""
    instaladas = voces_disponibles()
    preferidas = VOCES_MAC if ES_MAC else VOCES_WIN
    disponibles = [v for v in preferidas if v in instaladas]
    if disponibles:
        return disponibles
    # Fallback: usa lo que haya instalado (aunque sean pocas o en otro idioma).
    return instaladas or [""]


# ---------------------------------------------------------------------------
# Modos
# ---------------------------------------------------------------------------

def _nombre_wav(salida: str) -> str:
    base = salida[:-4] if salida.lower().endswith(".wav") else salida
    return base + ".wav"


def modo_uno(args: argparse.Namespace) -> None:
    wav = Path(args.out_dir) / _nombre_wav(args.salida)
    voz = args.voz if args.voz is not None else VOZ_DEFECTO
    print(f"==> Generando audio…")
    d = sintetizar(args.texto, wav, voz=voz, volumen=args.volumen)
    print(f"\n✅ Listo: {wav}   ({d:.0f} segundos)")


def modo_lote(args: argparse.Namespace) -> None:
    ruta = Path(args.lote)
    if not ruta.exists():
        _fail(f"No existe el archivo: {ruta}")
    with ruta.open(newline="", encoding="utf-8-sig") as f:
        filas = list(csv.DictReader(f))
    if not filas:
        _fail(f"El archivo {ruta} está vacío o sin encabezados.")
    cols = {c.strip().lower() for c in filas[0].keys()}
    col_nombre = "nombre" if "nombre" in cols else ("call_id" if "call_id" in cols else None)
    if col_nombre is None or "texto" not in cols:
        _fail("El CSV necesita las columnas:  nombre,texto  (o call_id,texto).")

    out_dir = Path(args.out_dir)
    voz = args.voz if args.voz is not None else VOZ_DEFECTO
    generados = 0
    print(f"==> Generando {len(filas)} audio(s) en «{out_dir}»…\n")
    for fila in filas:
        row = {k.strip().lower(): (v or "").strip() for k, v in fila.items()}
        nombre, texto = row.get(col_nombre, ""), row.get("texto", "")
        if not nombre or not texto:
            print(f"   ⚠️  fila incompleta, se omite: {fila}")
            continue
        vol = float(row["volumen"]) if row.get("volumen") else None
        wav = out_dir / _nombre_wav(nombre)
        d = sintetizar(texto, wav, voz=voz, volumen=vol)
        print(f"   ✓ {wav.name}   ({d:.0f}s)" + (f"  (volumen {vol})" if vol is not None else ""))
        generados += 1
    if generados == 0:
        _fail("No se generó ningún audio (revisa el CSV).")
    print(f"\n✅ Listo: {generados} audio(s) en «{out_dir}».")


def _parse_voces(spec: str | None) -> dict:
    if not spec:
        return {}
    m = {}
    for par in spec.split(","):
        if "=" in par:
            k, v = par.split("=", 1)
            m[k.strip().upper()] = v.strip()
    return m


def modo_conversacion(args: argparse.Namespace) -> None:
    ruta = Path(args.conversacion)
    if not ruta.exists():
        _fail(f"No existe el archivo: {ruta}")
    if not args.salida:
        _fail("Falta --salida (nombre del audio de la conversación).")
    with ruta.open(newline="", encoding="utf-8-sig") as f:
        turnos = list(csv.DictReader(f))
    if not turnos:
        _fail(f"El archivo {ruta} está vacío o sin encabezados.")
    cols = {c.strip().lower() for c in turnos[0].keys()}
    if "speaker" not in cols or "texto" not in cols:
        _fail("El CSV de conversación necesita las columnas:  speaker,texto")

    # Asignar una voz por hablante.
    voces_fijas = _parse_voces(args.voces_conv)
    pool = [v for v in _voces_para_conversacion() if v not in voces_fijas.values()] or [""]
    asignacion: dict = {}
    idx = 0
    for t in turnos:
        spk = (t.get("speaker") or "").strip().upper()
        if not spk or spk in asignacion:
            continue
        if spk in voces_fijas:
            asignacion[spk] = voces_fijas[spk]
        else:
            asignacion[spk] = pool[idx % len(pool)]
            idx += 1

    if len(set(asignacion.values())) == 1 and len(asignacion) > 1:
        print("   ⚠️  Solo hay una voz disponible: todos los hablantes sonarán igual.")
        if ES_WIN:
            print("       Para más voces, instala idiomas de voz en Windows: "
                  "Configuración > Hora e idioma > Voz.")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    gap = args.pausa
    print(f"==> Generando conversación «{args.salida}» ({len(turnos)} turnos)")
    print(f"    Hablantes: " + ", ".join(f"{s}→{v or 'voz por defecto'}" for s, v in asignacion.items()))

    tmp = Path(tempfile.mkdtemp(prefix="conv_"))
    silencio = tmp / "_sil.wav"
    _silencio(silencio, gap)

    referencia, partes, cursor = [], [], 0.0
    for i, t in enumerate(turnos, 1):
        row = {k.strip().lower(): (v or "").strip() for k, v in t.items()}
        spk, texto = row["speaker"].strip().upper(), row["texto"]
        if not spk or not texto:
            continue
        voz = asignacion[spk]
        seg = tmp / f"turno_{i:03d}.wav"
        dur = sintetizar(texto, seg, voz=voz)
        inicio, fin = round(cursor, 2), round(cursor + dur, 2)
        referencia.append({"n": i, "speaker": spk, "voz": voz or "(default)",
                           "inicio_seg": inicio, "fin_seg": fin, "texto": texto})
        partes.append(seg)
        cursor = fin + gap

    # Une turno + silencio + turno + …
    secuencia: list[Path] = []
    for i, seg in enumerate(partes):
        secuencia.append(seg)
        if i < len(partes) - 1:
            secuencia.append(silencio)
    wav = out_dir / _nombre_wav(args.salida)
    _concatenar(secuencia, wav)
    total = duracion(wav)

    ref_json = out_dir / f"{wav.stem}.referencia.json"
    ref_json.write_text(json.dumps({
        "audio": wav.name, "duracion_total_seg": total,
        "hablantes": asignacion, "turnos": referencia,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    ref_txt = out_dir / f"{wav.stem}.referencia.txt"
    lineas = [f"Conversación: {wav.name}   ({total:.0f}s, {len(referencia)} turnos)",
              "Hablantes: " + ", ".join(f"{s} = voz {v or 'default'}" for s, v in asignacion.items()), ""]
    for r in referencia:
        lineas.append(f"[{r['inicio_seg']:>6.2f}s - {r['fin_seg']:>6.2f}s]  {r['speaker']}: {r['texto']}")
    ref_txt.write_text("\n".join(lineas) + "\n", encoding="utf-8")

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n✅ Conversación lista: {wav}   ({total:.0f}s)")
    print(f"   Referencia: {ref_json.name} (JSON) y {ref_txt.name} (texto legible)")


def modo_listar_voces() -> None:
    voces = voces_disponibles()
    print(f"Sistema: {'macOS' if ES_MAC else 'Windows' if ES_WIN else SISTEMA}")
    if not voces:
        print("No pude listar las voces (o no hay ninguna instalada).")
        return
    print(f"Voces instaladas ({len(voces)}):")
    for v in voces:
        print(f"  - {v}")


# ---------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(
        description="Convierte texto en audio .wav (16 kHz mono). Mac y Windows.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--texto", help="El texto a convertir (un solo audio).")
    p.add_argument("--salida", help="Nombre del archivo, sin .wav (un audio o conversación).")
    p.add_argument("--lote", help="CSV con columnas nombre,texto[,volumen] (varios audios).")
    p.add_argument("--conversacion", help="CSV con columnas speaker,texto (una conversación).")
    p.add_argument("--voces-conv", help='Voces a mano en conversación, ej: "AGENTE=Paulina,CLIENTE=Juan".')
    p.add_argument("--pausa", type=float, default=0.4, help="Silencio entre turnos, en segundos (default 0.4).")
    p.add_argument("--out-dir", default="./audios", help="Carpeta de salida (default: ./audios).")
    p.add_argument("--voz", default=None, help="Voz a usar. Ver las tuyas con --listar-voces.")
    p.add_argument("--volumen", type=float, default=None,
                   help="Factor de volumen 0-1 (ej. 0.05 para audio de baja calidad). Solo con --texto.")
    p.add_argument("--listar-voces", action="store_true", help="Muestra las voces disponibles y sale.")
    args = p.parse_args()

    revisar_requisitos()
    if args.listar_voces:
        modo_listar_voces()
    elif args.conversacion:
        modo_conversacion(args)
    elif args.lote:
        modo_lote(args)
    elif args.texto and args.salida:
        modo_uno(args)
    else:
        p.error("Elige un modo:\n"
                "  • un audio:      --texto \"...\" --salida NOMBRE\n"
                "  • varios:        --lote archivo.csv\n"
                "  • conversación:  --conversacion archivo.csv --salida NOMBRE\n"
                "  • ver voces:     --listar-voces")


if __name__ == "__main__":
    main()
