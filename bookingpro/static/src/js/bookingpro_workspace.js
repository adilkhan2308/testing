(function () {
  "use strict";

  function ready(fn) {
    if (document.readyState !== "loading") {
      fn();
    } else {
      document.addEventListener("DOMContentLoaded", fn);
    }
  }

  function all(selector, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(selector));
  }

  function textOf(node) {
    return (node && (node.textContent || node.innerText) || "").toLowerCase();
  }

  function copyToClipboard(value, done) {
    value = (value || "").trim();
    if (!value) {
      return;
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(value).then(done).catch(function () {
        fallbackCopy(value, done);
      });
      return;
    }
    fallbackCopy(value, done);
  }

  function fallbackCopy(value, done) {
    var input = document.createElement("textarea");
    input.value = value;
    input.setAttribute("readonly", "readonly");
    input.style.position = "fixed";
    input.style.left = "-9999px";
    document.body.appendChild(input);
    input.select();
    try { document.execCommand("copy"); } catch (e) {}
    document.body.removeChild(input);
    if (done) { done(); }
  }

  function toast(message) {
    var stack = document.querySelector(".bp-toast-stack");
    if (!stack) {
      stack = document.createElement("div");
      stack.className = "bp-toast-stack";
      document.body.appendChild(stack);
    }
    var item = document.createElement("div");
    item.className = "bp-toast";
    item.textContent = message;
    stack.appendChild(item);
    window.setTimeout(function () {
      item.classList.add("is-leaving");
      window.setTimeout(function () {
        if (item.parentNode) {
          item.parentNode.removeChild(item);
        }
      }, 220);
    }, 1800);
  }

  function hideOdooChrome(isCustomerPortal, isWorkspace) {
    if (!isWorkspace && !isCustomerPortal) {
      return;
    }
    var backendChromeSelector = [
      ".o_frontend_to_backend_nav",
      ".o_frontend_to_backend",
      ".o_frontend_to_backend_apps_btn",
      ".o_frontend_to_backend_edit_btn",
      ".o_website_edit_top_bar",
      ".o_website_edit_actions",
      ".o_website_preview",
      ".o_website_edit_menu",
      ".o_website_editor",
      "#oe_main_menu_navbar",
      ".o_main_navbar",
      "#wrapwrap > header",
      "header",
      "footer",
      ".o_footer",
      "#top",
      "#top_menu",
      "#top_menu_collapse",
      ".navbar",
      ".o_header_standard",
      ".o_header_affixed",
      ".o_header_overlay"
    ].join(",");

    var removeBackendChrome = function () {
      all(backendChromeSelector).forEach(function (node) {
        node.setAttribute("aria-hidden", "true");
        node.style.setProperty("display", "none", "important");
        node.style.setProperty("visibility", "hidden", "important");
        node.style.setProperty("pointer-events", "none", "important");
        node.style.setProperty("height", "0", "important");
        node.style.setProperty("min-height", "0", "important");
        node.style.setProperty("max-height", "0", "important");
        node.style.setProperty("margin", "0", "important");
        node.style.setProperty("padding", "0", "important");
        node.style.setProperty("border", "0", "important");
        node.style.setProperty("overflow", "hidden", "important");
      });

      if (isCustomerPortal) {
        document.documentElement.style.setProperty("margin", "0", "important");
        document.body.style.setProperty("margin", "0", "important");
        document.body.style.setProperty("padding-top", "0", "important");
        ["#wrapwrap", "#wrapwrap > main", "main", "#wrap", ".o_portal_wrap", ".o_portal_container"].forEach(function (selector) {
          all(selector).forEach(function (node) {
            node.style.setProperty("margin-top", "0", "important");
            node.style.setProperty("padding-top", "0", "important");
            node.style.setProperty("border-top", "0", "important");
          });
        });
        all(".bp-command-customer").forEach(function (bar) {
          bar.style.setProperty("top", "0", "important");
          bar.style.setProperty("margin-top", "0", "important");
        });
      }

      if (isCustomerPortal && !isWorkspace) {
        all('a[href="/web"], a[href^="/web?"], a[href="/odoo"], a[href^="/odoo?"], a[href="/bookingpro/backend"]').forEach(function (link) {
          if (!link.closest(".bp-customer-top-actions") && !link.closest(".bp-command-actions")) {
            link.setAttribute("href", "/my/bookingpro");
            link.setAttribute("title", "Customer portal");
          }
        });
      }
    };

    removeBackendChrome();
    if (window.MutationObserver) {
      var chromeObserver = new MutationObserver(removeBackendChrome);
      chromeObserver.observe(document.documentElement, { childList: true, subtree: true });
    }
  }

  function enhanceCopyButtons() {
    all("[data-bp-copy]").forEach(function (btn) {
      if (btn.dataset.bpCopyReady) {
        return;
      }
      btn.dataset.bpCopyReady = "1";
      btn.addEventListener("click", function (ev) {
        ev.preventDefault();
        var target = document.querySelector(btn.getAttribute("data-bp-copy"));
        if (!target) { return; }
        var value = target.value || target.textContent || "";
        var old = btn.textContent;
        copyToClipboard(value, function () {
          btn.textContent = "Copied";
          btn.classList.add("bp-copied");
          toast("Link copied");
          setTimeout(function () {
            btn.textContent = old;
            btn.classList.remove("bp-copied");
          }, 1200);
        });
      });
    });
  }

  function enhanceSearchInputs() {
    all("[data-bp-table-search]").forEach(function (input) {
      if (input.dataset.bpSearchReady) {
        return;
      }
      input.dataset.bpSearchReady = "1";
      input.addEventListener("input", function () {
        var target = document.querySelector(input.getAttribute("data-bp-table-search"));
        if (!target) { return; }
        var q = input.value.toLowerCase().trim();
        var items = target.querySelectorAll("tbody tr, article, .bp-service-item, .bp-card, .bp-customer-appointment-card");
        if (!items.length && target.children.length) {
          items = target.children;
        }
        var visible = 0;
        Array.prototype.forEach.call(items, function (item) {
          var matched = !q || textOf(item).indexOf(q) >= 0;
          item.style.display = matched ? "" : "none";
          if (matched) {
            visible += 1;
          }
        });
        target.classList.toggle("bp-search-empty-results", !!q && visible === 0);
      });
    });
  }

  function enhancePublicCatalog() {
    var search = document.getElementById("bp_service_search");
    var pills = all(".bp-category-pill");
    var cards = all(".bp-service-item");
    if ((!search && !pills.length) || !cards.length) {
      return;
    }
    if (document.body.dataset.bpCatalogReady) {
      return;
    }
    document.body.dataset.bpCatalogReady = "1";
    var activeCategory = "all";
    function applyFilter() {
      var q = (search ? search.value : "").toLowerCase().trim();
      var visible = 0;
      cards.forEach(function (card) {
        var catOk = activeCategory === "all" || card.dataset.bpCategory === activeCategory;
        var textOk = !q || (card.dataset.bpSearch || "").toLowerCase().indexOf(q) >= 0;
        var matched = catOk && textOk;
        card.style.display = matched ? "" : "none";
        if (matched) {
          visible += 1;
        }
      });
      var grid = document.getElementById("bp_services_grid");
      if (grid) {
        grid.classList.toggle("bp-search-empty-results", visible === 0);
      }
    }
    pills.forEach(function (pill) {
      pill.addEventListener("click", function () {
        pills.forEach(function (item) { item.classList.remove("active"); });
        pill.classList.add("active");
        activeCategory = pill.dataset.bpCategory || "all";
        applyFilter();
      });
    });
    if (search) {
      search.addEventListener("input", applyFilter);
    }
    applyFilter();
  }

  function enhanceForms() {
    all(".bp-shell form, .bp-customer-shell form, .bp-public-wrap form, .bp-auth-shell form").forEach(function (form) {
      if (form.dataset.bpFormReady) {
        return;
      }
      form.dataset.bpFormReady = "1";
      form.addEventListener("submit", function () {
        form.classList.add("bp-form-submitting");
        all("button[type='submit']", form).forEach(function (button) {
          button.classList.add("bp-button-loading");
          button.setAttribute("aria-busy", "true");
        });
      });
    });
  }

  function enhancePasswordInputs() {
    all(".bp-auth-form input[type='password']").forEach(function (input) {
      if (input.dataset.bpPasswordReady) {
        return;
      }
      input.dataset.bpPasswordReady = "1";
      var wrapper = document.createElement("div");
      wrapper.className = "bp-password-field";
      var button = document.createElement("button");
      button.type = "button";
      button.className = "bp-password-toggle";
      button.textContent = "Show";
      button.setAttribute("aria-label", "Show password");
      input.parentNode.insertBefore(wrapper, input);
      wrapper.appendChild(input);
      wrapper.appendChild(button);
      button.addEventListener("click", function () {
        var show = input.type === "password";
        input.type = show ? "text" : "password";
        button.textContent = show ? "Hide" : "Show";
        button.setAttribute("aria-label", show ? "Hide password" : "Show password");
      });
    });
  }

  function enhanceFocusShortcuts() {
    document.addEventListener("keydown", function (event) {
      if (event.key !== "/" || event.ctrlKey || event.metaKey || event.altKey) {
        return;
      }
      var tag = (event.target && event.target.tagName || "").toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select") {
        return;
      }
      var search = document.querySelector(".bp-search-input, .bp-customer-search, #bp_service_search");
      if (search) {
        event.preventDefault();
        search.focus();
      }
    });
  }

  function enhanceVisualState() {
    all(".bp-card, .bp-stat, .bp-customer-stat-card, .bp-customer-appointment-card, .bp-service-card").forEach(function (card, index) {
      card.style.setProperty("--bp-index", String(index));
    });
    all(".bp-nav-link").forEach(function (link) {
      var href = link.getAttribute("href");
      if (href && window.location.pathname === href) {
        link.classList.add("active");
      }
    });
  }

  ready(function () {
    var isWorkspace = !!document.querySelector(".bp-shell");
    var isCustomerPortal = !!document.querySelector(".bp-customer-shell");
    var isPublicBooking = !!document.querySelector(".bp-public-wrap");
    var isAuth = !!document.querySelector(".bp-auth-shell");

    document.body.classList.add("bp-js-mounted");

    if (isWorkspace) {
      document.body.classList.add("bp-workspace-mode");
    }
    if (isCustomerPortal) {
      document.body.classList.add("bp-customer-portal-mode");
      document.documentElement.classList.add("bp-customer-portal-html-mode");
    }
    if (isAuth) {
      document.body.classList.add("bp-auth-mode");
    }

    hideOdooChrome(isCustomerPortal, isWorkspace);
    enhanceCopyButtons();
    enhanceSearchInputs();
    enhancePublicCatalog();
    enhanceForms();
    enhancePasswordInputs();
    enhanceFocusShortcuts();
    enhanceVisualState();

    if (isPublicBooking || isWorkspace || isCustomerPortal || isAuth) {
      all(".bp-btn, .bp-customer-btn, .bp-command-btn, .bp-nav-link, .bp-category-pill").forEach(function (el) {
        if (!el.getAttribute("aria-label") && textOf(el)) {
          el.setAttribute("aria-label", textOf(el).trim());
        }
      });
    }
  });
})();
