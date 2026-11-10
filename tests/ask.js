// Checks the Ask Claude panel against a stand-in for the Anthropic service (no key, no cost).
//   node tests/ask.js [path to index.html] [folder for screenshots]
'use strict';
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const file = path.resolve(process.argv[2] || path.join(__dirname, '..', 'index.html')), shots = process.argv[3];
  const b = await chromium.launch(); let bad = 0;
  for (const vp of [{ width: 1280, height: 900 }, { width: 390, height: 780 }]) {
    const pg = await b.newPage({ viewport: vp }); const errs = [], sent = [];
    pg.on('pageerror', e => errs.push(e.message));
    await pg.route('https://api.anthropic.com/**', async route => {
      const rq = route.request(), body = rq.postDataJSON(), h = rq.headers(); sent.push({ body, h });
      const reply = (content, stop) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ id: 'msg_x', type: 'message', role: 'assistant', model: body.model, content, stop_reason: stop, usage: { input_tokens: 5000, output_tokens: 1000 } }) });
      if (h['x-api-key'] === 'bad') return route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ type: 'error', error: { type: 'authentication_error', message: 'invalid x-api-key' } }) });
      const last = body.messages[body.messages.length - 1];
      if (typeof last.content === 'string') return reply([{ type: 'text', text: 'Let me test a narrower hull.' }, { type: 'tool_use', id: 'toolu_1', name: 'try_shape', input: { water: 'calm-lake', changes: [{ slider: 'beam', value: 33 }, { slider: 'b_rocker', value: 99 }], offer: true, label: 'Narrower' } }], 'tool_use');
      return reply([{ type: 'text', text: 'A 33 inch beam scores ' + JSON.parse(last.content[0].content).score + '.' }], 'end_turn');
    });
    const check = (ok, what) => { if (!ok) errs.push(what); };
    await pg.goto('file://' + file); await pg.waitForTimeout(400);
    await pg.click('#open-ai');
    check(await pg.isVisible('#ai-key'), 'setup is not open when there is no key');
    await pg.fill('#ai-key', 'bad'); await pg.click('#ai-save');
    await pg.fill('#ai-q', 'hello'); await pg.click('#ai-send'); await pg.waitForSelector('.ai-m.err');
    check(/did not accept/.test(await pg.innerText('.ai-m.err')), 'a bad key gives no clear message');
    await pg.click('#ai-setup summary'); await pg.fill('#ai-key', 'sk-test'); await pg.click('#ai-save');
    await pg.fill('#ai-q', 'make it faster'); await pg.click('#ai-send');
    await pg.waitForSelector('.ai-offer', { timeout: 30000 }); await pg.waitForFunction(() => !document.querySelector('.ai-m.wait'));
    const good = sent.filter(s => s.h['x-api-key'] === 'sk-test');
    check(good.length === 2, 'expected 2 calls, saw ' + good.length);
    check(good[0].body.model === 'claude-fable-5-2' && good[0].body.fallbacks === 'default' && !('temperature' in good[0].body) && !('tool_choice' in good[0].body), 'request body is not as expected');
    check(good[0].body.messages.length === 1, 'the failed question leaked into the history');
    check(good[1] && good[1].body.messages[1].content[1].type === 'tool_use' && good[1].body.messages[2].content[0].type === 'tool_result', 'tool result not sent back');
    const res = good[1] && JSON.parse(good[1].body.messages[2].content[0].content);
    check(res && res.sliders_changed.beam === 33 && res.sliders_changed.b_rocker === 8 && typeof res.score === 'number', 'tool result wrong: ' + JSON.stringify(res && res.sliders_changed));
    check(/33 inch beam scores \d+/.test(await pg.innerText('#ai-log')), 'answer not shown');
    if (shots) await pg.screenshot({ path: path.join(shots, 'ask-' + vp.width + '.png') });
    await pg.click('.ai-offer .btn.primary'); await pg.waitForTimeout(300);
    const v1 = await pg.evaluate(() => document.querySelector('.ai-offer .btn:not(.primary)').hidden);
    check(v1 === false, 'Go back did not appear');
    await pg.click('.ai-offer .btn:not(.primary)');
    await pg.click('#ai-setup summary'); await pg.click('#ai-forget');
    check(await pg.evaluate(() => localStorage.getItem('canoe-hull-designer-claude')) === null, 'key not forgotten');
    await pg.click('#ai-close');
    if (shots) await pg.screenshot({ path: path.join(shots, 'main-' + vp.width + '.png') });
    console.log(vp.width + ' px wide: ' + (errs.length ? 'FAILED\n  ' + errs.join('\n  ') : 'ok')); bad += errs.length;
    await pg.close();
  }
  await b.close(); process.exit(bad ? 1 : 0);
})();
