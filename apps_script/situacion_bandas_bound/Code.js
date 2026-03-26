const SHEET_MODEL_NAME = 'MODELO';
const BUTTON_CELL = 'H1';
const BUTTON_LABEL = 'ENVIAR';
const QUEUE_SHEET_NAME = '_ENVIO_COLA';
const OWNER_EMAIL = 'booking@artesbuhomanagement.com';
const BRAND_NAME = 'Artes Buho';
const FROM_REPLY_TO = 'booking@artesbuhomanagement.com';
const STATIC_SHEET_ID = '1YUOtxFLvryw_LmkoI2NB3FBeNucw0hFDdQa2qflr-xs';
const STATIC_ADMIN_KEY = 'ACTIVA_49a6e7e192d14f0e851e';

function doGet(e) {
  return routeWebRequest_(e);
}

function doPost(e) {
  return routeWebRequest_(e);
}

function routeWebRequest_(e) {
  try {
    const request = parseWebRequest_(e);
    verifyAdminKey_(request.adminKey);
    const ss = getSpreadsheet_();

    if (request.action === 'status') {
      const pending = getPendingCount_(ss);
      return jsonOutput_({
        ok: true,
        action: 'status',
        spreadsheetId: ss.getId(),
        pending: pending,
      });
    }

    if (request.action === 'mail_health') {
      return jsonOutput_({
        ok: true,
        action: 'mail_health',
        remainingDailyQuota: MailApp.getRemainingDailyQuota(),
      });
    }

    if (request.action === 'debug') {
      return jsonOutput_({
        ok: true,
        action: 'debug',
        spreadsheetConfigured: Boolean(
          STATIC_SHEET_ID && !/^__.*__$/.test(STATIC_SHEET_ID)
        ),
        spreadsheetId: STATIC_SHEET_ID,
        adminConfigured: Boolean(
          STATIC_ADMIN_KEY && !/^__.*__$/.test(STATIC_ADMIN_KEY)
        ),
        adminKeyPrefix: STATIC_ADMIN_KEY ? String(STATIC_ADMIN_KEY).slice(0, 8) : '',
      });
    }

    if (request.action === 'activate') {
      const res = activateEnvioCorporativoInternal_(ss);
      return jsonOutput_({ ok: true, action: 'activate', result: res });
    }

    if (request.action === 'prepare_all') {
      const res = prepararBotonesTodasLasBandas_(ss);
      return jsonOutput_({ ok: true, action: 'prepare_all', result: res });
    }

    if (request.action === 'activate_prepare') {
      const r1 = activateEnvioCorporativoInternal_(ss);
      const r2 = prepararBotonesTodasLasBandas_(ss);
      return jsonOutput_({
        ok: true,
        action: 'activate_prepare',
        activation: r1,
        prepared: r2,
      });
    }

    if (request.action === 'process_queue') {
      const res = processQueue_(ss);
      return jsonOutput_({ ok: true, action: 'process_queue', result: res });
    }

    return jsonOutput_({ ok: false, error: 'unknown_action' });
  } catch (err) {
    return jsonOutput_({
      ok: false,
      error: 'web_router_exception',
      message: String(err && err.message ? err.message : err),
    });
  }
}

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('SITUACION BANDAS')
    .addItem('Activar envio corporativo (1 vez)', 'activarEnvioCorporativo')
    .addItem('Preparar boton en hoja actual', 'prepararBotonHojaActual')
    .addItem('Preparar botones en todas las hojas', 'prepararBotonesTodasLasBandas')
    .addSeparator()
    .addItem('Enviar hoja actual (cola)', 'enviarInformeDesdeBoton')
    .addItem('Procesar cola ahora', 'procesarColaAhora')
    .addToUi();
}

function activarEnvioCorporativo() {
  const ss = getSpreadsheet_();
  return activateEnvioCorporativoInternal_(ss);
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

function prepararBotonesTodasLasBandas() {
  const ss = getSpreadsheet_();
  return prepararBotonesTodasLasBandas_(ss);
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
  const ss = getSpreadsheet_();
  processQueue_(ss);
}

function procesarColaAhora() {
  const ss = getSpreadsheet_();
  return processQueue_(ss);
}

function processQueue_(ss) {
  const targetSs = ss || getSpreadsheet_();
  const queueSheet = ensureQueueSheet_(targetSs);
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
      sendForSheetName_(sheetName, targetSs);
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
  const ss = getSpreadsheet_();
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
  const queue = ensureQueueSheet_(sheet.getParent());
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

function ensureQueueSheet_(ss) {
  const targetSs = ss || getSpreadsheet_();
  let sheet = targetSs.getSheetByName(QUEUE_SHEET_NAME);
  if (!sheet) {
    sheet = targetSs.insertSheet(QUEUE_SHEET_NAME);
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

function prepareButtonForSheet_(sheet) {
  if (!sheet) {
    return;
  }
  const name = String(sheet.getName() || '').toUpperCase();
  if (name === SHEET_MODEL_NAME || name === QUEUE_SHEET_NAME) {
    return;
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
}

function prepararBotonesTodasLasBandas_(ss) {
  const targetSs = ss || getSpreadsheet_();
  const sheets = targetSs.getSheets();
  let total = 0;
  sheets.forEach((s) => {
    const n = String(s.getName() || '').toUpperCase();
    if (n === SHEET_MODEL_NAME || n === QUEUE_SHEET_NAME) {
      return;
    }
    prepareButtonForSheet_(s);
    total++;
  });
  return { ok: true, preparedSheets: total };
}

function activateEnvioCorporativoInternal_(ss) {
  const targetSs = ss || getSpreadsheet_();
  ensureQueueSheet_(targetSs);
  deleteManagedTriggers_();

  ScriptApp.newTrigger('onEditRouter')
    .forSpreadsheet(targetSs)
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
    spreadsheetId: targetSs.getId(),
  };
}

function getSpreadsheet_() {
  if (STATIC_SHEET_ID && !/^__.*__$/.test(STATIC_SHEET_ID)) {
    return SpreadsheetApp.openById(STATIC_SHEET_ID);
  }
  const active = SpreadsheetApp.getActive();
  if (!active) {
    throw new Error('No hay spreadsheet activo disponible.');
  }
  return active;
}

function getPendingCount_(ss) {
  const queue = ensureQueueSheet_(ss);
  const lastRow = queue.getLastRow();
  if (lastRow < 2) {
    return 0;
  }
  const values = queue.getRange(2, 6, lastRow - 1, 1).getValues();
  let pending = 0;
  values.forEach((v) => {
    if (String(v[0] || '') === 'PENDING') {
      pending++;
    }
  });
  return pending;
}

function parseWebRequest_(e) {
  const action = e && e.parameter ? String(e.parameter.action || '').trim() : '';
  let adminKey = e && e.parameter ? String(e.parameter.key || '') : '';
  if (e && e.postData && e.postData.contents) {
    try {
      const body = JSON.parse(e.postData.contents);
      if (!adminKey && body && body.key) {
        adminKey = String(body.key);
      }
    } catch (err) {}
  }
  return { action: action || 'status', adminKey: adminKey };
}

function verifyAdminKey_(incoming) {
  const key = String(incoming || '');
  if (!STATIC_ADMIN_KEY || /^__.*__$/.test(STATIC_ADMIN_KEY)) {
    throw new Error('Admin key no configurada.');
  }
  if (key !== STATIC_ADMIN_KEY) {
    throw new Error('Admin key invalida.');
  }
}

function jsonOutput_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
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
