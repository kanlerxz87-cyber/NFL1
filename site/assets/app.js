/* Progressive enhancement only: the site is fully readable without JS. */
(function () {
  "use strict";

  // Row filter for every generated table.
  document.querySelectorAll("input.table-filter").forEach(function (input) {
    var target = document.querySelector(input.getAttribute("data-target"));
    if (!target) return;
    var counter = document.querySelector("[data-count-for='" + input.getAttribute("data-target").slice(1) + "']");
    var body = target.tBodies[0];
    if (!body) return;
    input.addEventListener("input", function () {
      var q = input.value.trim().toLowerCase();
      var shown = 0;
      Array.prototype.forEach.call(body.rows, function (row) {
        var match = !q || row.textContent.toLowerCase().indexOf(q) !== -1;
        row.style.display = match ? "" : "none";
        if (match) shown++;
      });
      if (counter) counter.textContent = shown + " rows shown";
    });
  });

  // Click a header to sort the table by that column.
  document.querySelectorAll("table.data-table th.sortable").forEach(function (th, idx) {
    th.addEventListener("click", function () {
      var table = th.closest("table");
      var body = table.tBodies[0];
      if (!body) return;
      var col = Array.prototype.indexOf.call(th.parentNode.children, th);
      var asc = th.getAttribute("data-dir") !== "asc";
      th.setAttribute("data-dir", asc ? "asc" : "desc");
      var rows = Array.prototype.slice.call(body.rows);
      rows.sort(function (a, b) {
        var x = (a.cells[col] ? a.cells[col].textContent.trim() : "");
        var y = (b.cells[col] ? b.cells[col].textContent.trim() : "");
        var nx = parseFloat(x.replace(/,/g, "")), ny = parseFloat(y.replace(/,/g, ""));
        var cmp = (!isNaN(nx) && !isNaN(ny)) ? nx - ny : x.localeCompare(y);
        return asc ? cmp : -cmp;
      });
      rows.forEach(function (r) { body.appendChild(r); });
    });
  });

  // Review & Choose a Path: local, reviewer-side decision record.
  var radios = document.querySelectorAll("input[name='chosen-path']");
  var outcome = document.getElementById("path-outcome");
  var issue = document.getElementById("path-issue");
  var key = "NFL1.chosenPath";
  function current() {
    var checked = document.querySelector("input[name='chosen-path']:checked");
    return checked ? { id: checked.value, label: checked.getAttribute("data-label") } : null;
  }
  function render() {
    var saved = null;
    try { saved = JSON.parse(localStorage.getItem(key) || "null"); } catch (e) { saved = null; }
    if (saved && outcome) {
      outcome.textContent = "Saved in this browser: " + saved.label + " (" + saved.id + "). Not implemented — waiting for reviewer confirmation.";
      radios.forEach(function (r) { r.checked = (r.value === saved.id); });
    } else if (outcome) {
      outcome.textContent = "No path has been chosen. Nothing on this site is implemented until a reviewer chooses.";
    }
    if (issue && saved) {
      var body = encodeURIComponent(
        "## Decision record\n\nChosen path: " + saved.label + " (" + saved.id + ")\n\n" +
        "Chosen by: <!-- reviewer -->\nDate: <!-- date -->\n\n" +
        "Open questions to close before implementation: see questions.html\n" +
        "Flagged items: see flagged.html\n\n" +
        "This issue records the review decision. No implementation has been performed by the agent."
      );
      issue.href = "https://github.com/kanlerxz87-cyber/NFL1/issues/new?title=" +
        encodeURIComponent("Decision record: " + saved.id) + "&body=" + body;
    }
    if (issue && !saved) issue.removeAttribute("href");
  }
  radios.forEach(function (r) {
    r.addEventListener("change", function () {
      var c = current();
      if (!c) return;
      try { localStorage.setItem(key, JSON.stringify(c)); } catch (e) { /* storage blocked */ }
      render();
    });
  });
  render();
})();
