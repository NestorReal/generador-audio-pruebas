# generador-audio-pruebas

Convierte texto en archivos de audio `.wav` para pruebas. Genera el formato que
esperan los pipelines de reconocimiento de voz: **WAV PCM, 16 kHz, mono**.

Usa la voz integrada de macOS (`say`) + `ffmpeg`. Solo librería estándar de Python,
sin dependencias de pip.

## Instalación

```bash
cd generador-audio-pruebas
./instalar.sh
```

El instalador revisa e instala lo que falte (ffmpeg) y hace una prueba al final.
Si prefieres a mano: necesitas macOS + `brew install ffmpeg`.

## Los tres modos

### 1. Un audio suelto

```bash
python3 generar_audio.py --texto "Buenas tardes, le confirmo su saldo." --salida MI-AUDIO
```
→ `audios/MI-AUDIO.wav`

### 2. Varios de un jalón (desde un CSV)

CSV con columnas `nombre,texto` (opcional `volumen`):

```csv
nombre,texto
AUDIO-1,"Buenas tardes, le confirmo que su contrato quedó activo."
AUDIO-2,"Le recuerdo que su estado de cuenta ya está disponible."
```

```bash
python3 generar_audio.py --lote guiones_ejemplo.csv
```
→ un `.wav` por renglón, en `audios/`.

### 3. Una conversación entre varias personas

Cada hablante sale con **una voz distinta**. CSV con columnas `speaker,texto`:

```csv
speaker,texto
AGENTE,"Buenas tardes, le atiende Ana. ¿En qué le ayudo?"
CLIENTE,"Hola, quiero consultar mi saldo."
AGENTE,"Su saldo es de diez mil pesos."
```

```bash
python3 generar_audio.py --conversacion conversacion_ejemplo.csv --salida MI-LLAMADA
```

Genera **tres archivos**:

| Archivo | Qué es |
|---|---|
| `MI-LLAMADA.wav` | La conversación completa, cada persona con su voz. |
| `MI-LLAMADA.referencia.txt` | Legible: quién habló, en qué segundo, y qué dijo. |
| `MI-LLAMADA.referencia.json` | Lo mismo en JSON — "ground truth" para comparar contra la separación de hablantes (diarización) del sistema. |

Ejemplo del `.referencia.txt`:

```
[  0.00s -   5.10s]  AGENTE: Buenas tardes, le atiende Ana Gómez...
[  5.50s -   9.30s]  CLIENTE: Hola, quiero consultar mi saldo.
[  9.70s -  13.90s]  AGENTE: Con gusto. Su saldo es de diez mil pesos.
```

## Opciones

| Opción | Para qué |
|---|---|
| `--out-dir CARPETA` | Guardar los audios en otra carpeta (default: `audios/`). |
| `--voz NOMBRE` | Cambiar la voz (default: `Paulina`, es_MX). Ver otras: `say -v '?' \| grep es_` |
| `--volumen 0.05` | Bajar el volumen para simular audio de mala calidad (solo con `--texto`). |
| `--voces-conv "AGENTE=Paulina,CLIENTE=Juan"` | Asignar voces a mano en la conversación. |
| `--pausa 0.6` | Segundos de silencio entre turnos de la conversación (default: 0.4). |

## Requisitos

- **macOS** (usa el comando `say`; en Windows/Linux no funciona tal cual).
- **ffmpeg** — `brew install ffmpeg`.
- **Python 3.8+** — las Macs ya lo traen. No requiere paquetes de pip.

## Archivos del proyecto

| Archivo | |
|---|---|
| `generar_audio.py` | El programa. |
| `instalar.sh` | Instala/verifica los requisitos y hace una prueba. |
| `LEEME.txt` | Instrucciones detalladas paso a paso. |
| `guiones_ejemplo.csv` | Plantilla para el modo "varios". |
| `conversacion_ejemplo.csv` | Plantilla para el modo "conversación". |
| `requirements.txt` | Nota sobre dependencias (no hay que instalar nada de pip). |

Detalles completos en [`LEEME.txt`](LEEME.txt).
