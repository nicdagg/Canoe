// Opens the built page in a real browser and walks through every panel, failing on any script error.
// Needs Playwright:  node tests/smoke.js [path to index.html]
'use strict';
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const file = path.resolve(process.argv[2] || path.join(__dirname, '..', 'index.html'));
  const b = await chromium.launch(); let bad = 0;
  for (const vp of [{ width: 1280, height: 900 }, { width: 390, height: 780 }]) {
    const pg = await b.newPage({ viewport: vp });
    const errs = []; pg.on('pageerror', e => errs.push(e.message)); pg.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
    await pg.goto('file://' + file); await pg.waitForTimeout(400);
    const step = async (name, fn) => { try { await fn(); } catch (e) { errs.push(name + ': ' + e.message.split('\n')[0]); } };
    const press = (name) => pg.evaluate(n => [...document.querySelectorAll('button')].find(x => x.textContent.trim() === n).click(), name);
    await step('analyze', async () => {
      await pg.click('#open-an'); await pg.waitForSelector('#an-score b', { timeout: 20000 }); await pg.waitForTimeout(1500);
      const s = await pg.innerText('#an-score'); if (!/\d/.test(s)) throw new Error('no score: ' + s);
      const tabs = await pg.$$('#ov-an [role=tab]'); for (const t of tabs) { await t.click(); await pg.waitForTimeout(900); }
      if (tabs.length) await tabs[0].click();
      await pg.click('#an-start'); await pg.waitForTimeout(6000); await pg.click('#an-start');
      await pg.waitForSelector('#an-found:not([hidden])', { timeout: 60000 });
      if (await pg.isVisible('#an-use')) { await pg.click('#an-use'); await pg.waitForTimeout(800); await pg.click('#an-undo'); }
      await pg.click('#an-close');
    });
    await step('lines plan', async () => { await pg.click('#open-plan'); await pg.waitForTimeout(500); for (const t of await pg.$$('#plan-tabs button')) { await t.click(); await pg.waitForTimeout(150); } await pg.click('#plan-close'); });
    await step('3d', async () => { await pg.click('#open-3d'); await pg.waitForTimeout(600); await pg.click('#v3-close'); });
    await step('mold', async () => { await pg.click('#open-mold'); await pg.waitForTimeout(2500); if (!(await pg.innerText('#md-tiles')).trim()) throw new Error('no tile list'); await pg.click('#md-close'); });
    await step('laminate', async () => {
      await pg.click('#open-lam'); await pg.waitForTimeout(1800);
      const n = await pg.$$eval('#lm-recs > li', l => l.length); if (n < 9) throw new Error('only ' + n + ' test rows');
      for (const m of await pg.$$('#lm-metric button')) { await m.click(); await pg.waitForTimeout(150); }
      await pg.click('#lc-quick button[data-q=fix]'); await pg.waitForTimeout(2500);
      const r = await pg.innerText('#lm-read'); if (!/Shell that needs work\s*none/.test(r)) throw new Error('fix left failing panels: ' + r.replace(/\n/g, ' '));
      await pg.click('#lm-close');
    });
    for (const name of ['Solo', "Kid's pack boat", 'Tumblehome']) {
      await step('preset ' + name, async () => {
        await press(name); await pg.waitForTimeout(400);
        await pg.click('#open-lam'); await pg.waitForTimeout(1500); await pg.click('#lm-close');
        await pg.click('#open-mold'); await pg.waitForTimeout(2000); await pg.click('#md-close');
      });
    }
    console.log(vp.width + ' px wide: ' + (errs.length ? 'FAILED\n  ' + errs.join('\n  ') : 'ok')); bad += errs.length;
    await pg.close();
  }
  await b.close(); process.exit(bad ? 1 : 0);
})();
