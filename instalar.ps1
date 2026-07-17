# instalar.ps1 — Verifica que todo esté listo (Windows) y hace una prueba.
#
# Este programa NO necesita instalar nada extra: usa la voz que ya trae Windows
# (System.Speech / SAPI) y solo la librería estándar de Python. Este script
# únicamente confirma que todo funcione.
#
# Cómo correrlo:
#   1) Abre PowerShell en esta carpeta (clic derecho en la carpeta con Shift >
#      "Abrir ventana de PowerShell aquí"), o abre PowerShell y usa `cd`.
#   2) Escribe:   .\instalar.ps1
#   Si te dice que la ejecución de scripts está deshabilitada, corre primero:
#      Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

Write-Host "=================================================="
Write-Host "  Verificando el generador de audio (Windows)"
Write-Host "=================================================="
Write-Host ""

# Python
$python = $null
foreach ($cmd in @("python", "python3", "py")) {
  if (Get-Command $cmd -ErrorAction SilentlyContinue) { $python = $cmd; break }
}
if (-not $python) {
  Write-Host "X  No encuentro Python. Instalalo desde https://www.python.org/downloads/"
  Write-Host "   (marca la casilla 'Add Python to PATH' durante la instalacion)."
  exit 1
}
Write-Host "OK  Python: $(& $python --version)"

# Voz del sistema (SAPI)
try {
  Add-Type -AssemblyName System.Speech
  $n = (New-Object System.Speech.Synthesis.SpeechSynthesizer).GetInstalledVoices().Count
  Write-Host "OK  Voz del sistema (SAPI): $n voz(ces) instalada(s)"
} catch {
  Write-Host "X  No pude usar la voz del sistema (System.Speech)."
  exit 1
}

# Prueba
Write-Host ""
Write-Host "==> Prueba rapida..."
& $python generar_audio.py --texto "Prueba de instalacion." --salida _prueba --out-dir _prueba_tmp | Out-Null
if (Test-Path "_prueba_tmp\_prueba.wav") {
  Remove-Item -Recurse -Force _prueba_tmp
  Write-Host "OK  Prueba correcta: se genero un audio."
} else {
  if (Test-Path "_prueba_tmp") { Remove-Item -Recurse -Force _prueba_tmp }
  Write-Host "X  La prueba fallo."
  exit 1
}

Write-Host ""
Write-Host "=================================================="
Write-Host "  TODO LISTO"
Write-Host "=================================================="
Write-Host ""
Write-Host "Ejemplos:"
Write-Host '  python generar_audio.py --texto "Buenas tardes." --salida MI-AUDIO'
Write-Host "  python generar_audio.py --lote guiones_ejemplo.csv"
Write-Host "  python generar_audio.py --conversacion conversacion_ejemplo.csv --salida MI-LLAMADA"
Write-Host ""
Write-Host "Ver tus voces:  python generar_audio.py --listar-voces"
Write-Host ""
Write-Host "NOTA: si al hacer una conversacion todos suenan igual, es que Windows"
Write-Host "solo tiene una voz. Para agregar voces en espanol ve a:"
Write-Host "  Configuracion > Hora e idioma > Voz > Agregar voces."
