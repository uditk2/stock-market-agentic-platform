const test = require('node:test');
const assert = require('node:assert/strict');

const { getBackgroundServiceStatus, installBackgroundService } = require('./background_service_manager');

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

test('darwin status reports running when launchctl print includes pid', async () => {
  const status = await getBackgroundServiceStatus({
    platform: 'darwin',
    run: async () => ({
      ok: true,
      stdout: 'state = waiting\npid = 4312',
      stderr: '',
      exitCode: 0,
    }),
  });
  assert.equal(status.installed, true);
  assert.equal(status.running, true);
});

test('darwin install bootstraps and kickstarts launchagent', async () => {
  const seen = [];
  let printCount = 0;
  const run = async (command, args) => {
    seen.push([command, args.join(' ')]);
    const joined = args.join(' ');
    if (joined.startsWith('bootout')) return { ok: false, stdout: '', stderr: '', exitCode: 1 };
    if (joined.startsWith('bootstrap')) return { ok: true, stdout: '', stderr: '', exitCode: 0 };
    if (joined.startsWith('kickstart')) return { ok: true, stdout: '', stderr: '', exitCode: 0 };
    if (joined.startsWith('print')) {
      printCount += 1;
      if (printCount === 1) return { ok: true, stdout: 'state = waiting', stderr: '', exitCode: 0 };
      return { ok: true, stdout: 'state = running\npid = 100', stderr: '', exitCode: 0 };
    }
    return { ok: true, stdout: '', stderr: '', exitCode: 0 };
  };

  const install = await installBackgroundService(
    { command: '/tmp/smap-service', args: ['--port', '18787'] },
    { platform: 'darwin', run },
  );
  assert.equal(install.ok, true);
  assert.equal(install.status.running, true);
  assert.ok(seen.some((entry) => entry[1].startsWith('bootstrap')));
  assert.ok(seen.some((entry) => entry[1].startsWith('kickstart -k')));
});

test('linux install returns failure when installed but never reaches running state', async () => {
  const run = async (_command, args) => {
    const joined = args.join(' ');
    if (joined === '--user daemon-reload') return { ok: true, stdout: '', stderr: '', exitCode: 0 };
    if (joined === '--user enable --now smap-service.service') return { ok: true, stdout: '', stderr: '', exitCode: 0 };
    if (joined === '--user cat smap-service.service') return { ok: true, stdout: '', stderr: '', exitCode: 0 };
    if (joined === '--user is-active smap-service.service') return { ok: true, stdout: 'inactive', stderr: '', exitCode: 0 };
    return { ok: true, stdout: '', stderr: '', exitCode: 0 };
  };

  const install = await installBackgroundService(
    { command: '/tmp/smap-service', args: [] },
    { platform: 'linux', run },
  );
  assert.equal(install.ok, false);
  assert.equal(install.status.installed, true);
  assert.equal(install.status.running, false);
  assert.match(install.stderr, /systemd-user service installed but not running/);
});

test('windows install retries and succeeds once status reaches running', async () => {
  let queryCount = 0;
  const run = async (_command, args) => {
    const joined = args.join(' ');
    if (joined.startsWith('/Delete')) return { ok: false, stdout: '', stderr: '', exitCode: 1 };
    if (joined.startsWith('/Create')) return { ok: true, stdout: '', stderr: '', exitCode: 0 };
    if (joined.startsWith('/Run')) return { ok: true, stdout: '', stderr: '', exitCode: 0 };
    if (joined.startsWith('/Query')) {
      queryCount += 1;
      if (queryCount < 2) return { ok: true, stdout: 'Status: Ready', stderr: '', exitCode: 0 };
      return { ok: true, stdout: 'Status: Running', stderr: '', exitCode: 0 };
    }
    return { ok: true, stdout: '', stderr: '', exitCode: 0 };
  };

  const install = await installBackgroundService(
    { command: 'C:\\smap-service.exe', args: ['--port', '18787'] },
    { platform: 'win32', run },
  );
  assert.equal(install.ok, true);
  assert.equal(install.status.running, true);
});
