const test = require('node:test');
const assert = require('node:assert/strict');
const { buildWizardCliInstallPlan } = require('./wizard_cli_install');

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
