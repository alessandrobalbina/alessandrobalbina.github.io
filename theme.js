(function () {
  const savedTheme = localStorage.getItem('theme');
  const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  if (savedTheme === 'dark' || (!savedTheme && systemPrefersDark)) {
    document.documentElement.setAttribute('data-theme', 'dark');
  } else {
    document.documentElement.setAttribute('data-theme', 'light');
  }
})();

document.addEventListener('DOMContentLoaded', () => {
  const toggleButton = document.getElementById('theme-toggle');
  if (!toggleButton) return;

  toggleButton.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
  });

  // Sync with system theme changes if no explicit user choice is saved
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    if (!localStorage.getItem('theme')) {
      const newTheme = e.matches ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', newTheme);
    }
  });

  // Hide/show navigation on scroll down/up
  let lastScrollY = window.scrollY;
  window.addEventListener('scroll', () => {
    const topbar = document.querySelector('.topbar');
    if (!topbar) return;

    if (window.scrollY > lastScrollY && window.scrollY > 80) {
      topbar.classList.add('topbar--hidden');
    } else {
      topbar.classList.remove('topbar--hidden');
    }
    lastScrollY = window.scrollY;
  }, { passive: true });
});
