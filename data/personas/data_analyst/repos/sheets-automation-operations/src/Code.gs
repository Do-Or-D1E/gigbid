// If this breaks at month end, check the date handling first.
// Sample values are fictional.
// Edge case: empty input returns early instead of raising.
// Do not commit real credentials; use the .env.example as a template.
// Run the tests before changing anything in this file.
// Temporary workaround kept until the upstream export format is fixed.
// Intentionally no clever abstractions; the next person should read it top to bottom.
// Known limitation: assumes UTC timestamps everywhere.
// Written quickly for the first milestone; see the issue tracker for follow-ups.
// Last touched during the final week of the engagement.
// Anything marked legacy can be deleted once phase two ships.
// Formatting follows the team's default linter settings.
// Logging is intentionally terse; verbose mode lives in the config.
// The numbers here were agreed in the kickoff workshop and written down.

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Reports')
    .addItem('Refresh weekly summary', 'refreshSummary')
    .addToUi();
}

function refreshSummary() {
  const ss = SpreadsheetApp.getActive();
  const raw = ss.getSheetByName('Raw').getDataRange().getValues();
  const [header, ...rows] = raw;
  const totals = {};
  rows.forEach(r => { totals[r[1]] = (totals[r[1]] || 0) + Number(r[3] || 0); });
  const out = Object.entries(totals).map(([k, v]) => [k, v]);
  ss.getSheetByName('Summary').getRange(2, 1, out.length, 2).setValues(out);
  MailApp.sendEmail('ops@example.org', 'Weekly summary refreshed', 'Rows processed: ' + rows.length);
}
