
from pathlib import Path

from flask import Blueprint, render_template, request, abort, url_for, send_from_directory, redirect, jsonify

from engine.registries.registry_manager import RegistryManager
from engine.compendium.compendium_reader import CompendiumReader
from engine.maps import ArenaRenderer
from engine.character_creation.service import CharacterCreationService
from engine.parsing.tag_parser import parse_file
from engine.saves import GameSaveManager

main_bp = Blueprint("main", __name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def read_tag_file(file_path):
    """Read a tag-value .txt definition into a dictionary."""

    data = {}

    with file_path.open("r", encoding="utf-8-sig") as file:
        for line in file:
            line = line.strip()

            # Ignore blank lines and comments.
            if not line or line.startswith("#"):
                continue

            if "," not in line:
                continue

            tag, value = line.split(",", 1)

            tag = tag.strip()
            value = value.strip().strip('"')

            data[tag] = value

    return data


def load_entity_categories():
    """Load registered entity categories and their entity files."""

    registry_path = (
        PROJECT_ROOT
        / "data"
        / "registries"
        / "entities"
        / "roles.txt"
    )

    entities_root = (
        PROJECT_ROOT
        / "data"
        / "compendium"
        / "entities"
    )

    categories = []

    if not registry_path.exists():
        return categories

    registered_types = []

    with registry_path.open("r", encoding="utf-8-sig") as file:
        for line in file:
            line = line.strip()

            if not line or line.startswith("#") or "," not in line:
                continue

            tag, value = line.split(",", 1)

            if not tag.strip().startswith("entity.role."):
                continue

            folder_name = value.strip().strip('"')

            if folder_name and folder_name not in registered_types:
                registered_types.append(folder_name)

    for folder_name in registered_types:

        category_folder = entities_root / folder_name

        entities = []

        for file_path in sorted(category_folder.glob("*.txt")):

            data = read_tag_file(file_path)

            # Only load actual entity definitions.
            if data.get("object.type") != "entity":
                continue

            name = data.get("entity.name", file_path.stem)

            entity = {
                "id": data.get("object.id", file_path.stem),
                "name": name,
                "nickname": data.get("entity.nickname", ""),
                "role": data.get("entity.role", ""),
                "species": data.get("entity.species", ""),
                "age": data.get("entity.age", ""),
                "portrait_url": data.get("entity.portrait_url", ""),
                "description": data.get("entity.description", ""),
            }

            entities.append(entity)

        categories.append({
            "id": folder_name,
            "name": folder_name.replace("_", " ").title(),
            "count": len(entities),
            "entities": entities,
        })

    return categories


@main_bp.route("/")
def index():
    return render_template("index.html")

# ==========================================
# COMPENDIUM
# ==========================================

@main_bp.route("/compendium")
def compendium():

    registries = RegistryManager(PROJECT_ROOT)

    reader = CompendiumReader(
        PROJECT_ROOT,
        registries
    )

    compendium_data = reader.load_all()

    selected_category = request.args.get("category", "")

    if selected_category:
        compendium_data["entities"] = [
            entity
            for entity in compendium_data["entities"]
            if entity["category_id"] == selected_category
        ]

    return render_template(
        "compendium.html",
        **compendium_data,
        selected_category=selected_category
    )


@main_bp.route("/character/create", methods=["GET", "POST"], endpoint="create_character")
def create_character():
    service = CharacterCreationService(PROJECT_ROOT)
    form_data = request.form.to_dict() if request.method == "POST" else {}
    errors = []
    if request.method == "POST":
        saved_path, report = service.save(request.form)
        if report.valid and saved_path:
            return redirect(url_for(
                "main.character_sheet",
                role=request.form.get("role", ""),
                character_file=saved_path.stem,
            ))
        errors = report.errors

    roles = service.references["roles"]
    default_role = form_data.get("role") or next(
        (item["id"] for item in roles if item["id"] == "tributes"),
        roles[0]["id"] if roles else "",
    )
    locked_species = service.references["settings"].get(
        f"character_creation.role_species.{default_role}", ""
    )
    default_species = form_data.get("species") or locked_species or (
        service.references["species"][0]["id"] if service.references["species"] else ""
    )
    return render_template(
        "character_creator.html",
        references=service.references,
        settings=service.references["settings"],
        form_data=form_data,
        errors=errors,
        default_role=default_role,
        default_species=default_species,
    )


@main_bp.route("/character/<role>/<character_file>", endpoint="character_sheet")
def character_sheet(role, character_file):
    service = CharacterCreationService(PROJECT_ROOT)
    roles = service.registries.get_registered_entries("roles")
    folder = roles.get(role)
    if not folder or not folder.replace("_", "").isalnum():
        abort(404)
    category_root = (PROJECT_ROOT / "data" / "compendium" / "entities" / folder).resolve()
    character_path = (category_root / f"{character_file}.txt").resolve()
    if character_path.parent != category_root or not character_path.is_file():
        abort(404)
    document = parse_file(character_path)
    if document.get("object.type") != "entity" or document.get("entity.role") != role:
        abort(404)
    return render_template("character_sheet.html", character=service.sheet_data(character_path))


# ==========================================
# TAG-DRIVEN ARENA PAGES
# ==========================================

def arena_renderer():
    return ArenaRenderer(
        PROJECT_ROOT,
        asset_url=lambda name: url_for("main.game_asset", filename=name),
    )


# ==========================================
# TAG-BASED GAME SETUP SAVES
# ==========================================

def game_save_manager():
    return GameSaveManager(PROJECT_ROOT)


@main_bp.route("/play")
def play():
    manager = game_save_manager()
    saves = manager.list_saves()
    return render_template(
        "game_saves.html",
        saves=saves,
        save_count=len(saves),
        save_limit=manager.save_limit,
        message=request.args.get("message", ""),
        character_count=len(manager.available_tributes("")),
    )


@main_bp.route("/play/new", methods=["POST"])
def create_game_save():
    manager = game_save_manager()
    try:
        game = manager.create_save(request.form.get("game_name", ""))
    except ValueError as error:
        saves = manager.list_saves()
        return render_template(
            "game_saves.html", saves=saves, save_count=len(saves),
            save_limit=manager.save_limit, message=str(error),
            character_count=len(manager.available_tributes("")),
        ), 400
    renderer = arena_renderer()
    arenas = renderer.list_arenas()
    preferred = manager.config.get("game_setup.default_arena", "")
    default_arena = next((item for item in arenas if item["id"] == preferred), None)
    if default_arena is None and arenas:
        default_arena = arenas[0]
    if default_arena:
        preview = renderer.render_map(default_arena["id"])
        manager.choose_map(game["id"], default_arena["id"], preview["seed"])
        return redirect(url_for("main.game_sectors", game_id=game["id"]))
    return redirect(url_for("main.game_map_selection", game_id=game["id"]))


@main_bp.route("/play/<game_id>/open", methods=["POST"])
def open_game_save(game_id):
    manager = game_save_manager()
    game = manager.load_save(game_id)
    if not game:
        abort(404)
    if not game["map_id"]:
        return redirect(url_for("main.game_map_selection", game_id=game_id))
    return redirect(url_for("main.game_sectors", game_id=game_id))


@main_bp.route("/play/<game_id>/delete", methods=["POST"])
def delete_game_save(game_id):
    manager = game_save_manager()
    if not manager.delete_save(game_id):
        abort(404)
    return redirect(url_for("main.play", message="Save deleted."))


@main_bp.route("/play/<game_id>/map", methods=["GET", "POST"])
def game_map_selection(game_id):
    manager = game_save_manager()
    game = manager.load_save(game_id)
    if not game:
        abort(404)
    renderer = arena_renderer()
    if request.method == "POST":
        map_id = request.form.get("map_id", "").strip()
        raw_seed = request.form.get("seed", "").strip()
        try:
            preview = renderer.render_map(map_id, raw_seed or None)
            manager.choose_map(game_id, map_id, preview["seed"])
        except KeyError:
            abort(404)
        except ValueError as error:
            return redirect(url_for("main.game_map_selection", game_id=game_id, message=str(error)))
        return redirect(url_for("main.game_sectors", game_id=game_id))

    arenas = []
    for item in renderer.list_arenas():
        arena = dict(item)
        arena["preview"] = renderer.render_map(item["id"])
        arenas.append(arena)
    return render_template(
        "arenas.html", arenas=arenas, selection_mode=True, game=game,
        message=request.args.get("message", ""),
    )


@main_bp.route("/play/<game_id>/sectors", methods=["GET", "POST"])
def game_sectors(game_id):
    manager = game_save_manager()
    game = manager.load_save(game_id)
    if not game:
        abort(404)
    if not game["map_id"]:
        return redirect(url_for("main.game_map_selection", game_id=game_id))

    renderer = arena_renderer()
    selected_map = renderer.render_map(game["map_id"], game["map_seed"] or None)
    arenas = renderer.list_arenas()
    tributes = manager.available_tributes(game_id)
    limits = manager.setup_limits()
    errors = []
    message = request.args.get("message", "")
    if request.method == "POST":
        try:
            sectors = manager.sectors_from_form(request.form)
            map_id = request.form.get("map_id", game["map_id"]).strip()
            map_seed = request.form.get("map_seed", game["map_seed"]).strip()
            map_locked = request.form.get("map_locked", "false").strip().lower() in ("true", "1", "yes")
            preview = renderer.render_map(map_id, map_seed or None)
            manager.choose_map(game_id, map_id, preview["seed"], locked=map_locked)
            manager.save_sectors(game_id, sectors)
            if request.accept_mimetypes.best == "application/json":
                tributes_by_id = {
                    tribute["id"]: tribute for tribute in manager.available_tributes(game_id)
                }
                saved_sectors = [{
                    "number": index,
                    "name": sector.get("name") or f"{limits['sector_label']} {index}",
                    "members": [{
                        "id": member_id,
                        "name": tributes_by_id[member_id]["name"],
                        "nickname": tributes_by_id[member_id]["nickname"],
                    } for member_id in sector["members"]],
                } for index, sector in enumerate(sectors, start=1)]
                return jsonify({"saved": True, "message": "Sectors saved.", "sectors": saved_sectors})
            return redirect(url_for("main.game_sectors", game_id=game_id, message="Sector setup saved."))
        except (KeyError, ValueError) as error:
            if request.accept_mimetypes.best == "application/json":
                return jsonify({"saved": False, "error": str(error)}), 400
            errors.append(str(error))
            try:
                sectors = manager.sectors_from_form(request.form)
            except ValueError:
                sectors = manager.initial_sectors(game_id, len(tributes))
            sector_count_value = request.form.get("sector_count", str(len(sectors)))
    else:
        sectors = manager.initial_sectors(game_id, len(tributes))
        sector_count_value = str(len(sectors))

    return render_template(
        "game_sectors.html", game=game, selected_map=selected_map, arenas=arenas,
        sectors=sectors, sector_count_value=sector_count_value,
        tributes=tributes, limits=limits, errors=errors, message=message,
    )


@main_bp.route("/play/<game_id>/map-preview")
def game_map_preview(game_id):
    manager = game_save_manager()
    if not manager.load_save(game_id):
        abort(404)
    map_id = request.args.get("map_id", "").strip()
    seed = request.args.get("seed", "").strip()
    try:
        rendered = arena_renderer().render_map(map_id, seed or None)
    except KeyError:
        abort(404)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({
        "id": rendered["id"], "name": rendered["name"],
        "rows": rendered["rows"], "columns": rendered["columns"],
        "seed": rendered["seed"], "grid_rows": rendered["grid_rows"],
        "grid_columns": rendered["grid_columns"],
        "border_width": rendered["border_width"],
        "border_type": rendered["edge_region"]["type"] if rendered["edge_region"] else "",
        "grid": [[{
            "coordinate": cell["coordinate"], "playable": cell["playable"],
            "color": cell["terrain_color"], "image": cell["terrain_image_url"],
            "terrain": cell["terrain_name"], "region": cell["region_name"],
            "location": cell["location_name"],
            "special": cell["special"]["name"] if cell["special"] else "",
            "symbol": cell["special"].get("symbol", "◆") if cell["special"] else "",
        } for cell in row] for row in rendered["grid"]],
    })


@main_bp.route("/play/<game_id>/map-lock", methods=["POST"])
def game_map_lock(game_id):
    manager = game_save_manager()
    if not manager.load_save(game_id):
        abort(404)
    map_id = request.form.get("map_id", "").strip()
    seed = request.form.get("seed", "").strip()
    locked = request.form.get("locked", "").strip().lower()
    if locked not in ("true", "false"):
        return jsonify({"error": "Choose whether to lock or unlock the map."}), 400
    try:
        rendered = arena_renderer().render_map(map_id, seed or None)
        manager.choose_map(game_id, map_id, rendered["seed"], locked=locked == "true")
    except KeyError:
        abort(404)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"map_id": map_id, "seed": rendered["seed"], "locked": locked == "true"})


@main_bp.route("/arenas")
def arenas_page():
    renderer = arena_renderer()
    arenas = []
    for item in renderer.list_arenas():
        arena = dict(item)
        arena["preview"] = renderer.render_map(item["id"])
        arenas.append(arena)
    return render_template("arenas.html", arenas=arenas)


@main_bp.route("/map/<map_id>")
def map_page(map_id):
    renderer = arena_renderer()
    maps = renderer.list_arenas()
    try:
        seed_override = None
        raw_seed = request.args.get("seed", "").strip()
        if raw_seed:
            seed_override = raw_seed
        selected_map = renderer.render_map(map_id, seed_override)
    except KeyError:
        abort(404)
    except ValueError as error:
        abort(400, description=str(error))
    return render_template(
        "map.html",
        maps=maps,
        selected_map=selected_map,
        setup_mode=False,
        current_map_confirmed=False,
        message=request.args.get("message", ""),
    )



@main_bp.route("/assets/<path:filename>")
def game_asset(filename):
    """Serve game data assets separately from website static files."""
    asset_root = PROJECT_ROOT / "data" / "assets"
    return send_from_directory(asset_root, filename)
