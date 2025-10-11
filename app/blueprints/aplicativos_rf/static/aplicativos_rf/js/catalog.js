document.addEventListener('DOMContentLoaded', () => {
  const filterButtons = Array.from(document.querySelectorAll('.rf-filter-group .list-group-item'));
  const searchInput = document.querySelector('#calculator-search');
  const cards = Array.from(document.querySelectorAll('.calculator-card'));

  filterButtons.forEach((button) => {
    button.addEventListener('click', (event) => {
      event.preventDefault();
      const target = button.getAttribute('data-target');
      if (!target) {
        return;
      }
      const section = document.getElementById(target);
      if (section) {
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
      filterButtons.forEach((btn) => btn.classList.remove('active'));
      button.classList.add('active');
    });
  });

  if (searchInput) {
    searchInput.addEventListener('input', () => {
      const term = searchInput.value.trim().toLowerCase();
      const visibleSections = new Map();
      cards.forEach((card) => {
        const title = card.getAttribute('data-title') || '';
        const match = !term || title.includes(term);
        card.closest('.calculator-wrapper').classList.toggle('d-none', !match);
        const section = card.closest('.rf-category-section');
        if (section) {
          const list = visibleSections.get(section.id) || { total: 0, visible: 0, element: section };
          list.total += 1;
          if (match) {
            list.visible += 1;
          }
          visibleSections.set(section.id, list);
        }
      });
      visibleSections.forEach(({ total, visible, element }) => {
        element.classList.toggle('d-none', visible === 0 && total > 0);
      });
    });
  }
});
