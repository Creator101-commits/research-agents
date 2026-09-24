let formulaReference = null;
let formulaReferenceLoading = null;
let formulaCalcLimit = 60;
let formulaValueLimit = 80;

function formulaNode(tag, className, content) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (content !== undefined) element.textContent = content;
  return element;
}

function formulaDisplay(value) {
  return typeof value === 'string' ? value : JSON.stringify(value);
}

function formulaSelectTab(name) {
  document.querySelectorAll('[data-fv-tab]').forEach(button => {
    const active = button.dataset.fvTab === name;
    button.classList.toggle('active', active);
    button.setAttribute('aria-selected', String(active));
  });
  document.querySelectorAll('.fv-panel').forEach(panel => {
    panel.hidden = panel.id !== 'fv-' + name;
  });
}

function formulaRenderProcess() {
  const daily = document.getElementById('fvDailyProcess');
  daily.replaceChildren(...formulaReference.daily_process.map(step => {
    const card = formulaNode('article', 'fv-process-step');
    card.append(
      formulaNode('div', 'fv-step-number', String(step.number).padStart(2, '0')),
      formulaNode('h3', '', step.name),
      formulaNode('p', '', step.description),
      formulaNode('code', '', step.call)
    );
    return card;
  }));
  const calendar = document.getElementById('fvCalendarProcess');
  calendar.replaceChildren(...formulaReference.calendar_process.map(item => {
    const card = formulaNode('div', 'fv-calendar-item');
    card.append(formulaNode('strong', '', item.name), formulaNode('span', '', item.description));
    return card;
  }));
}

function formulaOpenSource(path, line) {
  formulaSelectTab('source');
  const selector = document.getElementById('fvSourceFile');
  selector.value = path;
  formulaRenderSource(line);
  document.getElementById('fv-source').scrollIntoView({block: 'start', behavior: 'smooth'});
}

function formulaRenderCalculations() {
  const query = document.getElementById('fvCalcSearch').value.trim().toLowerCase();
  const file = document.getElementById('fvCalcFile').value;
  const matches = [...formulaReference.calculations, ...formulaReference.frontend_calculations].filter(item =>
    (!file || item.path === file) &&
    (!query || `${item.path} ${item.scope} ${item.expression}`.toLowerCase().includes(query))
  );
  const shown = matches.slice(0, formulaCalcLimit);
  document.getElementById('fvCalcCount').textContent = `Showing ${shown.length.toLocaleString()} of ${matches.length.toLocaleString()} calculations`;
  document.getElementById('fvCalcResults').replaceChildren(...shown.map(item => {
    const card = formulaNode('article', 'fv-calc');
    const head = formulaNode('div', 'fv-calc-head');
    head.append(formulaNode('span', 'fv-location', `${item.path}:${item.line}`));
    const button = formulaNode('button', 'fv-open', 'Open full source');
    button.type = 'button';
    button.addEventListener('click', () => formulaOpenSource(item.path, item.line));
    head.append(button);
    card.append(head, formulaNode('div', 'fv-scope', item.scope), formulaNode('pre', 'fv-expression', item.expression));
    return card;
  }));
  document.getElementById('fvCalcMore').hidden = shown.length === matches.length;
}

function formulaValueRows() {
  return formulaReference[document.getElementById('fvValueSet').value];
}

function formulaRenderValues() {
  const set = document.getElementById('fvValueSet').value;
  const query = document.getElementById('fvValueSearch').value.trim().toLowerCase();
  const matches = formulaValueRows().filter(item =>
    !query || JSON.stringify(item).toLowerCase().includes(query)
  );
  const shown = matches.slice(0, formulaValueLimit);
  const valueSetLabels = {
    calibration: 'calibration parameters',
    configuration: 'configuration values',
    literals: 'Python numeric and Boolean literals',
    frontend_literals: 'dashboard numeric code tokens',
  };
  document.getElementById('fvValueCount').textContent = `Showing ${shown.length.toLocaleString()} of ${matches.length.toLocaleString()} ${valueSetLabels[set]}`;
  document.getElementById('fvValueResults').replaceChildren(...shown.map(item => {
    const card = formulaNode('article', 'fv-value');
    const head = formulaNode('div', 'fv-value-head');
    head.append(
      formulaNode('span', 'fv-value-key', item.key || `${item.path}:${item.line}`),
      formulaNode('span', 'fv-value-main', formulaDisplay(item.value))
    );
    const meta = formulaNode('div', 'fv-value-meta');
    const facts = set === 'calibration'
      ? [item.unit, item.group, `range: ${formulaDisplay(item.valid_range)}`, item.assumption ? 'assumption' : 'sourced', `source: ${formulaDisplay(item.source)}`]
      : set === 'configuration'
        ? [item.path]
        : [item.path + ':' + item.line, item.scope];
    facts.filter(value => value !== undefined && value !== null).forEach(value => meta.append(formulaNode('span', '', value)));
    card.append(head, meta);
    const description = set === 'calibration' ? item.description : set === 'literals' || set === 'frontend_literals' ? item.context : '';
    if (description) card.append(formulaNode('p', 'fv-value-desc', description));
    if (set === 'literals' || set === 'frontend_literals') {
      const open = formulaNode('button', 'fv-open', 'Open full source');
      open.type = 'button';
      open.addEventListener('click', () => formulaOpenSource(item.path, item.line));
      card.append(open);
    }
    return card;
  }));
  document.getElementById('fvValueMore').hidden = shown.length === matches.length;
}

