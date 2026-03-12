const test = require('node:test');
const assert = require('node:assert/strict');

const {
  renderLinuxSystemdUnit,
  renderMacLaunchAgent,
  renderWindowsTaskXml,
} = require('./service_install_templates');

test('renderLinuxSystemdUnit includes binary and args', () => {
  const output = renderLinuxSystemdUnit({
    workingDirectory: '/tmp/smap',
    serviceBin: '/tmp/smap/smap-service',
    serviceArgs: ['--port', '8787'],
    description: 'SMAP Unit',
  });

  assert.match(output, /Description=SMAP Unit/);
  assert.match(output, /WorkingDirectory=\/tmp\/smap/);
  assert.match(output, /ExecStart=\/tmp\/smap\/smap-service --port 8787/);
});

test('renderMacLaunchAgent escapes xml entities', () => {
  const output = renderMacLaunchAgent({
    label: 'com.smap.service',
    workingDirectory: '/tmp/smap&ops',
    serviceBin: '/tmp/smap-service',
    serviceArgs: ['--token', 'a&b<c>'],
  });

  assert.match(output, /<string>\/tmp\/smap&amp;ops<\/string>/);
  assert.match(output, /<string>a&amp;b&lt;c&gt;<\/string>/);
});

test('renderWindowsTaskXml escapes command fields', () => {
  const output = renderWindowsTaskXml({
    workingDirectory: 'C:\\SMAP\\Run&Ops',
    serviceBin: 'C:\\SMAP\\smap-service.exe',
    serviceArgs: ['--profile', 'live<prod>'],
  });

  assert.match(output, /C:\\SMAP\\Run&amp;Ops/);
  assert.match(output, /live&lt;prod&gt;/);
});
