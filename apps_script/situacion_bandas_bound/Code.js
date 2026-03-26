const SHEET_MODEL_NAME = 'MODELO';
const BUTTON_CELL = 'H1';
const BUTTON_LABEL = 'ENVIAR';
const QUEUE_SHEET_NAME = '_ENVIO_COLA';
const OWNER_EMAIL = 'booking@artesbuhomanagement.com';
const BRAND_NAME = 'Artes Buho';
const FROM_REPLY_TO = 'booking@artesbuhomanagement.com';

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('SITUACION BANDAS')
    .addItem('Activar envio corporativo (1 vez)', 'activarEnvioCorporativo')
    .addItem('Preparar boton en hoja actual', 'prepararBotonHojaActual')
    .addSeparator()
    .addItem('Enviar hoja actual (cola)', 'enviarInformeDesdeBoton')
    .addItem('Procesar cola ahora', 'procesarColaAhora')
    .addToUi();
}

function activarEnvioCorporativo() {
  const user = Session.getActiveUser().getEmail();
  if (user && user.toLowerCase() !== OWNER_EMAIL.toLowerCase()) {
    throw new Error(
      'Esta activacion debe ejecutarse con la cuenta corporativa: ' + OWNER_EMAIL
    );
  }

  const ss = SpreadsheetApp.getActive();
  ensureQueueSheet_();
  deleteManagedTriggers_();

  ScriptApp.newTrigger('onEditRouter')
    .forSpreadsheet(ss)
    .onEdit()
    .create();

  ScriptApp.newTrigger('processQueueTick')
    .timeBased()
    .everyMinutes(1)
    .create();

  return {
    ok: true,
    message: 'Envio corporativo activado. Trigger onEdit + trigger cada minuto creados.',
    owner: OWNER_EMAIL,
  };
}

function prepararBotonHojaActual() {
  const sheet = SpreadsheetApp.getActiveSheet();
  if (sheet.getName().toUpperCase() === SHEET_MODEL_NAME) {
    throw new Error('MODELO no requiere boton.');
  }
  const rng = sheet.getRange(BUTTON_CELL);
  rng.setValue(BUTTON_LABEL);
  rng.setFontWeight('bold');
  rng.setBackground('#C62828');
  rng.setFontColor('#FFFFFF');
  rng.setHorizontalAlignment('center');
  rng.setNote(
    'Escribe ENVIAR y pulsa Enter. Se enviara desde la cuenta corporativa cuando la cola se procese.'
  );
  return { ok: true, sheet: sheet.getName(), cell: BUTTON_CELL };
}

function enviarInformeDesdeBoton() {
  const sheet = SpreadsheetApp.getActiveSheet();
  enqueueSheetSend_(sheet);
  return { ok: true, queued: true, sheet: sheet.getName() };
}

function onEditRouter(e) {
  if (!e || !e.range) {
    return;
  }
  const sheet = e.range.getSheet();
  if (sheet.getName().toUpperCase() === SHEET_MODEL_NAME) {
    return;
  }
  if (e.range.getA1Notation() !== BUTTON_CELL) {
    return;
  }

  const value = String(e.range.getValue() || '').trim().toUpperCase();
  if (value !== BUTTON_LABEL) {
    return;
  }

  enqueueSheetSend_(sheet);
  e.range.setValue('EN COLA');
}

function processQueueTick() {
  processQueue_();
}

function procesarColaAhora() {
  return processQueue_();
}

function processQueue_() {
  const queueSheet = ensureQueueSheet_();
  const lastRow = queueSheet.getLastRow();
  if (lastRow < 2) {
    return { ok: true, processed: 0, pending: 0 };
  }

  const rows = queueSheet.getRange(2, 1, lastRow - 1, 7).getValues();
  let processed = 0;
  let pending = 0;

  rows.forEach((row, idx) => {
    const rowNumber = idx + 2;
    const status = String(row[5] || '');
    if (status !== 'PENDING') {
      return;
    }
    pending++;
    const sheetName = String(row[2] || '');
    try {
      sendForSheetName_(sheetName);
      queueSheet.getRange(rowNumber, 6).setValue('SENT');
      queueSheet.getRange(rowNumber, 7).setValue(new Date());
      processed++;
    } catch (err) {
      queueSheet.getRange(rowNumber, 6).setValue('ERROR');
      queueSheet.getRange(rowNumber, 7).setValue(
        String(err && err.message ? err.message : err)
      );
    }
  });

  return { ok: true, processed: processed, pending: pending };
}

function sendForSheetName_(sheetName) {
  const ss = SpreadsheetApp.getActive();
  const sheet = ss.getSheetByName(sheetName);
  if (!sheet) {
    throw new Error('No existe hoja: ' + sheetName);
  }
  if (sheet.getName().toUpperCase() === SHEET_MODEL_NAME) {
    throw new Error('MODELO no se envia.');
  }

  const data = readBandPayload_(sheet);
  if (!data.to) {
    throw new Error('No hay correo destino en B2.');
  }
  GmailApp.sendEmail(data.to, data.subject, data.body, {
    name: BRAND_NAME,
    replyTo: FROM_REPLY_TO,
    noReply: false,
  });

  sheet.getRange('F2').setValue(new Date());
  sheet.getRange(BUTTON_CELL).setValue('ENVIADO');
  return { ok: true, to: data.to, subject: data.subject };
}

function enqueueSheetSend_(sheet) {
  const queue = ensureQueueSheet_();
  queue.appendRow([
    Utilities.getUuid(),
    new Date(),
    sheet.getName(),
    Session.getActiveUser().getEmail() || '',
    Session.getEffectiveUser().getEmail() || '',
    'PENDING',
    '',
  ]);
}

function readBandPayload_(sheet) {
  const banda = String(sheet.getRange('B1').getValue() || sheet.getName()).trim();
  const to = String(sheet.getRange('B2').getValue() || '').trim();
  const subject = String(
    sheet.getRange('B3').getValue() || ('Estado del proyecto: ' + banda)
  ).trim();
  const mensaje = String(sheet.getRange('B4').getValue() || '').trim();
  const obs = String(sheet.getRange('A14').getValue() || '').trim();

  const fases = [];
  for (let row = 7; row <= 11; row++) {
    const fase = String(sheet.getRange('A' + row).getValue() || '').trim();
    const estado = String(sheet.getRange('B' + row).getValue() || '').trim();
    if (fase) {
      fases.push(fase + ': ' + estado);
    }
  }

  const body =
    'Banda: ' + banda + '\n' +
    'Asunto operativo: ' + subject + '\n\n' +
    'Mensaje personalizado:\n' + (mensaje || '(sin mensaje)') + '\n\n' +
    'Estado por fases:\n- ' + fases.join('\n- ') + '\n\n' +
    'Observaciones:\n' + (obs || '(sin observaciones)') + '\n';

  return { to, subject, body, banda };
}

function ensureQueueSheet_() {
  const ss = SpreadsheetApp.getActive();
  let sheet = ss.getSheetByName(QUEUE_SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(QUEUE_SHEET_NAME);
    sheet.appendRow([
      'request_id',
      'created_at',
      'sheet_name',
      'requested_by',
      'effective_user',
      'status',
      'result',
    ]);
    sheet.hideSheet();
  }
  return sheet;
}

function deleteManagedTriggers_() {
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach((t) => {
    const handler = t.getHandlerFunction();
    if (handler === 'onEditRouter' || handler === 'processQueueTick') {
      ScriptApp.deleteTrigger(t);
    }
  });
}
