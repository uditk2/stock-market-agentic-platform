const test = require('node:test');
const assert = require('node:assert/strict');

const { checkSingleCli, runMandatoryCliChecks } = require('./cli_checks');

function makeRunner(map) {
  return (binary, args) => {
    const key = `${binary} ${args.join(' ')}`;
    const result = map[key];
    if (!result) {
      return {
        success: false,
        stdout: '',
        stderr: 'not mocked',
        exitCode: 1,
        error: 'not mocked',
      };
    }
    return result;
  };
}

test('checkSingleCli fails when executable is missing', () => {
  const runner = makeRunner({
    'codex --version': {
      success: false,
      stdout: '',
      stderr: 'not found',
      exitCode: 127,
      error: 'ENOENT',
    },
  });

  const result = checkSingleCli(
    {
      id: 'codex',
      label: 'OpenAI Codex CLI',
      binary: 'codex',
      authCandidates: [['login', 'status']],
    },
    runner,
  );

  assert.equal(result.installed, false);
  assert.equal(result.pass, false);
});

test('checkSingleCli passes when version and auth probes pass', () => {
  const runner = makeRunner({
    'codex --version': {
      success: true,
      stdout: 'codex 1.2.3',
      stderr: '',
      exitCode: 0,
      error: null,
    },
    'codex login status': {
      success: true,
      stdout: 'authenticated',
      stderr: '',
      exitCode: 0,
      error: null,
    },
  });

  const result = checkSingleCli(
    {
      id: 'codex',
      label: 'OpenAI Codex CLI',
      binary: 'codex',
      authCandidates: [['login', 'status']],
    },
    runner,
  );

  assert.equal(result.installed, true);
  assert.equal(result.auth_ok, true);
  assert.equal(result.pass, true);
});

test('runMandatoryCliChecks aggregates status', () => {
  const runner = makeRunner({
    'codex --version': { success: true, stdout: 'codex 1.2.3', stderr: '', exitCode: 0, error: null },
    'codex login status': { success: true, stdout: 'ok', stderr: '', exitCode: 0, error: null },
    'claude --version': { success: true, stdout: 'claude 0.9.0', stderr: '', exitCode: 0, error: null },
  });

  const result = runMandatoryCliChecks(runner);
  assert.equal(result.ok, true);
  assert.equal(result.checks.length >= 2, true);
});

test('runMandatoryCliChecks supports subscription scope', () => {
  const runner = makeRunner({
    'codex --version': { success: true, stdout: 'codex 1.2.3', stderr: '', exitCode: 0, error: null },
    'codex login status': { success: true, stdout: 'ok', stderr: '', exitCode: 0, error: null },
  });
  const result = runMandatoryCliChecks({ requiredCliIds: ['codex'] }, runner);
  assert.equal(result.ok, true);
  assert.equal(result.checks.length, 1);
  assert.equal(result.checks[0].id, 'codex');
});
