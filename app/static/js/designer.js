(function () {
  const designer = document.getElementById('designer');
  if (!designer) return;

  const apiUrl = designer.dataset.api;
  const SPEED_OF_LIGHT = 299792458;
  const frequencyMhz = Number(designer.dataset.frequency || designer.dataset.frequencyMhz || 0);
  let payload = JSON.parse(designer.dataset.payload || '{}');
  const chartHrp = document.getElementById('chart-hrp');
  const chartVrp = document.getElementById('chart-vrp');
  const tableBody = document.querySelector('#erp-table tbody');
  const betaDisplay = document.getElementById('beta-display');
  const betaInput = designer.querySelector('input[name="v_beta_deg"]');
  const tiltInput = designer.querySelector('input[name="v_tilt_deg"]');
  const spacingInput = designer.querySelector('input[name="v_spacing_m"]');

  function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    if (match) return decodeURIComponent(match[2]);
    return null;
  }

  function computeBetaDegrees(tiltDeg, spacing) {
    if (!Number.isFinite(tiltDeg) || !Number.isFinite(spacing) || spacing === 0 || frequencyMhz <= 0) {
      return 0;
    }
    const wavelength = SPEED_OF_LIGHT / (frequencyMhz * 1_000_000);
    const betaRad = (-2 * Math.PI * spacing * Math.sin((tiltDeg * Math.PI) / 180)) / wavelength;
    return (betaRad * 180) / Math.PI;
  }

  function updateBetaDisplay() {
    if (!betaInput) return;
    const spacing = spacingInput ? Number(spacingInput.value) : 0;
    const tilt = tiltInput ? Number(tiltInput.value) : 0;
    const betaDeg = computeBetaDegrees(tilt, spacing);
    betaInput.value = Number.isFinite(betaDeg) ? betaDeg.toFixed(3) : '0';
    if (betaDisplay) {
      betaDisplay.textContent = Number.isFinite(betaDeg) ? betaDeg.toFixed(2) : '0.00';
    }
  }

  function drawPolar(canvas, angles, values) {
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);
    const cx = width / 2;
    const cy = height / 2;
    const maxVal = Math.max(...values, 1);

    ctx.strokeStyle = '#cbd5e1';
    ctx.lineWidth = 1;
    for (let r = 0.25; r <= 1; r += 0.25) {
      ctx.beginPath();
      ctx.arc(cx, cy, (Math.min(cx, cy) - 10) * r, 0, Math.PI * 2);
      ctx.stroke();
    }

    ctx.strokeStyle = '#0A4E8B';
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
    let html = '';
    data.angles_deg.forEach((angle, idx) => {
      const erpW = data.erp_w[idx];
      const erpDbw = data.erp_dbw[idx];
      html += `<tr><td>${String(Math.round(angle) % 360).padStart(3, '0')}</td><td>${erpW.toFixed(2)}</td><td>${erpDbw.toFixed(2)}</td></tr>`;
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
  updateBetaDisplay();

  let debounce;
  designer.querySelectorAll('.controls input[type="range"]').forEach((input) => {
    if (input.name === 'v_beta_deg') {
      input.setAttribute('disabled', 'disabled');
    }
    input.addEventListener('input', () => {
      if (input.name === 'v_tilt_deg' || input.name === 'v_spacing_m') {
        updateBetaDisplay();
      }
      clearTimeout(debounce);
      debounce = setTimeout(() => submitPreview(), 150);
    });
  });

  function submitPreview() {
    updateBetaDisplay();
    const body = {};
    designer.querySelectorAll('.controls input[type="range"]').forEach((input) => {
      body[input.name] = Number(input.value);
    });
    fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrf_token') || ''
      },
      credentials: 'same-origin',
      body: JSON.stringify(body)
    })
      .then((res) => (res.ok ? res.json() : Promise.reject(res.statusText)))
      .then((json) => {
        payload = json;
        refreshVisuals(json);
      })
      .catch((err) => console.warn('Erro ao atualizar previa', err));
  }
})();
