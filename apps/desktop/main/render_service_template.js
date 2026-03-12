#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { renderServiceTemplate } = require('./service_install_templates');

function parseArgs(argv) {
  const result = {
    target: '',
    output: '',
    workingDirectory: '',
    serviceBin: '',
    serviceArgs: [],
    label: 'com.smap.service',
    description: 'SMAP Background Service',
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--target') result.target = argv[++i] || '';
    else if (arg === '--output') result.output = argv[++i] || '';
    else if (arg === '--working-directory') result.workingDirectory = argv[++i] || '';
    else if (arg === '--service-bin') result.serviceBin = argv[++i] || '';
    else if (arg === '--arg') result.serviceArgs.push(argv[++i] || '');
    else if (arg === '--label') result.label = argv[++i] || result.label;
    else if (arg === '--description') result.description = argv[++i] || result.description;
    else throw new Error(`unknown_argument:${arg}`);
  }

  if (!result.target || !result.output || !result.workingDirectory || !result.serviceBin) {
    throw new Error('missing_required_args');
  }

  return result;
}

function main() {
  const parsed = parseArgs(process.argv.slice(2));
  const content = renderServiceTemplate(parsed.target, {
    workingDirectory: path.resolve(parsed.workingDirectory),
    serviceBin: parsed.serviceBin,
    serviceArgs: parsed.serviceArgs,
    label: parsed.label,
    description: parsed.description,
  });
  fs.writeFileSync(parsed.output, content, 'utf8');
}

main();
