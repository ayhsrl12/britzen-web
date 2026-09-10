// BRITZEN — comportamiento compartido del sitio

document.addEventListener("DOMContentLoaded", function () {
  // Menú móvil
  var toggle = document.querySelector(".nav-toggle");
  var nav = document.querySelector(".main-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      nav.classList.toggle("is-open");
      var expanded = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", String(!expanded));
    });
  }

  // Filtro de catálogo por categoría
  var filterButtons = document.querySelectorAll(".filter-btn");
  var cards = document.querySelectorAll("[data-category]");
  var countEl = document.querySelector(".catalog-count");

  function applyFilter(category) {
    var visible = 0;
    cards.forEach(function (card) {
      var match = category === "todos" || card.getAttribute("data-category") === category;
      card.style.display = match ? "" : "none";
      if (match) visible++;
    });
    if (countEl) {
      countEl.textContent = visible + (visible === 1 ? " producto" : " productos");
    }
  }

  if (filterButtons.length) {
    filterButtons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        filterButtons.forEach(function (b) { b.classList.remove("is-active"); });
        btn.classList.add("is-active");
        applyFilter(btn.getAttribute("data-filter"));
        history.replaceState(null, "", btn.getAttribute("data-slug") === "todos" ? location.pathname : "#" + btn.getAttribute("data-slug"));
      });
    });

    // Si se entra con #categoria en la URL (ej. desde los tiles de la home),
    // activa ese filtro en lugar de mostrar todo el catálogo.
    var hash = decodeURIComponent(location.hash.replace("#", ""));
    if (hash) {
      var matchBtn = null;
      filterButtons.forEach(function (b) {
        if (b.getAttribute("data-slug") === hash) matchBtn = b;
      });
      if (matchBtn) {
        filterButtons.forEach(function (b) { b.classList.remove("is-active"); });
        matchBtn.classList.add("is-active");
        applyFilter(matchBtn.getAttribute("data-filter"));
        matchBtn.scrollIntoView({ block: "nearest", inline: "center" });
      }
    }
  }

  // Buscador global (SKU o nombre), disponible en toda la web
  var searchToggle = document.querySelector(".search-toggle");
  var searchOverlay = document.getElementById("search-overlay");
  var searchInput = document.getElementById("search-input");
  var searchResults = document.getElementById("search-results");
  var searchClose = document.querySelector(".search-close");

  function normalize(str) {
    return str.toString().toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  }

  function inProductDir() {
    return location.pathname.indexOf("/producto/") !== -1;
  }

  function renderResults(query) {
    var data = window.SEARCH_DATA || [];
    var q = normalize(query.trim());
    if (!q) {
      searchResults.innerHTML = '<p class="search-hint">Empezá a escribir un código o nombre de producto.</p>';
      return;
    }
    var matches = data.filter(function (p) {
      return normalize(p.sku).indexOf(q) !== -1 || normalize(p.title).indexOf(q) !== -1;
    }).slice(0, 8);

    if (!matches.length) {
      searchResults.innerHTML = '<p class="search-hint">No encontramos productos para "' + query + '". Probá con otro código o nombre, o <a href="' + (inProductDir() ? "../" : "") + 'contacto.html">consultanos por WhatsApp</a>.</p>';
      return;
    }
    var prefix = inProductDir() ? "" : "producto/";
    searchResults.innerHTML = matches.map(function (p) {
      return '<a class="search-result" href="' + prefix + p.slug + '.html">' +
        '<span class="search-result-cat">' + p.category + '</span>' +
        '<span class="search-result-title">' + p.title + '</span>' +
        '<span class="search-result-sku">Cód. ' + p.sku + '</span>' +
        '</a>';
    }).join("");
  }

  function openSearch() {
    if (!searchOverlay) return;
    searchOverlay.classList.add("is-open");
    document.body.style.overflow = "hidden";
    renderResults("");
    setTimeout(function () { searchInput.focus(); }, 50);
  }

  function closeSearch() {
    if (!searchOverlay) return;
    searchOverlay.classList.remove("is-open");
    document.body.style.overflow = "";
    searchInput.value = "";
  }

  if (searchToggle) {
    searchToggle.addEventListener("click", openSearch);
    searchClose.addEventListener("click", closeSearch);
    searchOverlay.addEventListener("click", function (e) {
      if (e.target === searchOverlay) closeSearch();
    });
    searchInput.addEventListener("input", function () { renderResults(searchInput.value); });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeSearch();
      if ((e.key === "/" || (e.ctrlKey && e.key === "k")) && !searchOverlay.classList.contains("is-open") && document.activeElement.tagName !== "INPUT") {
        e.preventDefault();
        openSearch();
      }
    });
  }
});

document.addEventListener("DOMContentLoaded", function () {
  var mainImg = document.getElementById("gallery-main");
  var thumbs = document.querySelectorAll(".gallery-thumb");
  if (mainImg && thumbs.length) {
    thumbs.forEach(function (btn) {
      btn.addEventListener("click", function () {
        mainImg.src = btn.getAttribute("data-src");
        thumbs.forEach(function (b) { b.classList.remove("is-active"); });
        btn.classList.add("is-active");
      });
    });
  }
});
