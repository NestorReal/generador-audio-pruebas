# generador-audio-pruebas

Convierte texto en archivos de audio `.wav` para pruebas. Genera el formato que
esperan los pipelines de reconocimiento de voz: **WAV PCM, 16 kHz, mono**.

**Funciona en macOS y en Windows.** Usa la voz que ya trae cada sistema
(`say` en Mac, System.Speech/SAPI en Windows) y solo la librería estándar de
Python — **no necesita instalar ffmpeg ni ningún paquete de pip**.

## Instalación / verificación

No hay que instalar nada extra: solo Python. Estos scripts lo confirman y hacen
una prueba:

- **macOS:** `./instalar.sh`
- **Windows:** `.\instalar.ps1` (en PowerShell)

Requisito único: **Python 3.8+**. En Mac ya viene; en Windows se instala desde
[python.org](https://www.python.org/downloads/) (marca *"Add Python to PATH"*).

## Los tres modos

> En **macOS** usa `python3`; en **Windows** usa `python`.

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

## Ver las voces de tu equipo

```bash
python3 generar_audio.py --listar-voces
```

En Windows, si solo hay una voz, todos los hablantes de una conversación sonarán
igual. Para agregar voces en español: *Configuración > Hora e idioma > Voz > Agregar voces*.

## Opciones

| Opción | Para qué |
|---|---|
| `--out-dir CARPETA` | Guardar los audios en otra carpeta (default: `audios/`). |
| `--voz NOMBRE` | Usar una voz específica (ver `--listar-voces`). |
| `--volumen 0.05` | Bajar el volumen para simular audio de mala calidad (solo con `--texto`). |
| `--voces-conv "AGENTE=Paulina,CLIENTE=Juan"` | Asignar voces a mano en la conversación. |
| `--pausa 0.6` | Segundos de silencio entre turnos (default: 0.4). |

## Requisitos

- **macOS o Windows.**
- **Python 3.8+** (Mac ya lo trae; Windows se instala de python.org).
- Nada más: sin ffmpeg, sin pip install.

Detalles completos en [`LEEME.txt`](LEEME.txt).
