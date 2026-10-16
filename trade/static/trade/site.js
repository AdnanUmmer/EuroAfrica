/* Progressive enhancement: navigation and content also work without JavaScript. */
(() => {
  const header = document.querySelector('.header');
  const menu = document.querySelector('.mobile-nav');
  const updateHeader = () => header?.classList.toggle('is-scrolled', window.scrollY > 24);
  updateHeader();
  window.addEventListener('scroll', updateHeader, { passive: true });
  if (menu) {
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && menu.open) {
        menu.open = false;
        menu.querySelector('summary').focus();
      }
    });
    document.addEventListener('click', event => {
      if (menu.open && !menu.contains(event.target)) menu.open = false;
    });
    menu.querySelectorAll('a').forEach(link => link.addEventListener('click', () => { menu.open = false; }));
  }
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  if (!motion.matches && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.06 });
    document.querySelectorAll('.section-heading, .direction-panel, .category-card, .about-strip, .editorial, .contact-banner').forEach(element => {
      // Animate only on entry; never hide content if scripts are delayed or disabled.
      observer.observe(element);
    });
  }
})();