function formulaRenderSource(line) {
  const path = document.getElementById('fvSourceFile').value;
  const file = formulaReference.files.find(item => item.path === path);
  if (!file) return;
  document.getElementById('fvSourceMeta').textContent = `${file.path} · ${file.lines.toLocaleString()} lines · SHA-256 ${file.sha256}`;
  document.getElementById('fvSourceCode').textContent = file.text;
  const preview = document.getElementById('fvSourcePreview');
  if (line) {
    const lines = file.text.split('\n');
    const first = Math.max(1, line - 5);
    const last = Math.min(lines.length, line + 8);
    preview.textContent = lines.slice(first - 1, last).map((text, index) =>
      `${String(first + index).padStart(5, ' ')} ${text}`
    ).join('\n');
    preview.hidden = false;
  } else {
    preview.hidden = true;
  }
}

function formulaSetup() {
  const stats = [
    [formulaReference.calibration.length, 'calibration parameters'],
    [formulaReference.calculations.length + formulaReference.frontend_calculations.length, 'indexed expressions'],
    [formulaReference.literals.length + formulaReference.frontend_literals.length, 'code number occurrences'],
    [formulaReference.files.length, 'full source files'],
  ];
  document.getElementById('fvStats').replaceChildren(...stats.map(([count, label]) => {
    const card = formulaNode('div', 'fv-stat');
    card.append(formulaNode('strong', '', count.toLocaleString()), formulaNode('span', '', label));
    return card;
  }));
  formulaRenderProcess();
  const calculationFiles = formulaReference.files.filter(item => item.path.endsWith('.py') || item.path === 'web/js/dashboard.js');
  const calcSelect = document.getElementById('fvCalcFile');
  calculationFiles.forEach(file => {
    const option = formulaNode('option', '', file.path);
    option.value = file.path;
    calcSelect.append(option);
  });
  const sourceSelect = document.getElementById('fvSourceFile');
  formulaReference.files.forEach(file => {
    const option = formulaNode('option', '', file.path);
    option.value = file.path;
    sourceSelect.append(option);
  });
  sourceSelect.value = 'dairy_abm/model.py';
  document.querySelectorAll('[data-fv-tab]').forEach(button =>
    button.addEventListener('click', () => formulaSelectTab(button.dataset.fvTab))
  );
  document.getElementById('fvCalcSearch').addEventListener('input', () => {formulaCalcLimit = 60; formulaRenderCalculations();});
  calcSelect.addEventListener('change', () => {formulaCalcLimit = 60; formulaRenderCalculations();});
  document.getElementById('fvCalcMore').addEventListener('click', () => {formulaCalcLimit += 60; formulaRenderCalculations();});
  document.getElementById('fvValueSet').addEventListener('change', () => {formulaValueLimit = 80; formulaRenderValues();});
  document.getElementById('fvValueSearch').addEventListener('input', () => {formulaValueLimit = 80; formulaRenderValues();});
  document.getElementById('fvValueMore').addEventListener('click', () => {formulaValueLimit += 80; formulaRenderValues();});
  sourceSelect.addEventListener('change', () => formulaRenderSource());
  formulaRenderCalculations();
  formulaRenderValues();
  formulaRenderSource();
}

async function initFormulaPage() {
  if (formulaReference) return;
  if (!formulaReferenceLoading) {
    formulaReferenceLoading = fetch('/assets/data/formulas_values.json')
      .then(response => {
        if (!response.ok) throw new Error('Formula reference unavailable');
        return response.json();
      })
      .then(data => {formulaReference = data; formulaSetup();})
      .catch(error => {
        formulaReferenceLoading = null;
        document.getElementById('fvStats').textContent = error.message;
      });
  }
  await formulaReferenceLoading;
}
