document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("characterCreator");
    if (!form) return;
    const steps = [...form.querySelectorAll(".creator-step")];
    const indicators = [...document.querySelectorAll("[data-step-indicator]")];
    let activeStep = 1;

    function showStep(step) {
        activeStep = step;
        form.closest(".creator-shell").dataset.activeStep = String(step);
        steps.forEach(section => { section.hidden = Number(section.dataset.step) !== step; });
        indicators.forEach(item => {
            const index = Number(item.dataset.stepIndicator);
            item.classList.toggle("is-current", index === step);
            item.classList.toggle("is-complete", index < step);
        });
        window.scrollTo({ top: 0, behavior: "smooth" });
    }

    function allocationState(kind) {
        const counter = document.querySelector(`[data-point-counter="${kind}"]`);
        const group = document.querySelector(`[data-allocation="${kind}"]`);
        if (!counter || !group) return { valid: true };
        const inputs = [...group.querySelectorAll("[data-point-value]")];
        const budget = kind === "skills"
            ? Number(counter.dataset.pointsPerItem) * inputs.length
            : Number(counter.dataset.extraPoints);
        const used = inputs.reduce((total, input) => total + (Number(input.value) - Number(input.dataset.default)), 0);
        const remaining = budget - used;
        const valid = inputs.every(input => input.value !== "" && input.checkValidity()) && remaining === 0;
        counter.querySelector("[data-points-remaining]").textContent = remaining;
        const status = document.querySelector(`[data-allocation-status="${kind}"]`);
        if (status) status.textContent = valid ? "Point allocation is valid." : `Use exactly ${budget} additional points. ${remaining} remain.`;
        return { valid, remaining, budget };
    }

    function updateAllocations() {
        for (const kind of ["attributes", "skills"]) {
            const state = allocationState(kind);
            const section = form.querySelector(`[data-step="${kind === "attributes" ? 2 : 3}"]`);
            const next = section?.querySelector("[data-next]");
            if (next) next.disabled = !state.valid;
        }
    }

    form.querySelectorAll("[data-point-value]").forEach(input => input.addEventListener("input", updateAllocations));
    form.querySelectorAll("[data-next]").forEach(button => button.addEventListener("click", () => {
        const section = button.closest(".creator-step");
        const fields = [...section.querySelectorAll("input,select,textarea")].filter(item => !item.disabled);
        const invalid = fields.find(item => !item.checkValidity());
        if (invalid) { invalid.reportValidity(); return; }
        if (section.dataset.step === "2" && !allocationState("attributes").valid) return;
        if (section.dataset.step === "3" && !allocationState("skills").valid) return;
        showStep(Number(section.dataset.step) + 1);
    }));
    form.querySelectorAll("[data-back]").forEach(button => button.addEventListener("click", () => {
        showStep(Number(button.closest(".creator-step").dataset.step) - 1);
    }));

    const roleSelect = document.getElementById("roleSelect");
    const speciesSelect = document.getElementById("speciesSelect");
    const tributeNote = document.getElementById("tributeSpeciesNote");
    const hardcoreField = document.getElementById("hardcoreField");
    const hardcoreToggle = document.getElementById("hardcoreToggle");
    function updateSpeciesLock() {
        if (!roleSelect || !speciesSelect) return;
        const locked = roleSelect.value === "tributes";
        if (hardcoreField) hardcoreField.hidden = !locked;
        if (hardcoreToggle) {
            hardcoreToggle.disabled = !locked;
            if (!locked) hardcoreToggle.checked = false;
        }
        [...speciesSelect.options].forEach(option => {
            if (!option.value) return;
            option.hidden = locked && option.value !== "species.human";
            option.disabled = option.hidden;
        });
        if (locked) speciesSelect.value = "species.human";
        else if (speciesSelect.selectedOptions[0]?.disabled) speciesSelect.value = "";
        if (tributeNote) tributeNote.hidden = !locked;
    }
    roleSelect?.addEventListener("change", updateSpeciesLock);
    updateSpeciesLock();

    const portraitUrl = document.getElementById("portraitUrl");
    const deathToggle = document.getElementById("useBwDeath");
    const deathUrl = document.getElementById("customDeathPortraitUrl");
    const deathValue = document.getElementById("deathPortraitValue");
    function updatePreview(kind, url, grayscale = false) {
        const image = document.querySelector(`[data-preview-image="${kind}"]`);
        const placeholder = document.querySelector(`[data-preview-placeholder="${kind}"]`);
        const status = document.querySelector(`[data-preview-status="${kind}"]`);
        if (!image || !placeholder) return;
        const source = (url || "").trim();
        image.hidden = !source;
        placeholder.hidden = Boolean(source);
        image.style.filter = grayscale ? "grayscale(1)" : "none";
        if (source && image.src !== source) image.src = source;
        if (status) status.textContent = source ? "Preview loaded when the image URL is available" : "Waiting for an image URL";
    }
    function updateDeathPreview() {
        const useBw = deathToggle?.checked ?? true;
        if (deathUrl) deathUrl.disabled = useBw;
        if (deathValue) deathValue.value = useBw ? "bw" : (deathUrl?.value.trim() || "");
        updatePreview("death", useBw ? (portraitUrl?.value || "") : (deathUrl?.value || ""), useBw);
    }
    portraitUrl?.addEventListener("input", () => {
        updatePreview("portrait", portraitUrl.value);
        updateDeathPreview();
    });
    deathToggle?.addEventListener("change", updateDeathPreview);
    deathUrl?.addEventListener("input", updateDeathPreview);
    updatePreview("portrait", portraitUrl?.value || "");
    updateDeathPreview();

    const rangeInputs = [...form.querySelectorAll("[data-range-input]")];
    function updateRangeOutput(input) {
        const output = form.querySelector(`output[for="${CSS.escape(input.id)}"]`);
        if (output) output.value = input.value;
    }
    function updateOpposite(input) {
        if (!input.dataset.opposite) return;
        const opposite = document.getElementById(`${input.dataset.rangeFamily}_${input.dataset.opposite}`);
        if (!opposite) return;
        const minimum = Number(input.min);
        const maximum = Number(input.max);
        const oppositeMinimum = Number(opposite.min);
        const oppositeMaximum = Number(opposite.max);
        const ratio = (Number(input.value) - minimum) / (maximum - minimum || 1);
        opposite.value = String(Math.round(oppositeMaximum - ratio * (oppositeMaximum - oppositeMinimum)));
        updateRangeOutput(opposite);
    }
    rangeInputs.forEach(input => {
        input.addEventListener("input", () => {
            updateRangeOutput(input);
            updateOpposite(input);
        });
        updateRangeOutput(input);
    });
    rangeInputs.filter(input => input.dataset.opposite).forEach(input => updateOpposite(input));
    form.addEventListener("submit", event => {
        updateAllocations();
        if (!allocationState("attributes").valid || !allocationState("skills").valid) {
            event.preventDefault();
            showStep(!allocationState("attributes").valid ? 2 : 3);
        }
    });
    updateAllocations();
});
