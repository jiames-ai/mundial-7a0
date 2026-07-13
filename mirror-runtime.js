(() => {
  const locales = ["en", "de", "ja", "pt", "es", "fr", "it", "tr", "zh"];
  const localeNames = {
    en: "English",
    de: "Deutsch",
    ja: "日本語",
    pt: "Português",
    es: "Español",
    fr: "Français",
    it: "Italiano",
    tr: "Türkçe",
    zh: "简体中文",
  };
  const legacyRoutes = {
    privacidad: ["es", "privacy"],
    terminos: ["es", "terms"],
    "aviso-legal": ["es", "disclaimer"],
    privacidade: ["pt", "privacy"],
    termos: ["pt", "terms"],
    "aviso-legal-pt": ["pt", "disclaimer"],
  };
  const adSelector = [
    ".ad-break",
    ".ad-page-rail",
    ".ad-placement",
    ".adsterra-code",
    '[aria-label="Advertisement"]',
    'script[src*="googlesyndication"]',
    'script[src*="effectivecpmnetwork"]',
    'script[src*="highperformanceformat"]',
    'script[src*="googletagmanager"]',
    'script[src*="cloudflareinsights"]',
    'link[href*="googletagmanager"]',
    'meta[name="google-adsense-account"]',
  ].join(",");
  const attributeNames = ["aria-label", "title", "alt", "placeholder"];
  const positionCodes = {
    en: { GOL: "GK", LD: "RB", ZAG: "CB", LE: "LB", VOL: "DM", MEI: "AM", MD: "RM", ME: "LM", PD: "RW", CA: "ST", PE: "LW" },
    de: { GOL: "TW", LD: "RV", ZAG: "IV", LE: "LV", VOL: "DM", MEI: "OM", MD: "RM", ME: "LM", PD: "RA", CA: "ST", PE: "LA" },
    ja: { GOL: "GK", LD: "RSB", ZAG: "CB", LE: "LSB", VOL: "DMF", MEI: "OMF", MD: "RMF", ME: "LMF", PD: "RWG", CA: "CF", PE: "LWG" },
    pt: { GOL: "GOL", LD: "LD", ZAG: "ZAG", LE: "LE", VOL: "VOL", MEI: "MEI", MD: "MD", ME: "ME", PD: "PD", CA: "CA", PE: "PE" },
    es: { GOL: "POR", LD: "LD", ZAG: "DFC", LE: "LI", VOL: "MCD", MEI: "MCO", MD: "MD", ME: "MI", PD: "ED", CA: "DC", PE: "EI" },
    fr: { GOL: "GB", LD: "DD", ZAG: "DC", LE: "DG", VOL: "MDC", MEI: "MOC", MD: "MD", ME: "MG", PD: "AD", CA: "BU", PE: "AG" },
    it: { GOL: "POR", LD: "TD", ZAG: "DC", LE: "TS", VOL: "MED", MEI: "TRQ", MD: "ED", ME: "ES", PD: "AD", CA: "ATT", PE: "AS" },
    tr: { GOL: "KL", LD: "SĞB", ZAG: "STP", LE: "SLB", VOL: "DOS", MEI: "OOS", MD: "SĞO", ME: "SLO", PD: "SĞK", CA: "SF", PE: "SLK" },
    zh: { GOL: "门将", LD: "右后卫", ZAG: "中后卫", LE: "左后卫", VOL: "后腰", MEI: "前腰", MD: "右中场", ME: "左中场", PD: "右边锋", CA: "中锋", PE: "左边锋" },
  };
  let catalog = null;
  let currentLocale = "en";
  let translating = false;

  function routeState() {
    const parts = location.pathname.split("/").filter(Boolean);
    if (parts.length && locales.includes(parts[0])) {
      return { locale: parts[0], page: parts[1] || "home" };
    }
    if (parts.length && legacyRoutes[parts[0]]) {
      const [locale, page] = legacyRoutes[parts[0]];
      return { locale, page };
    }
    const page = ["privacy", "terms", "contact", "disclaimer"].includes(parts[0])
      ? parts[0]
      : "home";
    return { locale: "en", page };
  }

  function routeFor(locale, page) {
    if (page === "home") return locale === "en" ? "/" : `/${locale}/`;
    return `/${locale}/${page}/`;
  }

  function removeAds(root = document) {
    root.querySelectorAll?.(adSelector).forEach((element) => element.remove());
  }

  function normalize(value) {
    return value.replace(/\s+/g, " ").trim();
  }

  function translateTemplate(value) {
    if (!catalog) return null;
    for (const [source, translated] of Object.entries(catalog.strings)) {
      const placeholders = [...source.matchAll(/\{([a-zA-Z0-9_]+)\}/g)].map((match) => match[1]);
      if (!placeholders.length) continue;
      const escaped = source
        .split(/\{[a-zA-Z0-9_]+\}/)
        .map((part) => part.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
      const expression = new RegExp(`^${escaped.join("(.+?)")}$`);
      const match = value.match(expression);
      if (!match) continue;
      let result = translated;
      placeholders.forEach((name, index) => {
        result = result.replaceAll(`{${name}}`, match[index + 1]);
      });
      return result;
    }
    return null;
  }

  function translatedValue(value) {
    const key = normalize(value);
    if (!key || !catalog) return null;
    const direct = catalog.strings[key] || translateTemplate(key);
    if (direct) return direct;
    const codes = key.split("/");
    const dictionary = positionCodes[currentLocale];
    if (codes.length > 1 && codes.every((code) => dictionary[code])) {
      return codes.map((code) => dictionary[code]).join("/");
    }
    return null;
  }

  function translateTextNode(node) {
    const raw = node.nodeValue || "";
    const translated = translatedValue(raw);
    if (!translated || normalize(raw) === translated) return;
    const leading = raw.match(/^\s*/)?.[0] || "";
    const trailing = raw.match(/\s*$/)?.[0] || "";
    node.nodeValue = `${leading}${translated}${trailing}`;
  }

  function translateElement(element) {
    for (const attribute of attributeNames) {
      const value = element.getAttribute?.(attribute);
      const translated = value && translatedValue(value);
      if (translated) element.setAttribute(attribute, translated);
    }
    if (element.matches?.('meta[name="description"], meta[property="og:title"], meta[property="og:description"], meta[name="twitter:title"], meta[name="twitter:description"]')) {
      const value = element.getAttribute("content");
      const translated = value && translatedValue(value);
      if (translated) element.setAttribute("content", translated);
    }
  }

  function translateTree(root = document) {
    if (!catalog || translating) return;
    translating = true;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) {
      const parent = walker.currentNode.parentElement;
      if (parent && !["SCRIPT", "STYLE", "NOSCRIPT", "OPTION"].includes(parent.tagName)) {
        nodes.push(walker.currentNode);
      }
    }
    nodes.forEach(translateTextNode);
    if (root.nodeType === Node.ELEMENT_NODE) translateElement(root);
    root.querySelectorAll?.("*").forEach(translateElement);
    const translatedTitle = translatedValue(document.title);
    if (translatedTitle) document.title = translatedTitle;
    translating = false;
  }

  function installLanguageSelect() {
    const state = routeState();
    const candidates = document.querySelectorAll("label.language-select, select.language-select");
    candidates.forEach((candidate) => {
      if (candidate.tagName === "SELECT" && candidate.dataset.mirrorSelect === "true") {
        candidate.value = currentLocale;
        return;
      }
      const select = document.createElement("select");
      select.className = "language-select";
      select.setAttribute("aria-label", catalog?.strings.Language || "Language");
      select.dataset.mirrorSelect = "true";
      for (const locale of locales) {
        const option = document.createElement("option");
        option.value = locale;
        option.title = localeNames[locale];
        option.textContent = locale.toUpperCase();
        select.append(option);
      }
      select.value = currentLocale;
      select.addEventListener("change", () => {
        location.href = routeFor(select.value, state.page);
      });
      candidate.replaceWith(select);
    });
  }

  function localizeInternalLinks() {
    for (const page of ["privacy", "terms", "contact", "disclaimer"]) {
      document.querySelectorAll(`a[href="/${page}"], a[href="/${page}/"]`).forEach((link) => {
        link.setAttribute("href", routeFor(currentLocale, page));
      });
    }
  }

  async function loadCatalog(locale) {
    const response = await fetch(`/i18n/${locale}.json`);
    if (!response.ok) throw new Error(`Unable to load locale ${locale}`);
    return response.json();
  }

  function apply() {
    removeAds();
    installLanguageSelect();
    localizeInternalLinks();
    translateTree(document);
  }

  const observer = new MutationObserver((records) => {
    for (const record of records) {
      record.addedNodes.forEach((node) => {
        if (node.nodeType === Node.ELEMENT_NODE) removeAds(node);
      });
    }
    if (catalog) requestAnimationFrame(apply);
  });

  addEventListener("load", async () => {
    const state = routeState();
    currentLocale = state.locale;
    try {
      catalog = await loadCatalog(currentLocale);
      document.documentElement.lang = currentLocale === "zh" ? "zh-CN" : currentLocale;
      setTimeout(() => {
        apply();
        observer.observe(document.documentElement, { childList: true, subtree: true });
      }, 600);
    } catch (error) {
      console.error(error);
      setTimeout(() => {
        removeAds();
        installLanguageSelect();
        observer.observe(document.documentElement, { childList: true, subtree: true });
      }, 600);
    }
  });
})();
