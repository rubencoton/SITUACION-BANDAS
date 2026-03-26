# SITUACION-BANDAS

Sistema de cuadro de mando + informes corporativos PDF para **SITUACION BANDAS** (Artes Buho), con arquitectura de coste 0 EUR, automatizable y mantenible.

## Objetivo

- Leer la Google Sheet operativa como **fuente principal**.
- Normalizar datos por banda y fases.
- Calcular metricas y ranking.
- Generar informes PDF corporativos (semanal, mensual, anual).
- Guardar snapshots historicos para comparativas.
- Subir informes a Drive en estructura `Informes/*` cuando haya permisos API.
- Dejar modulo de correo listo en `dry-run` (sin envio real por defecto).

## Fuente principal

- Google Sheet ID: `1YUOtxFLvryw_LmkoI2NB3FBeNucw0hFDdQa2qflr-xs`
- URL: <https://docs.google.com/spreadsheets/d/1YUOtxFLvryw_LmkoI2NB3FBeNucw0hFDdQa2qflr-xs/edit>

## Arquitectura

- `src/sheets_reader.py`: descarga y parsing robusto (coordenadas + fallback semantico).
- `src/data_model.py`: normalizacion de estados/fases y scoring.
- `src/analytics.py`: KPIs, distribuciones, ranking, heatmap y detalle operativo.
- `src/insights.py`: insights ejecutivos basados en datos.
- `src/reports/*`: naming, scheduler Europe/Madrid, graficos, PDF y uploader Drive.
- `src/emailing/*`: preview + envio manual con provider abstraction y guardas de seguridad.
- `src/pipeline.py`: orquestacion unica para scripts, UI y automatizaciones.
- `app.py`: dashboard Streamlit reutilizando la misma logica.

Auditoria de partida: `docs/AUDITORIA_INICIAL_2026-03-26.md`.

## Estructura de carpetas Drive (objetivo)

Se intenta resolver automaticamente la carpeta padre de la Sheet y crear/reusar:

```text
Informes/
  InformeSemanal/
  InformeMensual/
  InformeAnual/
```

Reglas implementadas:

- Si no existe `Informes`, se crea.
- Si faltan subcarpetas, se crean.
- Si existen, se reutilizan.
- No se suben PDFs duplicados si ya existe el mismo nombre.

> Nota: si las credenciales actuales no tienen permisos sobre el file ID de la Sheet en Drive API, el sistema sigue funcionando en local y deja logs claros para activacion posterior.

## Naming y periodos (implementados)

- Semanal (lunes 08:00 Europe/Madrid): `YYMMDD_InformeSemanal.pdf`
- Mensual (dia 1 08:00 Europe/Madrid, mes anterior): `YYMM_InformeMensual.pdf`
- Anual (1 enero 08:00 Europe/Madrid, año anterior): `YYYY_InformeAnual.pdf`

Funciones:

- `src/reports/naming.py`
- `src/reports/scheduler.py`

Con tests para bordes de calendario y horario.

## Historico y comparativa

- Snapshots guardados en `data/history/`.
- Indice en `data/history/snapshots_index.json`.
- Cada informe guarda snapshot normalizado con KPIs, bandas y fases.
- Comparativa contra el ultimo informe equivalente si existe.
- Si no hay historial, se informa elegantemente en insights.

## Correo (preparado, desactivado por defecto)

- Remitente esperado: `booking@artesbuhomanagement.com`
- Provider abstraction en `src/emailing/sender.py`
- Preview: `scripts/preview_email.py`
- Envio manual: `scripts/send_email.py`
- Seguridad:
  - `EMAIL_ENABLED=false` por defecto
  - `EMAIL_DRY_RUN_DEFAULT=true`
  - `--confirm-live` obligatorio para live
  - sin credenciales hardcodeadas

## Instalacion local

1. Crear entorno:

```bash
python -m venv .venv
source .venv/bin/activate  # en Windows: .venv\\Scripts\\activate
```

2. Instalar dependencias:

```bash
pip install -e .[dev]
```

3. Configurar entorno:

```bash
cp .env.example .env
```

4. Ajustar credenciales en `.env` segun disponibilidad.

## Ejecucion manual

- Dashboard:

```bash
streamlit run app.py
```

- Informe semanal:

```bash
python scripts/generate_weekly_report.py
```

- Informe mensual:

```bash
python scripts/generate_monthly_report.py
```

- Informe anual:

```bash
python scripts/generate_annual_report.py
```

- Generar todos los pendientes segun horario local Europe/Madrid:

```bash
python scripts/run_due_reports.py
```

- Generar todos los tipos pendientes por idempotencia (semanal, mensual, anual):

```bash
python scripts/generate_pending_reports.py
```

- Preview de correo:

```bash
python scripts/preview_email.py
```

- Envio manual (por defecto dry-run):

```bash
python scripts/send_email.py --dry-run
```

- Envio real (solo cuando se habilite):

```bash
python scripts/send_email.py --live --confirm-live
```

## GitHub Actions

- `ci.yml`: lint/test base con `pytest`.
- `reports_scheduler.yml`: cron cada 30 min; el script decide si toca por Europe/Madrid y evita duplicados.
- `manual_run.yml`: ejecucion manual on-demand de informe semanal/mensual/anual.

## Seguridad

- Secretos fuera del codigo.
- `.env` excluido por `.gitignore`.
- Soporte para:
  - service account JSON
  - OAuth user JSON
  - perfil `.clasprc` (si aplica)

## Estado operativo esperado

Con credenciales validas:

- lectura Google Sheet
- normalizacion de bandas y fases
- calculo de score y KPIs
- generacion PDF corporativo
- subida idempotente a Drive en estructura `Informes/*`
- snapshots historicos y comparativas
- correo en dry-run y live con guardas
