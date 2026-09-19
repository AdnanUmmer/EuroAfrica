(() => {
  const form = document.getElementById('enquiry-form');
  if (!form) return;
  const button = form.querySelector('button[type="submit"]');
  const status = document.getElementById('submission-status');
  const verification = document.getElementById('enquiry-verification');
  if (verification) {
    window.renderEnquiryChallenge = () => {
      window.turnstile.render(verification, {
        sitekey: verification.dataset.sitekey,
        action: 'enquiry',
        size: verification.clientWidth < 300 ? 'compact' : 'flexible',
        theme: 'light'
      });
    };
    const script = document.createElement('script');
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit&onload=renderEnquiryChallenge';
    script.async = true;
    script.onerror = () => { status.textContent = 'The security check could not load. Please reload this page and try again.'; };
    document.head.appendChild(script);
  }
  let pending = false;
  form.addEventListener('submit', event => {
    if (verification && !form.querySelector('[name="cf-turnstile-response"]')?.value) {
      event.preventDefault();
      status.textContent = 'Please wait for the security check to complete, then try again.';
      return;
    }
    if (pending) { event.preventDefault(); return; }
    pending = true;
    button.disabled = true;
    form.setAttribute('aria-busy', 'true');
    status.textContent = 'Sending your enquiry…';
  });
  window.addEventListener('pageshow', () => {
    if (pending) {
      pending = false;
      button.disabled = false;
      form.removeAttribute('aria-busy');
      status.textContent = '';
    }
  });
  document.getElementById('form-errors')?.focus();
})();
