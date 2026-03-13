const test = require('node:test');
const assert = require('node:assert/strict');

const { isCommandAllowed } = require('./terminal_profiles');

test('ops_status allows readonly health command', () => {
  assert.equal(isCommandAllowed('ops_status', 'curl http://127.0.0.1:18787/health'), true);
});

test('ops_status rejects chained shell command', () => {
  assert.equal(isCommandAllowed('ops_status', 'pwd; rm -rf /'), false);
});

test('service_logs allows journalctl profile command', () => {
  assert.equal(
    isCommandAllowed('service_logs', 'journalctl -u orchestrator.service -n 50 --no-pager'),
    true,
  );
});

test('repo_dev rejects destructive git command', () => {
  assert.equal(isCommandAllowed('repo_dev', 'git reset --hard'), false);
});
