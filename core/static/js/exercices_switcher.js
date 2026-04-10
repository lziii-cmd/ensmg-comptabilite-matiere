// static/js/exercices_switcher.js
document.addEventListener("DOMContentLoaded", function () {
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(";").shift();
  }

  const toolbar = document.getElementById("xrcToolbar");
  if (!toolbar) return;

  const actionUrl = toolbar.dataset.action;
  const list = document.getElementById("xrcList");
  const btnAll = document.getElementById("xrcAll");
  const btnNone = document.getElementById("xrcNone");
  const btnApply = document.getElementById("xrcApply");
  const countEl = document.getElementById("xrcCount");

  function currentIds() {
    return Array.from(list.querySelectorAll('input[type="checkbox"]'))
      .filter(c => c.checked)
      .map(c => c.value);
  }

  function updateCount() {
    if (!countEl) return;
    countEl.textContent = String(currentIds().length);
  }

  list?.addEventListener("change", updateCount);

  btnAll?.addEventListener("click", () => {
    list.querySelectorAll('input[type="checkbox"]').forEach(c => c.checked = true);
    updateCount();
  });

  btnNone?.addEventListener("click", () => {
    list.querySelectorAll('input[type="checkbox"]').forEach(c => c.checked = false);
    updateCount();
  });

  btnApply?.addEventListener("click", () => {
    const ids = currentIds();
    const csrftoken = getCookie("csrftoken");
    fetch(actionUrl, {
      method: "POST",
      headers: {
        "X-Requested-With": "fetch",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-CSRFToken": csrftoken || "",
      },
      body: ids.map(id => `ids[]=${encodeURIComponent(id)}`).join("&"),
    })
      .then(r => r.json())
      .then(data => { if (data && data.ok) window.location.reload(); })
      .catch(() => {
        const form = document.createElement("form");
        form.method = "POST";
        form.action = actionUrl;
        const csrf = document.createElement("input");
        csrf.type = "hidden"; csrf.name = "csrfmiddlewaretoken"; csrf.value = csrftoken || "";
        form.appendChild(csrf);
        ids.forEach(id => {
          const input = document.createElement("input");
          input.type = "hidden"; input.name = "ids[]"; input.value = id;
          form.appendChild(input);
        });
        document.body.appendChild(form);
        form.submit();
      });
  });

  // init
  updateCount();
});

