// static/purchasing/js/ligne_achat_inline.js
// Calcule total_ligne_ht = quantite * prix_unitaire en direct pour les inlines d'achat.
(function() {
  function toNumber(v) {
    if (v === null || v === undefined) return 0;
    if (typeof v === "string") v = v.replace(/\s/g, "").replace(",", ".");
    var n = parseFloat(v);
    return isNaN(n) ? 0 : n;
  }
  function formatDecimal(n, digits) {
    if (!isFinite(n)) return "0";
    return n.toFixed(digits || 6);
  }
  function findSiblingInput(row, suffix) {
    var inputs = row.querySelectorAll("input, select, textarea");
    for (var i = 0; i < inputs.length; i++) {
      var el = inputs[i];
      if (el.name && el.name.endsWith(suffix)) return el;
    }
    return null;
  }
  function updateRowTotal(row) {
    var qEl = findSiblingInput(row, "-quantite");
    var puEl = findSiblingInput(row, "-prix_unitaire");
    var totalEl = findSiblingInput(row, "-total_ligne_ht");
    var q = toNumber(qEl ? qEl.value : 0);
    var pu = toNumber(puEl ? puEl.value : 0);
    var total = q * pu;
    if (totalEl) totalEl.value = formatDecimal(total, 6);
    var ro = row.querySelector("div.readonly");
    if (ro) ro.textContent = formatDecimal(total, 2);
  }
  function wireRow(row) {
    var qEl = findSiblingInput(row, "-quantite");
    var puEl = findSiblingInput(row, "-prix_unitaire");
    if (qEl) qEl.addEventListener("input", function(){ updateRowTotal(row); });
    if (puEl) puEl.addEventListener("input", function(){ updateRowTotal(row); });
    updateRowTotal(row);
  }
  function init() {
    var rows = document.querySelectorAll(".inline-related.tabular tr.form-row");
    for (var i = 0; i < rows.length; i++) wireRow(rows[i]);
    document.body.addEventListener("formset:added", function(e, row) {
      var newRow = row || e && e.target;
      if (!newRow || !newRow.classList) {
        var all = document.querySelectorAll(".inline-related.tabular tr.form-row");
        if (all.length) newRow = all[all.length - 1];
      }
      if (newRow) wireRow(newRow);
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
