# generador-audio-pruebas

Convierte texto en archivos de audio `.wav` para pruebas. Genera el formato que
esperan los pipelines de reconocimiento de voz: **WAV PCM, 16 kHz, mono**.

Usa la voz integrada de macOS (`say`) + `ffmpeg`.

## Instalación

```bash
cd generador-audio-pruebas
./instalar.sh
```

El instalador revisa e instala lo que falte (ffmpeg) y hace una prueba al final.

## Uso

**Un audio:**
```bash
python3 generar_audio.py --texto "Buenas tardes, le confirmo su saldo." --salida MI-AUDIO
```

**Varios de un jalón** desde un CSV con columnas `nombre,texto`:
```bash
python3 generar_audio.py --lote guiones_ejemplo.csv
```

Los audios quedan en la carpeta `audios/`.

## Requisitos

- macOS (usa el comando `say`).
- ffmpeg — `brew install ffmpeg`.
- Python 3.8+ (las Macs ya lo traen). No requiere paquetes de pip.

Detalles completos en [`LEEME.txt`](LEEME.txt).
