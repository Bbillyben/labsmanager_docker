const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const path = require('path');

const script = fs.readFileSync(path.join(__dirname, 'static/plugin/js/token_copy.js'), 'utf8');

async function click({ clipboard, execCommand }) {
    const handlers = {};
    const secret = 'public-id.private-secret';
    const input = {
        value: secret,
        focus() { this.focused = true; },
        select() { this.selected = true; },
        setSelectionRange(start, end) { this.range = [start, end]; },
        addEventListener() {},
    };
    const button = { addEventListener(event, handler) { handlers[event] = handler; } };
    const status = { textContent: '' };
    const document = {
        readyState: 'complete',
        getElementById(id) {
            return {
                'created-plugin-token': input,
                'copy-plugin-token': button,
                'copy-plugin-token-status': status,
            }[id];
        },
        execCommand(command) {
            assert.strictEqual(command, 'copy');
            assert.strictEqual(input.selected, true);
            return execCommand;
        },
    };
    vm.runInNewContext(script, { document, navigator: clipboard ? { clipboard } : {}, Promise });
    handlers.click();
    await Promise.resolve();
    await Promise.resolve();
    return { input, status, secret };
}

(async () => {
    let written;
    const secure = await click({ clipboard: { writeText: async value => { written = value; } }, execCommand: false });
    assert.strictEqual(written, secure.secret);
    assert.strictEqual(secure.status.textContent, 'Token copied.');

    const http = await click({ execCommand: true });
    assert.strictEqual(http.status.textContent, 'Token copied.');
    assert.deepStrictEqual(http.input.range, [0, http.secret.length]);

    const denied = await click({ clipboard: { writeText: async () => { throw Error('denied'); } }, execCommand: true });
    assert.strictEqual(denied.status.textContent, 'Token copied.');

    const manual = await click({ execCommand: false });
    assert.strictEqual(manual.input.selected, true);
    assert.ok(!manual.status.textContent.includes('Token copied.'));
    console.log('Token copy interactions: OK');
})().catch(error => { console.error(error); process.exitCode = 1; });
