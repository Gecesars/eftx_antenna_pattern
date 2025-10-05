document.addEventListener("DOMContentLoaded", () => {
  const openBtn = document.getElementById("open-datasheet-modal");
  const modal = document.getElementById("datasheet-modal");
  if (!openBtn || !modal) return;

  const closeEls = modal.querySelectorAll('[data-role="close"]');
  const statusEl = document.getElementById("datasheet-status");
  const fileInput = document.getElementById("datasheet-file");
  const previewForm = document.getElementById("datasheet-preview");
  const applyBtn = modal.querySelector('[data-role="apply"]');
  const mainForm = document.getElementById("cable-form");

  function openModal() {
    modal.hidden = false;
    modal.classList.add("open");
  }
  function closeModal() {
    modal.classList.remove("open");
    modal.hidden = true;
    statusEl.textContent = "";
    previewForm.hidden = true;
    applyBtn.disabled = true;
    previewForm.reset();
    if (fileInput) fileInput.value = "";
  }

  openBtn.addEventListener("click", openModal);
  closeEls.forEach((el) => el.addEventListener("click", closeModal));

  let extractedData = null;

  async function uploadAndExtract(file) {
    if (!file) return;
    statusEl.textContent = "Enviando datasheet e extraindo...";
    applyBtn.disabled = true;
    previewForm.hidden = true;

    const formData = new FormData();
    formData.append("file", file);

    const csrf = (mainForm.querySelector('input[name="csrf_token"]').value || "");
    try {
      const res = await fetch("/admin/cables/parse-datasheet", {
        method: "POST",
        headers: { "X-CSRFToken": csrf },
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || "Falha ao processar datasheet");
      }
      statusEl.textContent = "Parâmetros extraídos. Revise e aplique.";
      extractedData = data;
      // Fill preview form
      for (const [k, v] of Object.entries(data)) {
        const input = previewForm.querySelector(`[name="${k}"]`);
        if (input) {
          if (input.tagName.toLowerCase() === "textarea") {
            input.value = typeof v === "object" ? JSON.stringify(v, null, 2) : (v ?? "");
          } else {
            input.value = v ?? "";
          }
        }
      }
      previewForm.hidden = false;
      applyBtn.disabled = false;
    } catch (err) {
      statusEl.textContent = String(err);
    }
  }

  fileInput.addEventListener("change", (e) => {
    const file = e.target.files && e.target.files[0];
    if (file) uploadAndExtract(file);
  });

  function setField(form, name, value) {
    let el = form.querySelector(`[name="${name}"]`);
    if (!el) {
      // fallback por id
      el = form.querySelector(`#${name}`);
    }
    if (!el) return;
    if (el.tagName.toLowerCase() === "textarea") {
      el.value = typeof value === "object" ? JSON.stringify(value, null, 2) : (value ?? "");
    } else {
      el.value = value ?? "";
    }
  }

  applyBtn.addEventListener("click", () => {
    const fields = [
      "display_name","model_code","size_inch","impedance_ohms","manufacturer","notes",
      "frequency_min_mhz","frequency_max_mhz","velocity_factor","max_power_w","min_bend_radius_mm","outer_diameter_mm",
      "weight_kg_per_km","vswr_max","shielding_db","temperature_min_c","temperature_max_c","conductor_material",
      "dielectric_material","jacket_material","shielding_type","conductor_diameter_mm","dielectric_diameter_mm",
      "attenuation_db_per_100m_curve","datasheet_path"
    ];
    // Preferir dados extraídos direto, com fallback para o preview
    fields.forEach((name) => {
      let val = extractedData && Object.prototype.hasOwnProperty.call(extractedData, name)
        ? extractedData[name]
        : null;
      if (val == null) {
        const src = previewForm.querySelector(`[name="${name}"]`);
        val = src ? src.value : null;
      }
      setField(mainForm, name, val);
    });
    closeModal();
  });
});
