const test = require('node:test');
const assert = require('node:assert/strict');
const {
  buildWizardCliInstallPlan,
  runWizardCliInstall,
  shellCommandForPlatform,
} = require('./wizard_cli_install');

test('buildWizardCliInstallPlan rejects unknown target', () => {
  const result = buildWizardCliInstallPlan({
    platform: 'linux',
    subscription: 'both',
    cliId: 'unknown',
  });
  assert.equal(result.ok, false);
  assert.equal(result.error, 'unknown_cli_target');
});

test('buildWizardCliInstallPlan rejects subscription mismatch', () => {
  const result = buildWizardCliInstallPlan({
    platform: 'linux',
    subscription: 'claude',
    cliId: 'codex',
  });
  assert.equal(result.ok, false);
  assert.equal(result.error, 'subscription_mismatch');
});

test('buildWizardCliInstallPlan returns codex install plan', () => {
  const result = buildWizardCliInstallPlan({
    platform: 'linux',
    subscription: 'codex',
    cliId: 'codex',
  });
  assert.equal(result.ok, true);
  assert.equal(result.install_command, 'npm install -g @openai/codex');
  assert.equal(result.auth_command, 'codex auth login');
});

test('shellCommandForPlatform uses cmd on windows', () => {
  const result = shellCommandForPlatform('win32', 'echo hi');
  assert.equal(result.binary, 'cmd.exe');
  assert.deepEqual(result.args, ['/d', '/s', '/c', 'echo hi']);
});

test('runWizardCliInstall returns prereq failure when npm is missing', async () => {
  const result = await runWizardCliInstall(
    {
      platform: 'linux',
      subscription: 'codex',
      cliId: 'codex',
    },
    async () => ({
      ok: false,
      code: 1,
      stdout: '',
      stderr: 'npm: command not found',
      error: null,
    }),
  );
  assert.equal(result.ok, false);
  assert.equal(result.error, 'prereq_failed');
});
