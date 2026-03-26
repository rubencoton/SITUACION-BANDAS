const PROP_TOKEN = 'MAIL_GATEWAY_TOKEN';
const PROP_ALLOWED_SHEET_ID = 'MAIL_ALLOWED_SHEET_ID';
const PROP_SEND_ENABLED = 'MAIL_SEND_ENABLED';
const BRAND_NAME = 'Artes Buho';
const DEFAULT_FROM = 'booking@artesbuhomanagement.com';
const STATIC_TOKEN = '__MAIL_GATEWAY_TOKEN__';
const STATIC_ALLOWED_SHEET_ID = '__SHEET_ID__';
const STATIC_SEND_ENABLED = true;

function doGet() {
  return jsonOutput_({
    ok: true,
    service: 'situacion-bandas-mail-gateway',
    timestamp: new Date().toISOString(),
  });
}

function doPost(e) {
  try {
    const payload = parsePayload_(e);
    validatePayload_(payload);

    const props = PropertiesService.getScriptProperties();
    const expectedToken = props.getProperty(PROP_TOKEN) || STATIC_TOKEN;
    const allowedSheetId = props.getProperty(PROP_ALLOWED_SHEET_ID) || STATIC_ALLOWED_SHEET_ID;
    const sendEnabled =
      (props.getProperty(PROP_SEND_ENABLED) || String(STATIC_SEND_ENABLED)) === 'true';

    if (!expectedToken || payload.token !== expectedToken) {
      return jsonOutput_({ ok: false, error: 'unauthorized_token' });
    }
    if (allowedSheetId && payload.sheetId !== allowedSheetId) {
      return jsonOutput_({ ok: false, error: 'sheet_not_allowed' });
    }

    const validateOnly = payload.validateOnly === true;
    if (!sendEnabled && !validateOnly) {
      return jsonOutput_({
        ok: false,
        error: 'send_disabled',
        message: 'Envio desactivado por configuracion.',
      });
    }

    if (validateOnly) {
      return jsonOutput_({
        ok: true,
        sent: false,
        dryRun: true,
        to: payload.to,
        subject: payload.subject,
        timestamp: new Date().toISOString(),
      });
    }

    const options = {
      name: BRAND_NAME,
      replyTo: DEFAULT_FROM,
      noReply: false,
    };

    GmailApp.sendEmail(payload.to, payload.subject, payload.body, options);

    return jsonOutput_({
      ok: true,
      sent: true,
      dryRun: false,
      to: payload.to,
      subject: payload.subject,
      timestamp: new Date().toISOString(),
    });
  } catch (err) {
    return jsonOutput_({
      ok: false,
      error: 'gateway_exception',
      message: String(err && err.message ? err.message : err),
    });
  }
}

function setupGatewayConfig(sheetId, token, sendEnabled) {
  if (!sheetId || !token) {
    throw new Error('setupGatewayConfig requiere sheetId y token.');
  }
  const props = PropertiesService.getScriptProperties();
  props.setProperty(PROP_ALLOWED_SHEET_ID, String(sheetId));
  props.setProperty(PROP_TOKEN, String(token));
  props.setProperty(PROP_SEND_ENABLED, String(sendEnabled === true));
  return {
    ok: true,
    sheetId: String(sheetId),
    sendEnabled: sendEnabled === true,
  };
}

function getGatewayConfigStatus() {
  const props = PropertiesService.getScriptProperties();
  return {
    ok: true,
    hasToken: Boolean(props.getProperty(PROP_TOKEN)),
    allowedSheetId: props.getProperty(PROP_ALLOWED_SHEET_ID) || '',
    sendEnabled: props.getProperty(PROP_SEND_ENABLED) === 'true',
    updatedAt: new Date().toISOString(),
  };
}

function parsePayload_(e) {
  if (!e || !e.postData || !e.postData.contents) {
    throw new Error('Request vacia');
  }
  return JSON.parse(e.postData.contents);
}

function validatePayload_(payload) {
  if (!payload) {
    throw new Error('Payload vacio');
  }
  if (!payload.token) {
    throw new Error('Falta token');
  }
  if (!payload.sheetId) {
    throw new Error('Falta sheetId');
  }
  if (!payload.to) {
    throw new Error('Falta destinatario');
  }
  if (!payload.subject) {
    throw new Error('Falta subject');
  }
  if (!payload.body) {
    throw new Error('Falta body');
  }
}

function jsonOutput_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
