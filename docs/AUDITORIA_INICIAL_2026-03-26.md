# Auditoria inicial (2026-03-26)

## 1) Estado de partida del workspace

- No existia un proyecto Python/Streamlit previo para `SITUACION-BANDAS`.
- Se detectaron scripts y repos de otros proyectos (Apps Script, automatizaciones varias), sin una base reutilizable directa para este caso.

## 2) Validacion de la hoja fuente

- Google Sheet objetivo: `1YUOtxFLvryw_LmkoI2NB3FBeNucw0hFDdQa2qflr-xs`.
- Se confirmo export publico `.xlsx` operativo.
- Estructura detectada: 19 hojas.
- Hojas: `MODELO` + 18 operativas (`LYDIA MARTIN`, `LINZE`, ... `Noiah`).

## 3) Validacion de layout observado

En muestra representativa:

- `A1`: `NOMBRE BANDA`
- `B1/C1`: nombre banda
- `A2`: `CORREO`
- `B2/C2`: correo
- `A3`: `ASUNTO`
- `B3/C3`: asunto
- `E2/F2`: ultimo envio
- `A7:A11`: fases
- `B7:B11`: estados
- `A14:F17`: observaciones

## 4) Estados detectados

- `CRITICO`
- `EN PROCESO`
- `OPTIMO`

## 5) Drive API sobre el file ID

- Con los perfiles OAuth locales auditados, no hay acceso Drive API al file ID (`404`).
- Consecuencia: el codigo implementa la capa Drive completa, pero en este entorno no puede crear/verificar carpetas en el parent real hasta disponer de credencial con permiso sobre esa sheet.

## 6) Decision tecnica aplicada

- Ingesta principal implementada con `export xlsx` (Google Sheet real) + parser robusto.
- Capa Drive implementada y activable con credenciales validas sin rediseñar arquitectura.
