(function () {
  var THEME_KEY = 'ezzaouia-theme';

  function updateBtn(theme) {
    var btn = document.getElementById('theme-toggle');
    if (!btn) return;
    var sun = btn.querySelector('.icon-sun');
    var moon = btn.querySelector('.icon-moon');
    if (theme === 'dark') {
      if (sun) sun.style.display = 'block';
      if (moon) moon.style.display = 'none';
      btn.title = 'Switch to light mode';
    } else {
      if (sun) sun.style.display = 'none';
      if (moon) moon.style.display = 'block';
      btn.title = 'Switch to dark mode';
    }
  }

  window.toggleTheme = function () {
    var current = document.documentElement.getAttribute('data-theme') || 'dark';
    var next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem(THEME_KEY, next);
    updateBtn(next);
  };

  document.addEventListener('DOMContentLoaded', function () {
    updateBtn(document.documentElement.getAttribute('data-theme') || 'dark');
  });
}());
