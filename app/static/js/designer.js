(function () {
  const designer = document.getElementById("designer");
  if (!designer) return;

  const apiUrl = designer.dataset.api;
  let payload = JSON.parse(designer.dataset.payload || "{}");
  const chartHrp = document.getElementById("chart-hrp");
  const chartVrp = document.getElementById("chart-vrp");
  const tableBody = document.querySelector("#erp-table tbody");

  function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    if (match) return decodeURIComponent(match[2]);
    return null;
  }

  function drawPolar(canvas, angles, values) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);
    const cx = width / 2;
    const cy = height / 2;
    const maxVal = Math.max(...values, 1);

    ctx.strokeStyle = "#cbd5e1";
    ctx.lineWidth = 1;
    for (let r = 0.25; r <= 1; r += 0.25) {
      ctx.beginPath();
      ctx.arc(cx, cy, (Math.min(cx, cy) - 10) * r, 0, Math.PI * 2);
      ctx.stroke();
    }

    ctx.strokeStyle = "#0A4E8B";
    ctx.lineWidth = 2;
    ctx.beginPath();
    angles.forEach((angle, idx) => {
      const rad = (angle * Math.PI) / 180;
      const norm = values[idx] / maxVal;
      const radius = (Math.min(cx, cy) - 12) * norm;
      const x = cx + radius * Math.sin(rad);
      const y = cy - radius * Math.cos(rad);
      if (idx === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.closePath();
    ctx.stroke();
  }

  function updateTable(data) {
    if (!tableBody) return;
    let html = "";
    data.angles_deg.forEach((angle, idx) => {
      const erpW = data.erp_w[idx];
      const erpDbw = data.erp_dbw[idx];
      html += `<tr><td>${String(Math.round(angle) % 360).padStart(3, "0")}</td><td>${erpW.toFixed(2)}</td><td>${erpDbw.toFixed(2)}</td></tr>`;
      if ((idx + 1) % 24 === 0) {
        html += '<tr class="separator"><td colspan="3"></td></tr>';
      }
    });
    tableBody.innerHTML = html;
  }

  function refreshVisuals(data) {
    drawPolar(chartHrp, data.angles_deg, data.hrp_linear);
    drawPolar(chartVrp, data.vrp_angles_deg, data.vrp_linear);
    updateTable(data);
    designer.dataset.payload = JSON.stringify(data);
  }

  refreshVisuals(payload);

  let debounce; // avoid flooding
  designer.querySelectorAll('.controls input[type="range"]').forEach((input) => {
    input.addEventListener("input", () => {
      clearTimeout(debounce);
      debounce = setTimeout(() => submitPreview(), 150);
    });
  });

  function submitPreview() {
    const body = {};
    designer.querySelectorAll('.controls input[type="range"]').forEach((input) => {
      const value = input.value;
      body[input.name] = Number(value);
    });
    fetch(apiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrf_token") || ""
      },
      credentials: "same-origin",
      body: JSON.stringify(body)
    })
      .then((res) => res.ok ? res.json() : Promise.reject(res.statusText))
      .then((json) => {
        payload = json;
        refreshVisuals(json);
      })
      .catch((err) => console.warn("Erro ao atualizar prévia", err));
  }
})();
