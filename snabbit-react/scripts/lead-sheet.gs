/* Google Apps Script backing the website's request-form backup.

   Setup (once):
   1. Create a Google Sheet (e.g. "Switch website leads").
   2. Extensions → Apps Script, replace the code with this file, Save.
   3. Deploy → New deployment → type "Web app".
      Execute as: Me · Who has access: Anyone → Deploy, allow access.
   4. Copy the web app URL (ends in /exec) into LEADS_SHEET_URL in
      src/data/site.js.

   Each form submit appends one row to the "Leads" tab. */

const SHEET_NAME = 'Leads'
const FIELDS = ['business', 'phone', 'role', 'count', 'area', 'message', 'page']
const HEADERS = ['Received', 'Business', 'Phone', 'Role', 'How many', 'Area', 'Notes', 'Page']

function doPost(e) {
  const p = (e && e.parameter) || {}
  if (p['bot-field']) return ok() // honeypot filled — a bot

  const lock = LockService.getScriptLock()
  lock.waitLock(10000)
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet()
    const sheet = ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME)
    if (sheet.getLastRow() === 0) {
      sheet.appendRow(HEADERS)
      sheet.setFrozenRows(1)
    }
    sheet.appendRow([new Date()].concat(FIELDS.map((f) => clean(p[f]))))
  } finally {
    lock.releaseLock()
  }
  return ok()
}

// Stop entries like "=HYPERLINK(...)" from running as formulas in the sheet.
function clean(v) {
  const s = String(v || '').slice(0, 1000)
  return /^[=+\-@]/.test(s) ? "'" + s : s
}

function ok() {
  return ContentService.createTextOutput('ok')
}
