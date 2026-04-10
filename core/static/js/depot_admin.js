(function () {
  function toggleBlocks() {
    const typeField = document.getElementById("id_type_lieu");
    if (!typeField) return;

    const isBureau = typeField.value === "BUREAU";

    // Le fieldset "Bureau / Service" est le 3e (selon fieldsets ci-dessus)
    const fieldsets = document.querySelectorAll("fieldset.module");
    if (fieldsets.length < 3) return;

    const bureauFs = fieldsets[2];
    bureauFs.style.display = isBureau ? "" : "none";
  }

  document.addEventListener("DOMContentLoaded", function () {
    toggleBlocks();
    const typeField = document.getElementById("id_type_lieu");
    if (typeField) {
      typeField.addEventListener("change", toggleBlocks);
    }
  });
})();
