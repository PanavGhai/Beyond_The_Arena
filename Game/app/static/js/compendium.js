
// app/static/js/compendium.js

document.addEventListener("DOMContentLoaded", () => {

    const gallery = document.getElementById("characterGallery");

    if (!gallery) return;


    // ==========================================
    // 1. ELEMENTS
    // ==========================================

    const cards = [...gallery.querySelectorAll(".character-card")];

    const tabs = [...document.querySelectorAll(".category-tab")];

    const searchInput = document.getElementById("characterSearch");

    const roleFilter = document.getElementById("roleFilter");

    const speciesFilter = document.getElementById("speciesFilter");

    const emptyState = document.getElementById("emptyFilterState");

    const personalityPanel = document.getElementById("personalityPanel");

    const personalityContent = document.getElementById("personalityContent");


    // ==========================================
    // 2. FILTER STATE
    // ==========================================

    let activeCategory = (
        document.querySelector(".category-tab.is-active")
            ?.dataset.category || "all"
    );


    // ==========================================
    // 3. FILTER CARDS
    // ==========================================

    function filterCards() {

        const search = searchInput.value.trim().toLowerCase();

        const role = roleFilter.value.toLowerCase();

        const species = speciesFilter.value.toLowerCase();

        let visibleCount = 0;

        cards.forEach(card => {

            const matchesCategory = (
                activeCategory === "all" ||
                card.dataset.category === activeCategory
            );

            const matchesSearch = (
                card.dataset.search.includes(search)
            );

            const matchesRole = (
                !role || card.dataset.role === role
            );

            const matchesSpecies = (
                !species || card.dataset.species === species
            );

            const visible = (
                matchesCategory &&
                matchesSearch &&
                matchesRole &&
                matchesSpecies
            );

            card.hidden = !visible;

            if (visible) visibleCount++;

        });

        emptyState.hidden = visibleCount > 0;

        closePersonalityPanel();
    }


    // ==========================================
    // 4. CATEGORY TABS
    // ==========================================

    tabs.forEach(tab => {

        tab.addEventListener("click", () => {

            activeCategory = tab.dataset.category;

            tabs.forEach(item => {

                const active = item === tab;

                item.classList.toggle("is-active", active);

                item.setAttribute(
                    "aria-selected",
                    active ? "true" : "false"
                );

            });

            filterCards();

        });

    });


    // ==========================================
    // 5. SEARCH AND FILTERS
    // ==========================================

    searchInput?.addEventListener("input", filterCards);

    roleFilter?.addEventListener("change", filterCards);

    speciesFilter?.addEventListener("change", filterCards);


    // ==========================================
    // 6. CARD FLIPPING
    // ==========================================

    cards.forEach(card => {

        const flipButton = card.querySelector(".card-flip");

        if (!flipButton) return;

        flipButton.addEventListener("click", () => {

            const isFlipped = card.classList.toggle("is-flipped");

            flipButton.setAttribute(
                "aria-expanded",
                isFlipped ? "true" : "false"
            );

        });

    });


    // ==========================================
    // 7. PERSONALITY PANEL
    // ==========================================

    function closePersonalityPanel() {

        personalityPanel.hidden = true;

        personalityContent.replaceChildren();

        cards.forEach(card => {
            card.classList.remove("personality-active");
        });

    }


    function openPersonalityPanel(card) {

        const template = card.querySelector(".personality-template");

        if (!template) return;

        const isAlreadyOpen = (
            !personalityPanel.hidden &&
            card.classList.contains("personality-active")
        );

        closePersonalityPanel();

        if (isAlreadyOpen) return;

        personalityContent.appendChild(
            template.content.cloneNode(true)
        );

        personalityPanel.hidden = false;

        card.classList.add("personality-active");

        personalityPanel.scrollIntoView({
            behavior: "smooth",
            block: "nearest"
        });

        const closeButton = personalityContent.querySelector(
            ".close-panel"
        );

        closeButton?.addEventListener(
            "click",
            closePersonalityPanel
        );

    }


    cards.forEach(card => {

        const personalityButton = card.querySelector(
            ".personality-link"
        );

        personalityButton?.addEventListener("click", () => {
            openPersonalityPanel(card);
        });

    });


    // ==========================================
    // 8. IMAGE FALLBACK
    // ==========================================

    gallery.querySelectorAll(".portrait-art img").forEach(image => {

        image.addEventListener("error", () => {

            const fallback = image.dataset.fallback;

            if (fallback && image.src !== new URL(fallback, window.location.href).href) {
                image.src = fallback;
            }

        });

    });


    // ==========================================
    // 9. INITIAL FILTER
    // ==========================================

    filterCards();

});
