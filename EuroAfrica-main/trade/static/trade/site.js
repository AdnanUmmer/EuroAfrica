/* Menus and content remain usable when JavaScript is unavailable. */
(() => {
  const header = document.querySelector('.header');
  const updateHeader = () => header?.classList.toggle('is-scrolled', scrollY > 40);
  updateHeader();
  window.addEventListener('scroll', updateHeader, {passive:true});
  const menus = [...document.querySelectorAll('.nav-disclosure')];
  menus.forEach(menu => {
    menu.addEventListener('toggle', () => {
      if (menu.open) menus.filter(other => other !== menu).forEach(other => {other.open=false;});
    });
    menu.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {menu.open=false;}));
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') menus.filter(menu => menu.open).forEach(menu => {menu.open=false;menu.querySelector('summary').focus();});
  });
  document.addEventListener('click', event => menus.filter(menu => menu.open && !menu.contains(event.target)).forEach(menu => {menu.open=false;}));
  if (!matchMedia('(prefers-reduced-motion: reduce)').matches && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) {entry.target.classList.add('is-visible');observer.unobserve(entry.target);}
    }), {threshold:.08});
    document.querySelectorAll('.intro-copy,.section-heading,.corridor-panel,.sector-row,.strength-grid article,.market-copy,.editorial,.story-opening,.contact-banner').forEach(el => observer.observe(el));
  }
})();
