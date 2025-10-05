document.addEventListener("DOMContentLoaded", () => {
  const openBtn = document.getElementById("open-composition-modal");
  const modal = document.getElementById("composition-modal");
  if (!openBtn || !modal) return;

  const projectForm = document.getElementById("project-form");
  const closeEls = modal.querySelectorAll('[data-role="close"]');
  const applyBtn = modal.querySelector('[data-role="apply"]');

  const vSvg = document.getElementById("vertical-svg");
  const hSvg = document.getElementById("horizontal-svg");

  const vCountInput = document.getElementById("v_count_input");
  const vSpacingInput = document.getElementById("v_spacing_input");
  const vTiltInput = document.getElementById("v_tilt_input");
  const hCountInput = document.getElementById("h_count_input");
  const hSpacingInput = document.getElementById("h_spacing_input");
  const hStepInput = document.getElementById("h_step_input");

  function openModal() {
    // seed from current form
    vCountInput.value = projectForm.querySelector('[name="v_count"]').value || 1;
    vSpacingInput.value = projectForm.querySelector('[name="v_spacing_m"]').value || 0.5;
    vTiltInput.value = projectForm.querySelector('[name="v_tilt_deg"]').value || 0.0;
    hCountInput.value = projectForm.querySelector('[name="h_count"]').value || 1;
    hSpacingInput.value = projectForm.querySelector('[name="h_spacing_m"]').value || 0.5;
    hStepInput.value = projectForm.querySelector('[name="h_step_deg"]').value || 0.0;
    redraw();
    modal.hidden = false; modal.classList.add("open");
  }
  function closeModal() { modal.classList.remove("open"); modal.hidden = true; }

  openBtn.addEventListener("click", openModal);
  closeEls.forEach((el) => el.addEventListener("click", closeModal));

  [vCountInput, vSpacingInput, vTiltInput].forEach((el) => el.addEventListener("input", redraw));
  [hCountInput, hSpacingInput, hStepInput].forEach((el) => el.addEventListener("input", redraw));

  function clearSvg(svg) { while (svg.firstChild) svg.removeChild(svg.firstChild); }

  function drawVertical() {
    clearSvg(vSvg);
    const count = Math.max(parseInt(vCountInput.value || 1, 10), 1);
    const spacing = parseFloat(vSpacingInput.value || 0.5);
    const tilt = parseFloat(vTiltInput.value || 0);
    const width = 200, height = 300, margin = 20;
    const pitch = count > 1 ? Math.max(24, spacing * 40) : 0;
    // mastro
    const mast = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    mast.setAttribute("x", String(width/2 - 4)); mast.setAttribute("y", String(margin/2));
    mast.setAttribute("width", "8"); mast.setAttribute("height", String(height - margin)); mast.setAttribute("fill", "#8a8a8a");
    vSvg.appendChild(mast);
    for (let i = 0; i < count; i++) {
      const y = margin + i * pitch;
      const el = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      el.setAttribute("x", String(width/2 - 12));
      el.setAttribute("y", String(y - 10));
      el.setAttribute("width", "24");
      el.setAttribute("height", "20");
      el.setAttribute("fill", "#ffcccc");
      el.setAttribute("stroke", "#cc0000");
      el.setAttribute("stroke-width", "1");
      vSvg.appendChild(el);
    }
    // cota de espaçamento (centro a centro entre os dois primeiros, se existirem)
    if (count >= 2) {
      const c0 = margin;
      const c1 = margin + pitch;
      const dim = document.createElementNS("http://www.w3.org/2000/svg", "line");
      dim.setAttribute("x1", String(width/2 + 24)); dim.setAttribute("y1", String(c0));
      dim.setAttribute("x2", String(width/2 + 24)); dim.setAttribute("y2", String(c1));
      dim.setAttribute("stroke", "#444"); dim.setAttribute("stroke-width", "1");
      vSvg.appendChild(dim);
      const txt = document.createElementNS("http://www.w3.org/2000/svg", "text");
      txt.setAttribute("x", String(width/2 + 28)); txt.setAttribute("y", String((c0 + c1)/2)); txt.setAttribute("fill", "#444");
      txt.setAttribute("transform", `rotate(-90 ${width/2 + 28} ${(c0 + c1)/2})`);
      txt.textContent = `Δv = ${spacing.toFixed(3)} m`;
      vSvg.appendChild(txt);
    }
    // seta de tilt saindo do centro
    const centerY = margin + (Math.max(count - 1, 0) * pitch) / 2;
    const baseX = width/2 - 50;
    const len = 60; const rad = (tilt * Math.PI) / 180;
    const x2 = baseX + len * Math.cos(-rad); const y2 = centerY + len * Math.sin(-rad);
    const arrow = document.createElementNS("http://www.w3.org/2000/svg", "line");
    arrow.setAttribute("x1", String(baseX)); arrow.setAttribute("y1", String(centerY));
    arrow.setAttribute("x2", String(x2)); arrow.setAttribute("y2", String(y2));
    arrow.setAttribute("stroke", "#ff7a00"); arrow.setAttribute("stroke-width", "3");
    vSvg.appendChild(arrow);
    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", String(x2 + 5)); label.setAttribute("y", String(y2));
    label.setAttribute("fill", "#ff7a00"); label.textContent = `${tilt.toFixed(1)}°`;
    vSvg.appendChild(label);
  }

  function drawHorizontal() {
    clearSvg(hSvg);
    const count = Math.max(parseInt(hCountInput.value || 1, 10), 1);
    const step = parseFloat(hStepInput.value || 0);
    const spacing = parseFloat(hSpacingInput.value || 0.5);
    const size = 300; const cx = size/2; const cy = size/2; const R = 90;
    // ring
    const ring = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    ring.setAttribute("cx", String(cx)); ring.setAttribute("cy", String(cy)); ring.setAttribute("r", String(R));
    ring.setAttribute("fill", "none"); ring.setAttribute("stroke", "#8a8a8a"); ring.setAttribute("stroke-dasharray", "4,4");
    hSvg.appendChild(ring);
    for (let i = 0; i < count; i++) {
      const ang = (i * (360 / count) + i * step) * Math.PI / 180;
      const x = cx + R * Math.cos(ang);
      const y = cy + R * Math.sin(ang);
      const el = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      el.setAttribute("x", String(x - 10)); el.setAttribute("y", String(y - 8));
      el.setAttribute("width", "20"); el.setAttribute("height", "16");
      el.setAttribute("fill", "#ffcccc");
      el.setAttribute("stroke", "#cc0000"); el.setAttribute("stroke-width", "1");
      hSvg.appendChild(el);
      // angulo
      const lx = (R + 20) * Math.cos(ang); const ly = (R + 20) * Math.sin(ang);
      const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
      label.setAttribute("x", String(cx + lx)); label.setAttribute("y", String(cy + ly)); label.setAttribute("fill", "#555");
      label.setAttribute("text-anchor", "middle"); label.setAttribute("dominant-baseline", "middle");
      label.textContent = `${(i*(360.0/count)+i*step)%360|0}°`;
      hSvg.appendChild(label);
    }
    const lbl = document.createElementNS("http://www.w3.org/2000/svg", "text");
    lbl.setAttribute("x", String(cx - 40)); lbl.setAttribute("y", String(cy - R - 10)); lbl.setAttribute("fill", "#555");
    const Rm = spacing * count / (2 * Math.PI);
    lbl.textContent = `N = ${count}, step = ${step}°, R = ${Rm.toFixed(3)} m`;
    hSvg.appendChild(lbl);
  }

  function redraw() { drawVertical(); drawHorizontal(); }

  applyBtn.addEventListener("click", () => {
    const set = (name, value) => { const el = projectForm.querySelector(`[name="${name}"]`); if (el) el.value = value; };
    set("v_count", vCountInput.value);
    set("v_spacing_m", vSpacingInput.value);
    set("v_tilt_deg", vTiltInput.value);
    set("h_count", hCountInput.value);
    set("h_spacing_m", hSpacingInput.value);
    set("h_step_deg", hStepInput.value);
    closeModal();
  });
});
