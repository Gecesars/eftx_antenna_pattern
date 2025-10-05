document.addEventListener("DOMContentLoaded", () => {
  const openBtn = document.getElementById("open-antenna-datasheet-modal");
  const modal = document.getElementById("antenna-datasheet-modal");
  if (!openBtn || !modal) return;

  const closeEls = modal.querySelectorAll('[data-role="close"]');
  const statusEl = document.getElementById("antenna-datasheet-status");
  const fileInput = document.getElementById("antenna-datasheet-file");
  const previewForm = document.getElementById("antenna-datasheet-preview");
  const applyBtn = modal.querySelector('[data-role="apply"]');
  const mainForm = document.getElementById("antenna-form");
  let extracted = null;

  function openModal() { modal.hidden = false; modal.classList.add("open"); }
  function closeModal() { modal.classList.remove("open"); modal.hidden = true; statusEl.textContent = ""; applyBtn.disabled = true; previewForm.hidden = true; previewForm.reset(); if (fileInput) fileInput.value = ""; }

  openBtn.addEventListener("click", openModal);
  closeEls.forEach((el) => el.addEventListener("click", closeModal));

  fileInput.addEventListener("change", async (e) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    statusEl.textContent = "Enviando datasheet e extraindo...";
    const fd = new FormData();
    fd.append("file", file);
    const csrf = (mainForm.querySelector('input[name="csrf_token"]').value || "");
    try {
      const res = await fetch("/admin/antennas/parse-datasheet", { method: "POST", headers: { "X-CSRFToken": csrf }, body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Falha ao processar datasheet");
      extracted = data;
      statusEl.textContent = "Parâmetros extraídos. Revise e aplique.";
      for (const [k, v] of Object.entries(data)) {
        const input = previewForm.querySelector(`[name="${k}"]`);
        if (input) {
          if (input.tagName.toLowerCase() === "textarea") input.value = v ?? ""; else input.value = v ?? "";
        }
      }
      previewForm.hidden = false;
      applyBtn.disabled = false;
    } catch (err) {
      statusEl.textContent = String(err);
    }
  });

  function setField(form, name, value) {
    const el = form.querySelector(`[name="${name}"]`);
    if (!el) return;
    el.value = value ?? "";
  }

  applyBtn.addEventListener("click", () => {
    const fields = ["name","model_number","description","nominal_gain_dbd","polarization","frequency_min_mhz","frequency_max_mhz","manufacturer","datasheet_path","thumbnail_path"]; 
    fields.forEach((name) => {
      let val = extracted && Object.prototype.hasOwnProperty.call(extracted, name) ? extracted[name] : null;
      if (val == null) {
        const src = previewForm.querySelector(`[name="${name}"]`);
        val = src ? src.value : null;
      }
      setField(mainForm, name, val);
    });
    closeModal();
  });
});
