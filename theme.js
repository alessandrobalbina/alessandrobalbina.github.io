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
  // 1. Language Toggle tracking
  document.querySelectorAll('.lang-toggle').forEach(toggle => {
    toggle.addEventListener('click', () => {
      const href = toggle.getAttribute('href');
      if (href && (href.includes('/it') || href.includes('it/'))) {
        localStorage.setItem('pref-lang', 'it');
      } else {
        localStorage.setItem('pref-lang', 'en');
      }
    });
  });

  // 2. Theme Toggle
  const toggleButton = document.getElementById('theme-toggle');
  if (toggleButton) {
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
  }

  // 3. Dropdown Menu (Touch & Click Support + ARIA accessibility)
  const dropdown = document.querySelector('.dropdown');
  const dropdownTrigger = document.querySelector('.dropdown-trigger');
  if (dropdown && dropdownTrigger) {
    const closeDropdown = () => {
      dropdown.classList.remove('is-open');
      dropdownTrigger.setAttribute('aria-expanded', 'false');
    };

    dropdownTrigger.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = dropdown.classList.toggle('is-open');
      dropdownTrigger.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });

    document.addEventListener('click', (e) => {
      if (!dropdown.contains(e.target)) {
        closeDropdown();
      }
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && dropdown.classList.contains('is-open')) {
        closeDropdown();
        dropdownTrigger.focus();
      }
    });
  }

  // 4. Hide/show navigation on scroll down/up
  let lastScrollY = window.scrollY;
  const topbar = document.querySelector('.topbar');
  const backToTopBtn = document.querySelector('.back-to-top');

  window.addEventListener('scroll', () => {
    const currentScrollY = window.scrollY;

    // Topbar visibility
    if (topbar) {
      if (currentScrollY > lastScrollY && currentScrollY > 80) {
        topbar.classList.add('topbar--hidden');
      } else {
        topbar.classList.remove('topbar--hidden');
      }
    }

    // Back to top button visibility (> 350px)
    if (backToTopBtn) {
      if (currentScrollY > 350) {
        backToTopBtn.classList.add('is-visible');
      } else {
        backToTopBtn.classList.remove('is-visible');
      }
    }

    lastScrollY = currentScrollY;
  }, { passive: true });

  // Back to top click
  if (backToTopBtn) {
    backToTopBtn.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // 5. Discrete Language Suggestion Banner (replaces aggressive auto-redirect)
  const isEnglishHome = window.location.pathname.endsWith('/') && !window.location.pathname.includes('/it');
  if (isEnglishHome) {
    const prefLang = localStorage.getItem('pref-lang');
    const userLang = (navigator.language || navigator.userLanguage || '').toLowerCase();
    
    if (!prefLang && userLang.startsWith('it')) {
      const toast = document.createElement('div');
      toast.className = 'lang-toast';
      toast.setAttribute('role', 'region');
      toast.setAttribute('aria-label', 'Selezione lingua');
      toast.innerHTML = `
        <p class="lang-toast-text">Preferisci visualizzare il sito in <strong>Italiano</strong>?</p>
        <div class="lang-toast-actions">
          <a href="./it/" class="lang-toast-btn" id="lang-toast-accept">Passa all'italiano</a>
          <button class="lang-toast-close" id="lang-toast-dismiss" aria-label="Chiudi avviso lingua">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
      `;
      document.body.appendChild(toast);

      document.getElementById('lang-toast-accept')?.addEventListener('click', () => {
        localStorage.setItem('pref-lang', 'it');
      });

      document.getElementById('lang-toast-dismiss')?.addEventListener('click', () => {
        localStorage.setItem('pref-lang', 'en');
        toast.remove();
      });
    }
  }

  // 6. Security: Protected Email decoding
  document.querySelectorAll('.protected-email').forEach(el => {
    const user = el.getAttribute('data-user');
    const domain = el.getAttribute('data-domain');
    if (user && domain) {
      const email = `${user}@${domain}`;
      el.textContent = email;
      if (el.tagName.toLowerCase() === 'a') {
        el.setAttribute('href', `mailto:${email}`);
      }
    }
  });
});
