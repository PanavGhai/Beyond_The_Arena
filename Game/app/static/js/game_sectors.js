document.addEventListener("DOMContentLoaded", () => {
    const siteHeader = document.querySelector(".site-header");
    if (siteHeader) {
        const setHeaderHeight = () => document.documentElement.style.setProperty(
            "--setup-header-height", `${siteHeader.getBoundingClientRect().height}px`
        );
        setHeaderHeight();
        if ("ResizeObserver" in window) new ResizeObserver(setHeaderHeight).observe(siteHeader);
        else window.addEventListener("resize", setHeaderHeight);
    }
    const form = document.getElementById("sectorForm");
    const roster = document.getElementById("sectorRoster");
    if (!form || !roster) return;

    const countInput = document.getElementById("sectorCount");
    const buildButton = document.getElementById("buildSectors");
    const saveButton = document.getElementById("saveSectors");
    const status = document.getElementById("sectorStatus");
    const optionSource = document.getElementById("tributeOptions");
    const sectorTemplate = document.getElementById("sectorTemplate");
    const memberTemplate = document.getElementById("memberTemplate");
    const sectorMin = Number(form.dataset.sectorMinimum);
    const sectorMax = Number(form.dataset.sectorMaximum);
    const memberMin = Number(form.dataset.memberMinimum);
    const memberMax = Number(form.dataset.memberMaximum);
    const uniqueMembers = form.dataset.uniqueMembers === "true";
    const availableCount = Number(form.dataset.availableCount);
    const sectorLabel = form.dataset.sectorLabel || "Sector";
    const defaultMembers = Number(form.dataset.defaultMembers) || memberMin;
    const sectorEditor = document.getElementById("sectorEditor");
    const sectorSummary = document.getElementById("sectorSummary");
    const summaryCards = document.getElementById("sectorSummaryCards");
    const editSectorsButton = document.getElementById("editSectors");
    const saveToast = document.getElementById("saveToast");
    let toastTimer;

    function showToast(message, isError = false) {
        saveToast.textContent = message;
        saveToast.classList.toggle("is-error", isError);
        saveToast.hidden = false;
        window.clearTimeout(toastTimer);
        toastTimer = window.setTimeout(() => { saveToast.hidden = true; }, isError ? 4500 : 2600);
    }

    function addGameActivity(message) {
        const list = document.getElementById("gameActivityList");
        list.querySelector(".activity-empty")?.remove();
        const entry = document.createElement("p");
        entry.className = "activity-entry";
        const time = document.createElement("time");
        time.dateTime = new Date().toISOString();
        time.textContent = new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit" }).format(new Date());
        const text = document.createElement("span");
        text.textContent = message;
        entry.append(time, text);
        list.prepend(entry);
        while (list.children.length > 8) list.lastElementChild.remove();
    }

    function rosterSummaryData() {
        return [...roster.querySelectorAll("[data-sector-card]")].map((card, index) => ({
            number: index + 1,
            members: [...card.querySelectorAll("[data-member-select]")].map(select => {
                const option = [...optionSource.options].find(item => item.value === select.value);
                return option ? {
                    id: option.value,
                    name: option.dataset.name || option.textContent,
                    nickname: option.dataset.nickname || "",
                } : null;
            }).filter(Boolean),
        }));
    }

    function showSavedSummary(sectors) {
        summaryCards.replaceChildren();
        sectors.forEach((sector, index) => {
            const card = document.createElement("article");
            card.className = "sector-summary-card";
            const title = document.createElement("h3");
            title.textContent = `${sectorLabel} ${sector.number || index + 1}`;
            card.appendChild(title);
            const names = document.createElement("ul");
            sector.members.forEach(member => {
                const item = document.createElement("li");
                item.textContent = member.nickname ? `${member.name} (${member.nickname})` : member.name;
                names.appendChild(item);
            });
            card.appendChild(names);
            summaryCards.appendChild(card);
        });
        sectorEditor.hidden = true;
        sectorSummary.hidden = false;
    }

    const mapChoice = document.getElementById("mapChoice");
    const mapSeed = document.getElementById("mapSeed");
    const mapIdValue = document.getElementById("mapIdValue");
    const mapSeedValue = document.getElementById("mapSeedValue");
    const mapLockedValue = document.getElementById("mapLocked");
    const lockButton = document.getElementById("toggleMapLock");
    const previewButton = document.getElementById("useMapSeed");
    const randomSeedButton = document.getElementById("randomMapSeed");
    const previewGrid = document.getElementById("setupArenaGrid");
    const previewStatus = document.getElementById("previewStatus");
    let mapLocked = form.dataset.initiallyLocked === "true";
    let previewRequest = 0;

    function setMapControlsLocked(locked) {
        mapLocked = locked;
        mapLockedValue.value = String(locked);
        mapChoice.disabled = locked;
        mapSeed.disabled = locked;
        previewButton.disabled = locked;
        randomSeedButton.disabled = locked;
        lockButton.textContent = locked ? "Unlock map" : "Lock map";
        lockButton.setAttribute("aria-pressed", String(locked));
        document.getElementById("mapLockStatus").textContent = locked ? "Locked" : "Unlocked";
    }

    function inspectMapCell(cell) {
        document.getElementById("previewTerrain").textContent = cell.dataset.terrain || "—";
        document.getElementById("previewRegion").textContent = cell.dataset.region || "—";
        document.getElementById("previewLocation").textContent = cell.dataset.location || "—";
    }

    function bindMapInspection() {
        previewGrid?.querySelectorAll(".setup-map-cell").forEach(cell => {
            cell.addEventListener("pointerenter", () => inspectMapCell(cell));
            cell.addEventListener("focus", () => inspectMapCell(cell));
        });
    }

    function renderMapPreview(map) {
        previewGrid.replaceChildren();
        previewGrid.style.setProperty("--columns", map.grid_columns);
        previewGrid.style.setProperty("--rows", map.grid_rows);
        previewGrid.parentElement.style.setProperty("--columns", map.grid_columns);
        previewGrid.parentElement.style.setProperty("--rows", map.grid_rows);
        map.grid.forEach(row => row.forEach(item => {
            const cell = document.createElement("button");
            cell.type = "button";
            cell.className = `setup-map-cell${item.playable ? "" : " is-border"}${item.special ? " is-special" : ""}`;
            cell.style.setProperty("--tile-color", item.color);
            if (item.image) cell.style.backgroundImage = `url("${item.image.replace(/["\\()]/g, "")}")`;
            cell.dataset.coordinate = item.coordinate;
            cell.dataset.playable = String(item.playable);
            cell.dataset.terrain = item.terrain;
            cell.dataset.region = item.region;
            cell.dataset.location = item.location;
            cell.setAttribute("aria-label", `${item.coordinate}: ${item.terrain}, ${item.region}${item.special ? `, ${item.special}` : ""}`);
            if (item.special) {
                const marker = document.createElement("span");
                marker.setAttribute("aria-hidden", "true");
                marker.textContent = item.symbol;
                cell.appendChild(marker);
            }
            previewGrid.appendChild(cell);
        }));
        document.getElementById("previewMapName").textContent = map.name;
        document.getElementById("previewMapSize").textContent = `${map.rows} × ${map.columns} playable${map.border_width ? ` · ${map.border_width}-cell ${map.border_type} border` : ""}`;
        document.getElementById("previewMapSeed").textContent = `Seed ${map.seed}`;
        mapChoice.value = map.id;
        mapSeed.value = String(map.seed);
        mapIdValue.value = map.id;
        mapSeedValue.value = String(map.seed);
        bindMapInspection();
    }

    async function updateMapPreview() {
        if (mapLocked) return false;
        const requestId = ++previewRequest;
        previewStatus.textContent = "Generating preview…";
        const url = new URL(form.dataset.previewUrl, window.location.origin);
        url.searchParams.set("map_id", mapChoice.value);
        url.searchParams.set("seed", mapSeed.value.trim());
        try {
            const response = await fetch(url);
            const map = await response.json();
            if (!response.ok) throw new Error(map.error || "Could not generate this preview.");
            if (requestId !== previewRequest) return false;
            renderMapPreview(map);
            previewStatus.textContent = "Preview updated.";
            addGameActivity(`Previewed ${map.name} · seed ${map.seed}`);
            return true;
        } catch (error) {
            if (requestId === previewRequest) previewStatus.textContent = error.message;
            return false;
        }
    }

    async function persistMapLock(locked) {
        if (!locked && mapLocked) {
            // The currently locked selection is already rendered and stored.
        } else if (locked && !await updateMapPreview()) {
            return;
        }
        const body = new URLSearchParams({ map_id: mapChoice.value, seed: mapSeed.value.trim(), locked: String(locked) });
        lockButton.disabled = true;
        try {
            const response = await fetch(form.dataset.lockUrl, {
                method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body,
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || "Could not update the map lock.");
            mapSeed.value = String(result.seed);
            mapSeedValue.value = String(result.seed);
            mapIdValue.value = result.map_id;
            setMapControlsLocked(result.locked);
            previewStatus.textContent = result.locked ? "Map locked." : "Map unlocked.";
            addGameActivity(result.locked ? `Locked ${mapChoice.options[mapChoice.selectedIndex].textContent}` : "Unlocked the arena");
        } catch (error) {
            previewStatus.textContent = error.message;
        } finally {
            lockButton.disabled = false;
        }
    }

    setMapControlsLocked(mapLocked);
    bindMapInspection();
    previewButton?.addEventListener("click", updateMapPreview);
    mapChoice?.addEventListener("change", updateMapPreview);
    mapSeed?.addEventListener("change", updateMapPreview);
    mapSeed?.addEventListener("keydown", event => {
        if (event.key === "Enter") { event.preventDefault(); updateMapPreview(); }
    });
    randomSeedButton?.addEventListener("click", () => {
        const seed = new Uint32Array(1);
        crypto.getRandomValues(seed);
        mapSeed.value = String(seed[0]);
        updateMapPreview();
    });
    lockButton?.addEventListener("click", () => persistMapLock(!mapLocked));

    function pad(value) { return String(value).padStart(3, "0"); }

    function updateMemberRowNames(card) {
        const sectorIndex = Number(card.dataset.sectorIndex);
        const rows = [...card.querySelectorAll("[data-member-row]")];
        rows.forEach((row, index) => {
            const memberIndex = index + 1;
            const select = row.querySelector("[data-member-select]");
            const label = row.querySelector("label");
            const text = row.querySelector("[data-member-label]") || row.querySelector("label span");
            select.name = `sector_${pad(sectorIndex)}_member_${pad(memberIndex)}`;
            select.id = select.name;
            label.htmlFor = select.id;
            if (text) text.textContent = `Member ${memberIndex}`;
            const remove = row.querySelector("[data-remove-member]");
            if (remove) remove.disabled = rows.length <= memberMin;
        });
        const headerCount = card.querySelector("[data-member-count]") || card.querySelector("header span");
        if (headerCount) headerCount.textContent = `${rows.length} member${rows.length === 1 ? "" : "s"}`;
        const add = card.querySelector("[data-add-member]");
        if (add) add.disabled = rows.length >= memberMax;
    }

    function appendMember(card, selected = "") {
        const memberList = card.querySelector("[data-member-list]");
        const fragment = memberTemplate.content.cloneNode(true);
        const row = fragment.querySelector("[data-member-row]");
        const select = row.querySelector("[data-member-select]");
        for (const option of optionSource.options) {
            select.add(new Option(option.textContent, option.value, false, option.value === selected));
        }
        row.querySelector("[data-remove-member]").addEventListener("click", () => {
            const rows = card.querySelectorAll("[data-member-row]");
            if (rows.length <= memberMin) return;
            row.remove();
            updateMemberRowNames(card);
            updateState();
        });
        select.addEventListener("change", updateState);
        memberList.appendChild(fragment);
        updateMemberRowNames(card);
    }

    function makeSector(index, memberValues = []) {
        const card = sectorTemplate.content.cloneNode(true).querySelector("[data-sector-card]");
        card.dataset.sectorIndex = String(index);
        card.querySelector("[data-sector-title]").textContent = `${sectorLabel} ${index}`;
        card.querySelector("[data-add-member]").addEventListener("click", () => {
            if (card.querySelectorAll("[data-member-row]").length < memberMax) appendMember(card);
            updateState();
        });
        const members = memberValues.length ? memberValues : Array(defaultMembers).fill("");
        members.slice(0, memberMax).forEach(value => appendMember(card, value));
        updateMemberRowNames(card);
        return card;
    }

    function currentValues() {
        return [...roster.querySelectorAll("[data-sector-card]")].map(card =>
            [...card.querySelectorAll("[data-member-select]")].map(select => select.value)
        );
    }

    function buildSectors() {
        const previous = currentValues();
        const desired = Number(countInput.value);
        if (!Number.isInteger(desired) || desired < sectorMin || desired > sectorMax) {
            countInput.reportValidity();
            return;
        }
        const fragment = document.createDocumentFragment();
        for (let index = 1; index <= desired; index++) {
            fragment.appendChild(makeSector(index, previous[index - 1] || []));
        }
        roster.replaceChildren(fragment);
        updateState();
    }

    function updateState() {
        const cards = [...roster.querySelectorAll("[data-sector-card]")];
        const allSelects = [...roster.querySelectorAll("[data-member-select]")];
        const selected = allSelects.map(select => select.value).filter(Boolean);
        const unique = new Set(selected).size === selected.length;
        const sectorCountValid = cards.length >= sectorMin && cards.length <= sectorMax && cards.length === Number(countInput.value);
        const memberCountsValid = cards.every(card => {
            const count = card.querySelectorAll("[data-member-row]").length;
            return count >= memberMin && count <= memberMax;
        });
        const complete = allSelects.length > 0 && allSelects.every(select => select.value);
        const enoughTributes = cards.length <= availableCount;
        const valid = sectorCountValid && memberCountsValid && complete && (!uniqueMembers || unique) && enoughTributes;
        saveButton.disabled = !valid;

        allSelects.forEach(select => {
            const selectedElsewhere = uniqueMembers
                ? new Set(allSelects.filter(other => other !== select).map(other => other.value).filter(Boolean))
                : new Set();
            for (const option of select.options) {
                option.disabled = Boolean(option.value && selectedElsewhere.has(option.value));
            }
        });

        if (!enoughTributes) status.textContent = `You have ${availableCount} Tributes, so every Sector needs more available characters before saving.`;
        else if (uniqueMembers && !unique) status.textContent = "Each Tribute can only be assigned once in this save.";
        else if (!complete) status.textContent = "Choose a Tribute for every member slot.";
        else if (!valid) status.textContent = `Use ${sectorMin}–${sectorMax} Sectors, with ${memberMin}–${memberMax} members in each.`;
        else status.textContent = `${selected.length} Tributes assigned across ${cards.length} Sectors.`;
    }

    buildButton.addEventListener("click", buildSectors);
    countInput.addEventListener("change", updateState);
    editSectorsButton.addEventListener("click", () => {
        sectorSummary.hidden = true;
        sectorEditor.hidden = false;
    });
    form.addEventListener("submit", async event => {
        event.preventDefault();
        updateState();
        mapIdValue.value = mapChoice.value;
        mapSeedValue.value = mapSeed.value.trim();
        mapLockedValue.value = String(mapLocked);
        if (saveButton.disabled || !form.reportValidity()) return;

        const originalLabel = saveButton.textContent;
        saveButton.disabled = true;
        saveButton.textContent = "Saving…";
        try {
            const response = await fetch(form.action, {
                method: "POST",
                headers: { Accept: "application/json" },
                body: new FormData(form),
            });
            const result = await response.json();
            if (!response.ok || !result.saved) throw new Error(result.error || "Could not save Sectors.");
            showSavedSummary(result.sectors);
            addGameActivity(`Saved ${result.sectors.length} ${sectorLabel}${result.sectors.length === 1 ? "" : "s"}`);
            showToast(result.message || "Sectors saved.");
        } catch (error) {
            showToast(error.message, true);
            status.textContent = error.message;
        } finally {
            saveButton.textContent = originalLabel;
            updateState();
        }
    });
    roster.querySelectorAll("[data-sector-card]").forEach(card => {
        card.querySelector("[data-add-member]")?.addEventListener("click", () => {
            if (card.querySelectorAll("[data-member-row]").length < memberMax) appendMember(card);
            updateState();
        });
        card.querySelectorAll("[data-member-select]").forEach(select => select.addEventListener("change", updateState));
        card.querySelectorAll("[data-remove-member]").forEach(button => button.addEventListener("click", () => {
            const rows = card.querySelectorAll("[data-member-row]");
            if (rows.length <= memberMin) return;
            button.closest("[data-member-row]").remove();
            updateMemberRowNames(card);
            updateState();
        }));
        updateMemberRowNames(card);
    });
    updateState();
    if (form.dataset.initiallySaved === "true") showSavedSummary(rosterSummaryData());
});
