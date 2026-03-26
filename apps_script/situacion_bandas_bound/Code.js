const SHEET_MODEL_NAME = 'MODELO';
const BUTTON_CELL = 'H1';
const BUTTON_LABEL = 'ENVIAR';
const BUTTON_QUEUED_LABEL = 'EN COLA';
const BUTTON_CANCELLED_LABEL = 'CANCELADO';
const BUTTON_PENDING_CONFIRM_LABEL = 'PENDIENTE_CONFIRMACION';
const BUTTON_SENT_LABEL = 'ENVIADO';
const QUEUE_SHEET_NAME = '_ENVIO_COLA';
const QUEUE_STATUS_PENDING = 'PENDING';
const QUEUE_STATUS_SENT = 'SENT';
const QUEUE_STATUS_ERROR = 'ERROR';
const QUEUE_MAX_SENDS_PER_TICK = 20;
const QUEUE_REQUESTED_BY = 'manual_or_trigger';
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
    .addItem('ENVIAR (con confirmacion)', 'enviarHojaActualConConfirmacion')
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
  applyButtonStyle_(rng);
  rng.setNote(
    'Pulsa ENVIAR y confirma en la ventana emergente. Si no aparece popup, usa menu SITUACION BANDAS > ENVIAR (con confirmacion).'
  );
  return { ok: true, sheet: sheet.getName(), cell: BUTTON_CELL };
}

function prepararBotonesTodasLasBandas() {
  const ss = getSpreadsheet_();
  return prepararBotonesTodasLasBandas_(ss);
}

function enviarInformeDesdeBoton() {
  const sheet = SpreadsheetApp.getActiveSheet();
  return confirmarYEncolarHoja_(sheet);
}

function enviarHojaActualConConfirmacion() {
  const sheet = SpreadsheetApp.getActiveSheet();
  return confirmarYEncolarHoja_(sheet);
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

  try {
    confirmarYEncolarHoja_(sheet);
  } catch (err) {
    // En algunos contextos de trigger no hay UI para popup.
    setButtonState_(
      sheet,
      BUTTON_PENDING_CONFIRM_LABEL,
      'No se pudo abrir popup de confirmacion desde esta accion. Usa menu SITUACION BANDAS > ENVIAR (con confirmacion).'
    );
  }
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
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(15000)) {
    return {
      ok: false,
      processed: 0,
      pending: 0,
      reason: 'queue_locked',
    };
  }

  try {
    const targetSs = ss || getSpreadsheet_();
    const queueSheet = ensureQueueSheet_(targetSs);
    const lastRow = queueSheet.getLastRow();
    if (lastRow < 2) {
      return { ok: true, processed: 0, attempted: 0, pending: 0, remaining: 0 };
    }

    const rows = queueSheet.getRange(2, 1, lastRow - 1, 7).getValues();
    const statusUpdates = [];
    const resultUpdates = [];
    let processed = 0;
    let attempted = 0;
    let pending = 0;

    rows.forEach((row, idx) => {
      const status = String(row[5] || '');
      if (status !== QUEUE_STATUS_PENDING) {
        return;
      }

      pending++;
      if (attempted >= QUEUE_MAX_SENDS_PER_TICK) {
        return;
      }

      const rowNumber = idx + 2;
      const sheetName = String(row[2] || '');
      attempted++;

      try {
        sendForSheetName_(sheetName, targetSs);
        statusUpdates.push([rowNumber, QUEUE_STATUS_SENT]);
        resultUpdates.push([rowNumber, new Date()]);
        processed++;
      } catch (err) {
        statusUpdates.push([rowNumber, QUEUE_STATUS_ERROR]);
        resultUpdates.push([rowNumber, String(err && err.message ? err.message : err)]);
      }
    });

    writeColumnUpdates_(queueSheet, 6, statusUpdates);
    writeColumnUpdates_(queueSheet, 7, resultUpdates);

    return {
      ok: true,
      processed: processed,
      attempted: attempted,
      pending: pending,
      remaining: Math.max(pending - attempted, 0),
      batchLimit: QUEUE_MAX_SENDS_PER_TICK,
    };
  } finally {
    lock.releaseLock();
  }
}

function sendForSheetName_(sheetName, ss) {
  const targetSs = ss || getSpreadsheet_();
  const sheet = targetSs.getSheetByName(sheetName);
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
  setButtonState_(sheet, BUTTON_SENT_LABEL);
  return { ok: true, to: data.to, subject: data.subject };
}

