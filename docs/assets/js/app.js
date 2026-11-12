/* NFL1 dashboard - progressive enhancement only.
   All table content is already in the HTML; this file only adds sorting,
   searching and category filtering. If it fails to load, every page still reads. */
(function () {
  'use strict';

  function text(cell) {
    return (cell.textContent || '').replace(/\s+/g, ' ').trim();
  }

  /* ---- sorting ---- */
  document.querySelectorAll('table[data-sortable]').forEach(function (table) {
    var head = table.tHead;
    if (!head) return;
    var headers = Array.prototype.slice.call(head.rows[head.rows.length - 1].cells);
    var body = table.tBodies[0];
    if (!body) return;

    headers.forEach(function (th, idx) {
      if (th.classList.contains('no-sort')) return;
      th.classList.add('sortable');
      th.setAttribute('scope', 'col');
      th.addEventListener('click', function () {
        var asc = !th.classList.contains('asc');
        headers.forEach(function (h) { h.classList.remove('asc', 'desc'); });
        th.classList.add(asc ? 'asc' : 'desc');
        var rows = Array.prototype.slice.call(body.rows);
        var num = th.classList.contains('num');
        rows.sort(function (a, b) {
          var x = text(a.cells[idx] || a.cells[0]);
          var y = text(b.cells[idx] || b.cells[0]);
          var r;
          if (num) {
            var nx = parseFloat(x.replace(/[^0-9.\-]/g, ''));
            var ny = parseFloat(y.replace(/[^0-9.\-]/g, ''));
            if (isNaN(nx) && isNaN(ny)) r = 0;
            else if (isNaN(nx)) r = 1;
            else if (isNaN(ny)) r = -1;
            else r = nx - ny;
          } else {
            r = x.localeCompare(y, undefined, { numeric: true, sensitivity: 'base' });
          }
          return asc ? r : -r;
        });
        rows.forEach(function (row) { body.appendChild(row); });
      });
    });
  });

  /* ---- searching + category filtering ---- */
  document.querySelectorAll('[data-table-tools]').forEach(function (tools) {
    var wrap = tools.closest('.card') || document;
    var table = wrap.querySelector('table');
    if (!table) return;
    var body = table.tBodies[0];
    var search = tools.querySelector('input[type=search]');
    var select = tools.querySelector('select[data-filter]');
    var count = tools.querySelector('.count');
    var filterCol = select ? parseInt(select.getAttribute('data-filter'), 10) : -1;
    var rows = Array.prototype.slice.call(body.rows);
    var empty = wrap.querySelector('.tbl-empty');

    function apply() {
      var q = search ? search.value.toLowerCase().trim() : '';
      var pick = select ? select.value : '';
      var shown = 0;
      rows.forEach(function (row) {
        var hay = (row.getAttribute('data-search') || '') + ' ' + text(row).toLowerCase();
        var okQ = !q || hay.indexOf(q) !== -1;
        var okF = !select || !pick ||
          text(row.cells[filterCol] || row.cells[0]).toLowerCase() === pick.toLowerCase();
        var vis = okQ && okF;
        row.style.display = vis ? '' : 'none';
        if (vis) shown++;
      });
      if (count) count.textContent = shown + ' of ' + rows.length + ' rows';
      if (empty) empty.style.display = shown === 0 ? '' : 'none';
    }

    if (search) search.addEventListener('input', apply);
    if (select) select.addEventListener('change', apply);
    if (search || select) apply();
  });

  /* ---- collapse long cards ---- */
  document.querySelectorAll('[data-collapse]').forEach(function (btn) {
    var target = document.getElementById(btn.getAttribute('data-collapse'));
    if (!target) return;
    btn.addEventListener('click', function () {
      var hidden = target.hasAttribute('hidden');
      if (hidden) { target.removeAttribute('hidden'); btn.textContent = 'Hide details'; }
      else { target.setAttribute('hidden', ''); btn.textContent = 'Show details'; }
    });
    target.setAttribute('hidden', '');
  });
})();
