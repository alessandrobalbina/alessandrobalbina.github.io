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

  // 5. Discrete Language Suggestion Banner (Safe DOM Creation without innerHTML)
  const isEnglishHome = window.location.pathname.endsWith('/') && !window.location.pathname.includes('/it');
  if (isEnglishHome) {
    const prefLang = localStorage.getItem('pref-lang');
    const userLang = (navigator.language || navigator.userLanguage || '').toLowerCase();
    
    if (!prefLang && userLang.startsWith('it')) {
      const toast = document.createElement('div');
      toast.className = 'lang-toast';
      toast.setAttribute('role', 'region');
      toast.setAttribute('aria-label', 'Selezione lingua');

      const p = document.createElement('p');
      p.className = 'lang-toast-text';
      p.appendChild(document.createTextNode('Preferisci visualizzare il sito in '));
      const strong = document.createElement('strong');
      strong.textContent = 'Italiano';
      p.appendChild(strong);
      p.appendChild(document.createTextNode('?'));

      const actions = document.createElement('div');
      actions.className = 'lang-toast-actions';

      const acceptBtn = document.createElement('a');
      acceptBtn.href = './it/';
      acceptBtn.className = 'lang-toast-btn';
      acceptBtn.id = 'lang-toast-accept';
      acceptBtn.textContent = "Passa all'italiano";

      const closeBtn = document.createElement('button');
      closeBtn.className = 'lang-toast-close';
      closeBtn.id = 'lang-toast-dismiss';
      closeBtn.setAttribute('aria-label', 'Chiudi avviso lingua');

      const svgNs = 'http://www.w3.org/2000/svg';
      const svg = document.createElementNS(svgNs, 'svg');
      svg.setAttribute('viewBox', '0 0 24 24');
      svg.setAttribute('fill', 'none');
      svg.setAttribute('stroke', 'currentColor');
      svg.setAttribute('stroke-width', '2');
      svg.setAttribute('stroke-linecap', 'round');
      svg.setAttribute('stroke-linejoin', 'round');

      const line1 = document.createElementNS(svgNs, 'line');
      line1.setAttribute('x1', '18'); line1.setAttribute('y1', '6');
      line1.setAttribute('x2', '6'); line1.setAttribute('y2', '18');
      const line2 = document.createElementNS(svgNs, 'line');
      line2.setAttribute('x1', '6'); line2.setAttribute('y1', '6');
      line2.setAttribute('x2', '18'); line2.setAttribute('y2', '18');
      svg.appendChild(line1);
      svg.appendChild(line2);
      closeBtn.appendChild(svg);

      actions.appendChild(acceptBtn);
      actions.appendChild(closeBtn);
      toast.appendChild(p);
      toast.appendChild(actions);
      document.body.appendChild(toast);

      acceptBtn.addEventListener('click', () => {
        localStorage.setItem('pref-lang', 'it');
      });

      closeBtn.addEventListener('click', () => {
        localStorage.setItem('pref-lang', 'en');
        toast.remove();
      });
    }
  }

  // 6. Security: Protected Email decoding (Safe DOM manipulation)
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

  // 7. 1-Click Citation Copy (Academic UX - Safe DOM manipulation without innerHTML)
  document.querySelectorAll('.pub-btn--cite').forEach(btn => {
    btn.addEventListener('click', async () => {
      const citation = btn.getAttribute('data-citation');
      if (!citation) return;
      try {
        await navigator.clipboard.writeText(citation);
        const textSpan = btn.querySelector('span');
        const originalText = textSpan ? textSpan.textContent : '';
        const isItalian = document.documentElement.lang === 'it' || window.location.pathname.includes('/it');
        
        btn.classList.add('is-copied');
        if (textSpan) {
          textSpan.textContent = isItalian ? 'Copiato!' : 'Copied!';
        }
        setTimeout(() => {
          btn.classList.remove('is-copied');
          if (textSpan) {
            textSpan.textContent = originalText;
          }
        }, 2200);
      } catch (err) {
        console.error('Clipboard copy failed:', err);
      }
    });
  });

  // 8. Thematic Publications Filtering
  const filterBtns = document.querySelectorAll('.pub-filter-btn');
  if (filterBtns.length > 0) {
    filterBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const filter = btn.getAttribute('data-filter');
        filterBtns.forEach(b => {
          b.classList.remove('is-active');
          b.setAttribute('aria-selected', 'false');
        });
        btn.classList.add('is-active');
        btn.setAttribute('aria-selected', 'true');

        const pubItems = document.querySelectorAll('.pub-list li');
        pubItems.forEach(item => {
          const categories = (item.getAttribute('data-category') || '').split(' ');
          if (filter === 'all' || categories.includes(filter)) {
            item.classList.remove('is-hidden');
          } else {
            item.classList.add('is-hidden');
          }
        });

        // Hide empty categories
        document.querySelectorAll('.pub-category').forEach(cat => {
          const visibleItems = cat.querySelectorAll('.pub-list li:not(.is-hidden)');
          if (visibleItems.length === 0) {
            cat.classList.add('is-hidden');
          } else {
            cat.classList.remove('is-hidden');
          }
        });
      });
    });
  }
});