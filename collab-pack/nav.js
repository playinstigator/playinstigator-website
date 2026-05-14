/* ---------- Theme toggle (shared across pack) ---------- */
(function () {
  var root  = document.documentElement;
  var btn   = document.getElementById("themeToggle");
  var label = document.getElementById("themeLabel");
  var KEY   = "pi-theme";

  function getInitialTheme() {
    try {
      var saved = localStorage.getItem(KEY);
      if (saved === "light" || saved === "dark") return saved;
    } catch (e) {}
    if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
      return "dark";
    }
    return "light";
  }

  function labelFor(theme, lang) {
    if (lang === "zh") return theme === "dark" ? "浅色" : "深色";
    return theme === "dark" ? "Light" : "Dark";
  }
  window.__piThemeLabelFor = labelFor;

  function applyTheme(theme) {
    root.setAttribute("data-theme", theme);
    var currentLang = root.getAttribute("data-lang") || "en";
    if (label) label.textContent = labelFor(theme, currentLang);
    if (btn) btn.setAttribute("aria-label", theme === "dark" ? "Switch to light mode" : "Switch to dark mode");
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", theme === "dark" ? "#1C1917" : "#F9F5F1");
  }

  applyTheme(getInitialTheme());

  if (btn) {
    btn.addEventListener("click", function () {
      var current = root.getAttribute("data-theme");
      var next = current === "dark" ? "light" : "dark";
      applyTheme(next);
      try { localStorage.setItem(KEY, next); } catch (e) {}
    });
  }
})();

/* ---------- Language toggle (shared across pack) ---------- */
(function () {
  var root        = document.documentElement;
  var btn         = document.getElementById("langToggle");
  var label       = document.getElementById("langLabel");
  var themeLabel  = document.getElementById("themeLabel");
  var KEY         = "pi-lang";

  function getInitialLang() {
    try {
      var saved = localStorage.getItem(KEY);
      if (saved === "en" || saved === "zh") return saved;
    } catch (e) {}
    var nav = (navigator.language || "en").toLowerCase();
    if (nav.indexOf("zh") === 0) return "zh";
    return "en";
  }

  function applyLang(lang) {
    root.setAttribute("data-lang", lang);
    root.setAttribute("lang", lang === "zh" ? "zh-Hans" : "en");
    if (label) label.textContent = lang === "zh" ? "EN" : "中文";
    if (btn)   btn.setAttribute("aria-label", lang === "zh" ? "Switch to English" : "切换到中文");
    if (themeLabel && window.__piThemeLabelFor) {
      var currentTheme = root.getAttribute("data-theme") || "light";
      themeLabel.textContent = window.__piThemeLabelFor(currentTheme, lang);
    }
    var titleEl = document.querySelector("title");
    if (titleEl && titleEl.dataset && titleEl.dataset.en && titleEl.dataset.zh) {
      titleEl.textContent = lang === "zh" ? titleEl.dataset.zh : titleEl.dataset.en;
    }
  }

  applyLang(getInitialLang());

  if (btn) {
    btn.addEventListener("click", function () {
      var current = root.getAttribute("data-lang") || "en";
      var next = current === "zh" ? "en" : "zh";
      applyLang(next);
      try { localStorage.setItem(KEY, next); } catch (e) {}
    });
  }
})();

/* ---------- Back to top button ---------- */
(function () {
  var btn = document.getElementById("backToTop");
  if (!btn) return;
  var threshold = 400;
  function update() {
    if (window.scrollY > threshold) {
      btn.classList.add("visible");
    } else {
      btn.classList.remove("visible");
    }
  }
  window.addEventListener("scroll", update, { passive: true });
  update();
  btn.addEventListener("click", function () {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
})();

/* ---------- Mark current nav link ---------- */
(function () {
  var current = (document.body.getAttribute("data-page") || "").toLowerCase();
  if (!current) return;
  var links = document.querySelectorAll(".pack-nav a[data-page]");
  for (var i = 0; i < links.length; i++) {
    if (links[i].getAttribute("data-page").toLowerCase() === current) {
      links[i].classList.add("current");
    }
  }
})();
