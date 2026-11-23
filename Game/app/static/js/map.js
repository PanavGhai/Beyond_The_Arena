document.addEventListener("DOMContentLoaded", () => {
    const toast = document.getElementById("saveToast");
    if (toast) {
        toast.querySelector("button")?.addEventListener("click", () => toast.remove());
        window.setTimeout(() => toast.remove(), 6500);
    }

    const selector = document.getElementById("mapSelector");
    if (selector) selector.addEventListener("change", () => {
        const target = new URL("/map/" + encodeURIComponent(selector.value), window.location.origin);
        if (new URLSearchParams(window.location.search).get("setup") === "1") {
            target.searchParams.set("setup", "1");
        }
        const gameId = new URLSearchParams(window.location.search).get("game_id");
        if (gameId) target.searchParams.set("game_id", gameId);
        window.location.href = target.toString();
    });

    const regen = document.getElementById("regenerateMap");
    const randomize = document.getElementById("randomizeMap");
    const seedInput = document.getElementById("mapSeed");
    function loadSeed(seed) {
        if (!seedInput || !seedInput.reportValidity()) return;
        const input = String(seed ?? "").trim();
        if (!input) return;
        const url = new URL(window.location.href);
        url.searchParams.set("seed", input);
        window.location.href = url.toString();
    }
    if (regen) regen.addEventListener("click", () => loadSeed(seedInput?.value));
    if (seedInput) seedInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") loadSeed(seedInput.value);
    });
    if (randomize) randomize.addEventListener("click", () => {
        const seed = new Uint32Array(1);
        crypto.getRandomValues(seed);
        seedInput.value = String(seed[0]);
        loadSeed(seed[0]);
    });

    const setupFlow = document.getElementById("mapSetupFlow");
    if (setupFlow) {
        const teamsReady = setupFlow.dataset.teamsReady === "true";
        const gameReady = setupFlow.dataset.gameReady === "true";
        const token = "arena-setup:" + setupFlow.dataset.setupToken;
        let progress = { npc: false, loot: false };
        try {
            progress = { ...progress, ...JSON.parse(sessionStorage.getItem(token) || "{}") };
        } catch (_) {}
        if (gameReady) progress = { npc: true, loot: true };

        const startForm = document.getElementById("startGameForm");
        const npcInput = startForm?.querySelector('[name="npc_ready"]');
        const lootInput = startForm?.querySelector('[name="loot_ready"]');
        const gameFlow = document.getElementById("gameFlow");

        function updateSetupProgress() {
            for (const step of ["npc", "loot"]) {
                const status = setupFlow.querySelector(`[data-roll-status="${step}"]`);
                if (status) {
                    status.textContent = progress[step] ? "Step ready" : "Not ready";
                    status.classList.toggle("is-ready", Boolean(progress[step]));
                }
            }
            setupFlow.querySelectorAll("[data-roll-reroll], [data-roll-confirm]").forEach(button => {
                button.disabled = !teamsReady || gameReady;
            });
            const complete = teamsReady && progress.npc && progress.loot;
            if (startForm) startForm.hidden = !complete && !gameReady;
            if (npcInput) npcInput.value = progress.npc ? "1" : "0";
            if (lootInput) lootInput.value = progress.loot ? "1" : "0";
            if (gameFlow) {
                gameFlow.textContent = gameReady
                    ? "Game setup is complete. The game is ready."
                    : complete
                        ? "Map, teams, NPC setup, and loot setup are ready."
                        : "Complete the NPC and loot setup steps to start the game.";
            }
        }

        setupFlow.querySelectorAll("[data-roll-reroll]").forEach(button => {
            button.addEventListener("click", () => {
                if (!teamsReady || gameReady) return;
                progress[button.dataset.rollReroll] = false;
                try { sessionStorage.setItem(token, JSON.stringify(progress)); } catch (_) {}
                updateSetupProgress();
            });
        });
        setupFlow.querySelectorAll("[data-roll-confirm]").forEach(button => {
            button.addEventListener("click", () => {
                if (!teamsReady || gameReady) return;
                progress[button.dataset.rollConfirm] = true;
                try { sessionStorage.setItem(token, JSON.stringify(progress)); } catch (_) {}
                updateSetupProgress();
            });
        });
        updateSetupProgress();
    }

    const grid = document.getElementById("arenaGrid");
    const inspector = document.getElementById("cellInfo");
    if (!grid || !inspector) return;
    const title = document.getElementById("inspectorTitle");
    const fields = Object.fromEntries(
        [...inspector.querySelectorAll("[data-inspector-field]")]
            .map((element) => [element.dataset.inspectorField, element])
    );

    function inspectTile(tile) {
        const values = {
            coordinate: tile.dataset.coordinate,
            location: tile.dataset.location,
            region: tile.dataset.region,
            biome: tile.dataset.biome,
            terrain: `${tile.dataset.terrainName || tile.dataset.terrainId} (${tile.dataset.terrainId})`,
            objects: JSON.parse(tile.dataset.objects || "[]").map(item => item.name).join(", "),
            overlays: JSON.parse(tile.dataset.overlays || "[]").map(item => item.name).join(", "),
            conditions: JSON.parse(tile.dataset.conditions || "[]").map(item => item.name || item.id).join(", ")
        };
        title.textContent = tile.dataset.special || tile.dataset.region || "Terrain details";
        Object.entries(values).forEach(([key, value]) => {
            if (fields[key]) fields[key].textContent = value || "—";
        });
    }

    grid.addEventListener("pointerover", (event) => {
        const tile = event.target.closest(".map-cell");
        if (tile && grid.contains(tile)) inspectTile(tile);
    });
    grid.addEventListener("focusin", (event) => {
        const tile = event.target.closest(".map-cell");
        if (tile && grid.contains(tile)) inspectTile(tile);
    });
    grid.addEventListener("click", (event) => {
        const tile = event.target.closest(".map-cell");
        if (!tile || !grid.contains(tile) || tile.dataset.playable !== "true") return;
        document.dispatchEvent(new CustomEvent("tile-selected", { detail: {
            row: tile.dataset.row ? Number(tile.dataset.row) : null,
            column: tile.dataset.column ? Number(tile.dataset.column) : null,
            gridRow: Number(tile.dataset.gridRow),
            gridColumn: Number(tile.dataset.gridColumn),
            playable: tile.dataset.playable === "true",
            coordinate: tile.dataset.coordinate,
            tileId: tile.dataset.tileId,
            terrainId: tile.dataset.terrainId,
            biome: tile.dataset.biome,
            regionId: tile.dataset.regionId,
            region: tile.dataset.region,
            location: tile.dataset.location,
            special: tile.dataset.special || null,
            objects: JSON.parse(tile.dataset.objects || "[]"),
            overlays: JSON.parse(tile.dataset.overlays || "[]"),
            conditions: JSON.parse(tile.dataset.conditions || "[]")
        }}));
    });
});
