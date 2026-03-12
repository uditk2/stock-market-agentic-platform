const test = require('node:test');
const assert = require('node:assert/strict');

const { getBackgroundServiceStatus } = require('./background_service_manager');

test('linux status reports installed+running from probes', async () => {
  const seen = [];
  const run = async (command, args) => {
    seen.push([command, args.join(' ')]);
    if (args[1] === 'cat') {
      return { ok: true, stdout: '', stderr: '', exitCode: 0 };
    }
    return { ok: true, stdout: 'active', stderr: '', exitCode: 0 };
  };

  const status = await getBackgroundServiceStatus({ platform: 'linux', run });
  assert.equal(status.supported, true);
  assert.equal(status.installed, true);
  assert.equal(status.running, true);
  assert.equal(seen.length, 2);
});

test('unsupported platform returns supported=false', async () => {
  const status = await getBackgroundServiceStatus({ platform: 'freebsd', run: async () => ({ ok: false }) });
  assert.equal(status.supported, false);
});
