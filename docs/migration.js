/* Small static-hosting adaptations; original Webflow presentation is retained. */
document.documentElement.classList.add('wf-active');
document.addEventListener('submit', function (event) {
  const form = event.target.closest('form[data-static-unavailable]');
  if (!form) return;
  event.preventDefault();
  event.stopImmediatePropagation();
  const error = form.parentElement.querySelector('.w-form-fail');
  if (error) {
    error.textContent = 'This contact form is temporarily unavailable. Please email help@analytics.org.nz to get in touch.';
    error.style.display = 'block';
    error.setAttribute('role', 'alert');
  }
}, true);
