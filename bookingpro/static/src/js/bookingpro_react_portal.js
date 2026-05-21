/** @odoo-module **/
/* globals React, ReactDOM */
(function () {
    "use strict";

    var REACT_URL = "https://unpkg.com/react@18/umd/react.production.min.js";
    var REACT_DOM_URL = "https://unpkg.com/react-dom@18/umd/react-dom.production.min.js";
    var loaded = false;
    var loading = false;
    var queue = [];

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

    function text(node) {
        return (node && (node.textContent || node.innerText) || "").replace(/\s+/g, " ").trim();
    }

    function isBookingProPage() {
        return !!document.querySelector(".bp-shell, .bp-customer-shell, .bp-public-wrap, .bp-auth-shell");
    }

    function loadScript(src, done, fail) {
        var script = document.createElement("script");
        script.src = src;
        script.async = true;
        script.crossOrigin = "anonymous";
        script.onload = done;
        script.onerror = fail;
        document.head.appendChild(script);
    }

    function ensureReact(callback) {
        if (window.React && window.ReactDOM) {
            callback();
            return;
        }
        queue.push(callback);
        if (loaded || loading) {
            return;
        }
        loading = true;
        loadScript(REACT_URL, function () {
            loadScript(REACT_DOM_URL, function () {
                loaded = true;
                loading = false;
                while (queue.length) {
                    queue.shift()();
                }
            }, function () {
                loading = false;
                queue = [];
            });
        }, function () {
            loading = false;
            queue = [];
        });
    }

    function actionFromLink(link, group) {
        if (!link || !link.getAttribute("href")) {
            return null;
        }
        return {
            label: text(link).replace(/^[^\w]+/, "").trim() || link.getAttribute("aria-label") || "Open",
            href: link.getAttribute("href"),
            group: group,
        };
    }

    function uniqueActions(actions) {
        var seen = {};
        return actions.filter(function (action) {
            var key;
            if (!action || !action.href) {
                return false;
            }
            key = action.group + action.label + action.href;
            if (seen[key]) {
                return false;
            }
            seen[key] = true;
            return true;
        });
    }

    function collectActions() {
        var actions = [];
        all(".bp-nav-link").forEach(function (link) {
            actions.push(actionFromLink(link, "Workspace"));
        });
        all(".bp-command-actions a, .bp-customer-hero-actions a, .bp-customer-top-actions a, .bp-form-actions a").forEach(function (link) {
            actions.push(actionFromLink(link, "Actions"));
        });
        all(".bp-btn-primary, .bp-customer-btn-primary, .bp-command-btn-primary").forEach(function (link) {
            if (link.tagName && link.tagName.toLowerCase() === "a") {
                actions.push(actionFromLink(link, "Primary"));
            }
        });
        if (document.querySelector(".bp-public-wrap")) {
            actions.push({ label: "Explore services", href: "#bp_services_grid", group: "Booking" });
            actions.push({ label: "Customer portal", href: "/my/bookingpro", group: "Booking" });
        }
        if (document.querySelector(".bp-auth-shell")) {
            actions.push({ label: "Customer signup", href: "/bookingpro/signup", group: "Account" });
            actions.push({ label: "Login", href: "/bookingpro/login", group: "Account" });
        }
        return uniqueActions(actions).slice(0, 18);
    }

    function collectNavigation() {
        return uniqueActions(all(".bp-nav-link").map(function (link) {
            var action = actionFromLink(link, "Navigation");
            if (action) {
                action.active = link.classList.contains("active");
            }
            return action;
        }));
    }

    function collectMetrics() {
        var metrics = [];
        all(".bp-stat, .bp-customer-stat-card, .bp-mini-stats div, .bp-side-metrics div").forEach(function (node) {
            var label = text(node.querySelector(".label, span, small"));
            var value = text(node.querySelector(".value, strong"));
            if (value) {
                metrics.push({ label: label || "Metric", value: value });
            }
        });
        return metrics.slice(0, 6);
    }

    function getPageTitle() {
        return text(document.querySelector(".bp-title, .bp-customer-hero h1, .bp-customer-detail-hero h1, .bp-hero-section h1, .bp-auth-card-head h2")) || "BookingPro";
    }

    function labelTables() {
        all(".bp-table").forEach(function (table) {
            var labels = all("thead th", table).map(text);
            all("tbody tr", table).forEach(function (row) {
                all("td", row).forEach(function (cell, index) {
                    if (!cell.getAttribute("data-bp-label")) {
                        cell.setAttribute("data-bp-label", labels[index] || "Info");
                    }
                });
            });
        });
    }

    function applyTheme(theme) {
        var selected = theme === "dark" ? "dark" : "light";
        document.documentElement.setAttribute("data-bp-theme", selected);
        try {
            window.localStorage.setItem("bookingpro_theme", selected);
        } catch (e) {}
    }

    function readTheme() {
        try {
            return window.localStorage.getItem("bookingpro_theme") === "dark" ? "dark" : "light";
        } catch (e) {
            return "light";
        }
    }

    function readCardView() {
        try {
            return window.localStorage.getItem("bookingpro_card_view") === "1";
        } catch (e) {
            return false;
        }
    }

    function setCardView(enabled) {
        document.body.classList.toggle("bp-card-view", !!enabled);
        try {
            window.localStorage.setItem("bookingpro_card_view", enabled ? "1" : "0");
        } catch (e) {}
    }

    function goTo(action) {
        var target;
        if (!action || !action.href) {
            return;
        }
        if (action.href.charAt(0) === "#") {
            target = document.querySelector(action.href);
            if (target) {
                target.scrollIntoView({ behavior: "smooth", block: "start" });
            }
            return;
        }
        window.location.href = action.href;
    }

    function PortalShell() {
        var h = window.React.createElement;
        var openState = window.React.useState(false);
        var commandOpen = openState[0];
        var setCommandOpen = openState[1];
        var navState = window.React.useState(false);
        var navOpen = navState[0];
        var setNavOpen = navState[1];
        var queryState = window.React.useState("");
        var query = queryState[0];
        var setQuery = queryState[1];
        var themeState = window.React.useState(readTheme);
        var theme = themeState[0];
        var setTheme = themeState[1];
        var cardState = window.React.useState(readCardView);
        var cardView = cardState[0];
        var setCardViewState = cardState[1];
        var actions = window.React.useMemo(collectActions, []);
        var nav = window.React.useMemo(collectNavigation, []);
        var metrics = window.React.useMemo(collectMetrics, []);
        var pageTitle = window.React.useMemo(getPageTitle, []);
        var filtered = actions.filter(function (action) {
            var haystack = (action.group + " " + action.label).toLowerCase();
            return !query || haystack.indexOf(query.toLowerCase()) >= 0;
        });

        window.React.useEffect(function () {
            labelTables();
        }, []);

        window.React.useEffect(function () {
            applyTheme(theme);
        }, [theme]);

        window.React.useEffect(function () {
            setCardView(cardView);
        }, [cardView]);

        window.React.useEffect(function () {
            function onKeydown(event) {
                var isCommand = (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k";
                if (isCommand) {
                    event.preventDefault();
                    setCommandOpen(true);
                }
                if (event.key === "Escape") {
                    setCommandOpen(false);
                    setNavOpen(false);
                }
            }
            document.addEventListener("keydown", onKeydown);
            return function () { document.removeEventListener("keydown", onKeydown); };
        }, []);

        function rotateTheme() {
            setTheme(theme === "dark" ? "light" : "dark");
        }

        function toggleCards() {
            setCardViewState(function (value) { return !value; });
        }

        return h(window.React.Fragment, null,
            h("div", { className: "bp-react-toolbar", role: "toolbar", "aria-label": "BookingPro React controls" },
                nav.length ? h("button", {
                    type: "button",
                    className: "bp-react-tool",
                    onClick: function () { setNavOpen(true); },
                    "aria-label": "Open navigation",
                }, h("span", null, "Menu")) : null,
                h("button", {
                    type: "button",
                    className: "bp-react-tool bp-react-tool-primary",
                    onClick: function () { setCommandOpen(true); },
                    "aria-label": "Open command center",
                }, h("span", null, "Ctrl"), h("strong", null, "K")),
                document.querySelector(".bp-table") ? h("button", {
                    type: "button",
                    className: "bp-react-tool",
                    onClick: toggleCards,
                    "aria-label": "Toggle table view",
                }, cardView ? "Table" : "Cards") : null,
                h("button", {
                    type: "button",
                    className: "bp-react-tool",
                    onClick: rotateTheme,
                    "aria-label": "Change theme",
                }, theme)
            ),
            commandOpen ? h("div", {
                className: "bp-react-overlay",
                onMouseDown: function (event) {
                    if (event.target === event.currentTarget) {
                        setCommandOpen(false);
                    }
                },
            },
                h("section", { className: "bp-react-command", role: "dialog", "aria-modal": "true" },
                    h("div", { className: "bp-react-command-head" },
                        h("div", null,
                            h("span", { className: "bp-react-kicker" }, "BookingPro React"),
                            h("h3", null, pageTitle)
                        ),
                        h("button", {
                            type: "button",
                            className: "bp-react-close",
                            onClick: function () { setCommandOpen(false); },
                            "aria-label": "Close",
                        }, "x")
                    ),
                    metrics.length ? h("div", { className: "bp-react-metrics" },
                        metrics.map(function (metric, index) {
                            return h("div", { className: "bp-react-metric", key: metric.label + index },
                                h("strong", null, metric.value),
                                h("span", null, metric.label)
                            );
                        })
                    ) : null,
                    h("label", { className: "bp-react-search" },
                        h("span", null, "Search actions"),
                        h("input", {
                            autoFocus: true,
                            value: query,
                            onChange: function (event) { setQuery(event.target.value); },
                            placeholder: "Find workspace pages, booking actions, portal links",
                        })
                    ),
                    h("div", { className: "bp-react-list" },
                        filtered.length ? filtered.map(function (action, index) {
                            return h("button", {
                                key: action.group + action.href + index,
                                type: "button",
                                className: "bp-react-action",
                                onClick: function () {
                                    setCommandOpen(false);
                                    goTo(action);
                                },
                            },
                                h("span", { className: "bp-react-action-icon" }, action.group.slice(0, 1)),
                                h("span", null,
                                    h("strong", null, action.label),
                                    h("small", null, action.group)
                                )
                            );
                        }) : h("div", { className: "bp-react-empty" }, "No matching action")
                    )
                )
            ) : null,
            navOpen ? h("div", {
                className: "bp-react-overlay bp-react-nav-overlay",
                onMouseDown: function (event) {
                    if (event.target === event.currentTarget) {
                        setNavOpen(false);
                    }
                },
            },
                h("aside", { className: "bp-react-drawer", role: "dialog", "aria-modal": "true" },
                    h("div", { className: "bp-react-command-head" },
                        h("div", null,
                            h("span", { className: "bp-react-kicker" }, "Navigation"),
                            h("h3", null, "Workspace menu")
                        ),
                        h("button", {
                            type: "button",
                            className: "bp-react-close",
                            onClick: function () { setNavOpen(false); },
                            "aria-label": "Close",
                        }, "x")
                    ),
                    h("nav", { className: "bp-react-nav-list" },
                        nav.map(function (item, index) {
                            return h("button", {
                                key: item.href + index,
                                type: "button",
                                className: "bp-react-nav-item" + (item.active ? " active" : ""),
                                onClick: function () { goTo(item); },
                            }, item.label);
                        })
                    )
                )
            ) : null
        );
    }

    function mountPortalShell() {
        var root;
        if (!window.React || !window.ReactDOM || !isBookingProPage()) {
            return;
        }
        if (document.getElementById("bp-react-command-root")) {
            return;
        }
        root = document.createElement("div");
        root.id = "bp-react-command-root";
        root.className = "bp-react-layer";
        document.body.appendChild(root);
        window.ReactDOM.createRoot(root).render(window.React.createElement(PortalShell));
        document.body.classList.add("bp-react-ui-mounted");
    }

    function mountCatalogApp() {
        var host;
        var originalTabs;
        var cards;
        var categories;
        var browser;
        if (!window.React || !window.ReactDOM) {
            return;
        }
        browser = document.getElementById("bp_services_grid");
        originalTabs = document.querySelector(".bp-category-tabs");
        cards = all(".bp-service-item");
        if (!browser || !originalTabs || !cards.length || document.getElementById("bp-react-catalog-root")) {
            return;
        }
        categories = all(".bp-category-pill", originalTabs).map(function (button) {
            return {
                id: button.getAttribute("data-bp-category") || "all",
                label: text(button) || "Category",
            };
        });
        host = document.createElement("div");
        host.id = "bp-react-catalog-root";
        originalTabs.parentNode.insertBefore(host, originalTabs);
        document.body.classList.add("bp-react-catalog-mode");

        function CatalogApp() {
            var h = window.React.createElement;
            var activeState = window.React.useState("all");
            var active = activeState[0];
            var setActive = activeState[1];
            var queryState = window.React.useState("");
            var query = queryState[0];
            var setQuery = queryState[1];
            var countState = window.React.useState(cards.length);
            var count = countState[0];
            var setCount = countState[1];

            window.React.useEffect(function () {
                var visible = 0;
                var q = query.toLowerCase().trim();
                cards.forEach(function (card) {
                    var catOk = active === "all" || card.dataset.bpCategory === active;
                    var textOk = !q || (card.dataset.bpSearch || "").toLowerCase().indexOf(q) >= 0;
                    var matched = catOk && textOk;
                    card.style.display = matched ? "" : "none";
                    if (matched) {
                        visible += 1;
                    }
                });
                all("[data-category-block]", browser).forEach(function (block) {
                    var hasVisible = all(".bp-service-item", block).some(function (card) {
                        return card.style.display !== "none";
                    });
                    block.style.display = hasVisible ? "" : "none";
                });
                browser.classList.toggle("bp-search-empty-results", visible === 0);
                setCount(visible);
            }, [active, query]);

            return h("section", { className: "bp-react-catalog-bar" },
                h("div", { className: "bp-react-catalog-head" },
                    h("div", null,
                        h("span", { className: "bp-react-kicker" }, "React service finder"),
                        h("h3", null, "Choose the right appointment")
                    ),
                    h("strong", null, count + " visible")
                ),
                h("div", { className: "bp-react-catalog-controls" },
                    h("input", {
                        type: "search",
                        value: query,
                        onChange: function (event) { setQuery(event.target.value); },
                        placeholder: "Search service or category",
                    }),
                    h("div", { className: "bp-react-segments" },
                        categories.map(function (category) {
                            return h("button", {
                                key: category.id,
                                type: "button",
                                className: "bp-react-segment" + (active === category.id ? " active" : ""),
                                onClick: function () { setActive(category.id); },
                            }, category.label);
                        })
                    )
                )
            );
        }

        window.ReactDOM.createRoot(host).render(window.React.createElement(CatalogApp));
    }

    function mountBookingFormApp() {
        var main;
        var form;
        var host;
        var sections;
        if (!window.React || !window.ReactDOM) {
            return;
        }
        form = document.querySelector(".bp-premium-form");
        main = document.querySelector(".bp-booking-main");
        if (!form || !main || document.getElementById("bp-react-booking-root")) {
            return;
        }
        sections = all(".bp-form-section", form);
        host = document.createElement("div");
        host.id = "bp-react-booking-root";
        form.parentNode.insertBefore(host, form);

        function selectedLabel(selector, fallback) {
            var field = document.querySelector(selector);
            if (!field) {
                return fallback;
            }
            if (field.tagName.toLowerCase() === "select") {
                return text(field.options[field.selectedIndex]) || fallback;
            }
            return field.value || fallback;
        }

        function readSummary() {
            return {
                staff: selectedLabel("#bp_staff_id", "Any staff"),
                resource: selectedLabel("#bp_resource_id", "No preference"),
                date: selectedLabel("#bp_date", "Pick date"),
                slot: selectedLabel("#bp_slot_select", "Pick slot"),
            };
        }

        function BookingFormApp() {
            var h = window.React.createElement;
            var summaryState = window.React.useState(readSummary);
            var summary = summaryState[0];
            var setSummary = summaryState[1];

            window.React.useEffect(function () {
                function sync() {
                    setSummary(readSummary());
                }
                all("input, select, textarea", form).forEach(function (field) {
                    field.addEventListener("change", sync);
                    field.addEventListener("input", sync);
                });
                sync();
                return function () {
                    all("input, select, textarea", form).forEach(function (field) {
                        field.removeEventListener("change", sync);
                        field.removeEventListener("input", sync);
                    });
                };
            }, []);

            return h("section", { className: "bp-react-booking-panel" },
                h("div", { className: "bp-react-booking-steps" },
                    sections.map(function (section, index) {
                        var title = text(section.querySelector(".bp-form-section-title h3")) || ("Step " + (index + 1));
                        return h("button", {
                            key: title + index,
                            type: "button",
                            className: "bp-react-step",
                            onClick: function () { section.scrollIntoView({ behavior: "smooth", block: "start" }); },
                        },
                            h("span", null, "0" + (index + 1)),
                            h("strong", null, title)
                        );
                    })
                ),
                h("div", { className: "bp-react-booking-summary" },
                    h("div", null, h("span", null, "Staff"), h("strong", null, summary.staff)),
                    h("div", null, h("span", null, "Resource"), h("strong", null, summary.resource)),
                    h("div", null, h("span", null, "Date"), h("strong", null, summary.date)),
                    h("div", null, h("span", null, "Slot"), h("strong", null, summary.slot))
                )
            );
        }

        window.ReactDOM.createRoot(host).render(window.React.createElement(BookingFormApp));
    }

    function mountReactSelects() {
        if (!window.React || !window.ReactDOM) {
            return;
        }
        all(".bp-shell select:not([multiple]), .bp-customer-shell select:not([multiple]), .bp-public-wrap select:not([multiple]), .bp-auth-shell select:not([multiple])").forEach(function (select, index) {
            var host;
            if (select.dataset.bpReactSelectReady) {
                return;
            }
            select.dataset.bpReactSelectReady = "1";
            select.classList.add("bp-react-native-select");
            if (!select.id) {
                select.id = "bp_react_select_" + index + "_" + Math.floor(Math.random() * 100000);
            }
            host = document.createElement("span");
            host.className = "bp-react-select-host";
            select.insertAdjacentElement("afterend", host);

            function readOptions() {
                return all("option", select).map(function (option) {
                    return {
                        value: option.value,
                        label: text(option) || option.value || "Select",
                        disabled: option.disabled,
                    };
                });
            }

            function ReactSelect() {
                var h = window.React.createElement;
                var openState = window.React.useState(false);
                var open = openState[0];
                var setOpen = openState[1];
                var valueState = window.React.useState(select.value);
                var value = valueState[0];
                var setValue = valueState[1];
                var optionsState = window.React.useState(readOptions);
                var options = optionsState[0];
                var setOptions = optionsState[1];
                var selected = options.filter(function (option) { return option.value === value; })[0] || options[0];
                var ref = window.React.useRef(null);

                window.React.useEffect(function () {
                    function sync() {
                        setValue(select.value);
                        setOptions(readOptions());
                    }
                    function close(event) {
                        if (ref.current && !ref.current.contains(event.target)) {
                            setOpen(false);
                        }
                    }
                    var observer = window.MutationObserver ? new MutationObserver(sync) : null;
                    select.addEventListener("change", sync);
                    document.addEventListener("mousedown", close);
                    if (observer) {
                        observer.observe(select, { childList: true, subtree: true, attributes: true });
                    }
                    sync();
                    return function () {
                        select.removeEventListener("change", sync);
                        document.removeEventListener("mousedown", close);
                        if (observer) {
                            observer.disconnect();
                        }
                    };
                }, []);

                function choose(option) {
                    if (!option || option.disabled) {
                        return;
                    }
                    select.value = option.value;
                    select.dispatchEvent(new Event("change", { bubbles: true }));
                    setValue(option.value);
                    setOpen(false);
                }

                return h("span", { className: "bp-react-select" + (open ? " open" : ""), ref: ref },
                    h("button", {
                        type: "button",
                        className: "bp-react-select-trigger",
                        onClick: function () { setOpen(function (state) { return !state; }); },
                        "aria-haspopup": "listbox",
                        "aria-expanded": open ? "true" : "false",
                    },
                        h("span", null, selected ? selected.label : "Select"),
                        h("b", null, "v")
                    ),
                    open ? h("span", { className: "bp-react-select-menu", role: "listbox" },
                        options.map(function (option) {
                            return h("button", {
                                key: option.value + option.label,
                                type: "button",
                                className: "bp-react-select-option" + (option.value === value ? " active" : "") + (option.disabled ? " disabled" : ""),
                                disabled: option.disabled,
                                role: "option",
                                "aria-selected": option.value === value ? "true" : "false",
                                onClick: function () { choose(option); },
                            }, option.label);
                        })
                    ) : null
                );
            }

            window.ReactDOM.createRoot(host).render(window.React.createElement(ReactSelect));
        });
    }

    ready(function () {
        if (!isBookingProPage()) {
            return;
        }
        ensureReact(function () {
            mountPortalShell();
            mountCatalogApp();
            mountBookingFormApp();
            mountReactSelects();
        });
    });
})();