function enqueueSheetSend_(sheet) {
  const queue = ensureQueueSheet_(sheet.getParent());
  if (hasPendingRequestForSheet_(queue, sheet.getName())) {
    return { ok: true, queued: false, duplicate: true };
  }
  queue.appendRow([
    Utilities.getUuid(),
    new Date(),
    sheet.getName(),
    QUEUE_REQUESTED_BY,
    OWNER_EMAIL,
    QUEUE_STATUS_PENDING,
    '',
  ]);
  return { ok: true, queued: true, duplicate: false };
}

function confirmarYEncolarHoja_(sheet) {
  if (!sheet) {
    throw new Error('No hay hoja activa.');
  }
  const sheetName = String(sheet.getName() || '');
  const upperName = sheetName.toUpperCase();
  if (upperName === SHEET_MODEL_NAME || upperName === QUEUE_SHEET_NAME) {
    throw new Error('Esta hoja no admite envio.');
  }

  const payload = readBandPayload_(sheet);
  if (!payload.to) {
    throw new Error('No hay correo destino en B2.');
  }

  const ui = SpreadsheetApp.getUi();
  const message =
    'Banda: ' + payload.banda + '\n' +
    'Destino: ' + payload.to + '\n' +
    'Asunto: ' + payload.subject + '\n\n' +
    'Quieres enviar este correo?';
  const decision = ui.alert(
    'Confirmar envio',
    message,
    ui.ButtonSet.YES_NO
  );

  if (decision !== ui.Button.YES) {
    setButtonState_(sheet, BUTTON_CANCELLED_LABEL);
    return { ok: true, queued: false, cancelled: true, sheet: sheetName };
  }

  const enqueueResult = enqueueSheetSend_(sheet);
  setButtonState_(sheet, BUTTON_QUEUED_LABEL);
  return {
    ok: true,
    queued: enqueueResult.queued,
    duplicate: enqueueResult.duplicate,
    sheet: sheetName,
  };
}

function readBandPayload_(sheet) {
  const block = sheet.getRange('A1:B14').getDisplayValues();
  const banda = String(block[0][1] || sheet.getName()).trim();
  const to = String(block[1][1] || '').trim();
  const subject = String(block[2][1] || ('Estado del proyecto: ' + banda)).trim();
  const mensaje = String(block[3][1] || '').trim();
  const obs = String(block[13][0] || '').trim();

  const fases = [];
  block.slice(6, 11).forEach((row) => {
    const fase = String(row[0] || '').trim();
    const estado = String(row[1] || '').trim();
    if (fase) {
      fases.push(fase + ': ' + estado);
    }
  });

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
  applyButtonStyle_(rng);
  rng.setNote(
    'Pulsa ENVIAR y confirma en la ventana emergente. Si no aparece popup, usa menu SITUACION BANDAS > ENVIAR (con confirmacion).'
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
    if (String(v[0] || '') === QUEUE_STATUS_PENDING) {
      pending++;
    }
  });
  return pending;
}

function hasPendingRequestForSheet_(queueSheet, sheetName) {
  const lastRow = queueSheet.getLastRow();
  if (lastRow < 2) {
    return false;
  }
  const totalRows = lastRow - 1;
  const values = queueSheet.getRange(2, 3, totalRows, 4).getValues();
  for (let i = values.length - 1; i >= 0; i--) {
    const queuedSheet = String(values[i][0] || '');
    const status = String(values[i][3] || '');
    if (queuedSheet === sheetName && status === QUEUE_STATUS_PENDING) {
      return true;
    }
  }
  return false;
}

function writeColumnUpdates_(sheet, column, updates) {
  if (!updates || updates.length === 0) {
    return;
  }

  let blockStart = updates[0][0];
  let prevRow = updates[0][0];
  let blockValues = [[updates[0][1]]];

  for (let i = 1; i < updates.length; i++) {
    const rowNumber = updates[i][0];
    const value = updates[i][1];

    if (rowNumber === prevRow + 1) {
      blockValues.push([value]);
    } else {
      sheet.getRange(blockStart, column, blockValues.length, 1).setValues(blockValues);
      blockStart = rowNumber;
      blockValues = [[value]];
    }
    prevRow = rowNumber;
  }

  sheet.getRange(blockStart, column, blockValues.length, 1).setValues(blockValues);
}

function applyButtonStyle_(rng) {
  rng.setFontWeight('bold');
  rng.setBackground('#C62828');
  rng.setFontColor('#FFFFFF');
  rng.setHorizontalAlignment('center');
}

function setButtonState_(sheet, value, note) {
  const rng = sheet.getRange(BUTTON_CELL);
  rng.setValue(value);
  applyButtonStyle_(rng);
  if (typeof note === 'string') {
    rng.setNote(note);
  }
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
