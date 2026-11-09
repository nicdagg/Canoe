const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const pg = await b.newPage({ viewport: { width: 1200, height: 900 }, acceptDownloads: true });
  const errs = []; pg.on('pageerror', e => errs.push('PAGEERR ' + e.message));
  await pg.goto('file://' + process.argv[2]);
  if (process.argv[4]) { await pg.evaluate((n) => { [...document.querySelectorAll('button')].find(x => x.textContent.trim() === n).click(); }, process.argv[4]); await pg.waitForTimeout(500); }
  await pg.click('#open-mold'); await pg.waitForTimeout(2500);
  console.log('STATUS', await pg.innerText('#md-status'));
  const [dl] = await Promise.all([pg.waitForEvent('download', { timeout: 60000 }), pg.click('#md-save')]);
  await dl.saveAs(process.argv[3]); console.log('saved', dl.suggestedFilename(), errs.join('\n'));
  await b.close();
})();
