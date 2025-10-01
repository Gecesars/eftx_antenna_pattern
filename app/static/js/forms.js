document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".password-toggle").forEach((button) => {
    const srOnly = button.querySelector(".sr-only");
    button.addEventListener("click", () => {
      const targetId = button.dataset.target;
      const input = document.getElementById(targetId);
      if (!input) {
        return;
      }
      const isHidden = input.type === "password";
      input.type = isHidden ? "text" : "password";
      button.setAttribute("aria-pressed", String(isHidden));
      button.classList.toggle("is-active", isHidden);
      if (srOnly) {
        srOnly.textContent = isHidden ? "Ocultar senha" : "Mostrar senha";
      }
    });
  });

  const dialogOk = document.getElementById("success-dialog-ok");
  if (dialogOk) {
    dialogOk.addEventListener("click", () => {
      const redirectUrl = dialogOk.dataset.redirect;
      window.location.href = redirectUrl || "/";
    });
  }
});
