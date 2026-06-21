from flask import Flask, render_template, jsonify, request, Response
import subprocess, yaml, os, re

app = Flask(__name__)
COMPOSE_PATH   = os.environ.get("COMPOSE_PATH",   "/DATA/TF2serveur/docker-compose.yml")
CONTAINER_NAME = os.environ.get("CONTAINER_NAME", "tf2serveur-northstar-attrition-1")
SERVICE_NAME   = os.environ.get("SERVICE_NAME",   "northstar-attrition")

FD_MAPS = [
    {"id": "mp_forwardbase_kodai", "name": "Kodai",      "label": "Forward Base Kodai",  "img": "https://static.wikia.nocookie.net/titanfall/images/b/b6/Forwardbase_Kodai.jpg"},
    {"id": "mp_crashsite3",        "name": "Crash Site", "label": "Crash Site",           "img": "https://static.wikia.nocookie.net/titanfall/images/5/5b/Crash_Site_TF2.jpg"},
    {"id": "mp_homestead",         "name": "Homestead",  "label": "Homestead",            "img": "https://static.wikia.nocookie.net/titanfall/images/e/e0/Homestead.jpg"},
    {"id": "mp_relic0",            "name": "Relic",      "label": "Relic",                "img": "https://static.wikia.nocookie.net/titanfall/images/2/2d/Relic.jpg"},
    {"id": "mp_drydock",           "name": "Drydock",    "label": "Dry Dock",             "img": "https://static.wikia.nocookie.net/titanfall/images/7/7b/Drydock.jpg"},
    {"id": "mp_thaw",              "name": "Boneyard",   "label": "Boneyard",             "img": "https://static.wikia.nocookie.net/titanfall/images/0/03/Boneyard_TF2.jpg"},
    {"id": "mp_hub_timeshift",     "name": "Glitch",     "label": "Glitch",               "img": "https://static.wikia.nocookie.net/titanfall/images/8/8d/Glitch.jpg"},
    {"id": "mp_eden",              "name": "Eden",       "label": "Eden",                 "img": "https://static.wikia.nocookie.net/titanfall/images/4/4e/Eden.jpg"},
    {"id": "mp_jaylen",            "name": "Nexus",      "label": "Nexus",                "img": "https://static.wikia.nocookie.net/titanfall/images/d/d9/Nexus.jpg"},
    {"id": "mp_wargames",          "name": "War Games",  "label": "War Games",            "img": "https://static.wikia.nocookie.net/titanfall/images/1/1e/War_Games.jpg"},
]

FD_DIFFICULTIES = [
    {"id": "fd_easy",   "name": "Easy",   "label": "Facile"},
    {"id": "fd_normal", "name": "Normal", "label": "Normal"},
    {"id": "fd_hard",   "name": "Hard",   "label": "Difficile"},
    {"id": "fd_master", "name": "Master", "label": "Master"},
    {"id": "fd_insane", "name": "Insane", "label": "Insane"},
]

# Console vars (ns_xxx) -> go in NS_EXTRA_ARGUMENTS
# Playlist vars (fd_xxx) -> go in setplaylistvaroverrides
FD_PARAMS = [
    # ── CONSOLE VARS ──
    {"key": "ns_reaper_warpfall_kill",    "type": "toggle", "default": 1, "group": "Reapers",
     "label": "Reaper Warpfall Kill",    "desc": "Les Reapers tuent les Titans en Warpfall. Désactiver pour plus de clémence."},
    {"key": "ns_ronin_fair_phase",        "type": "toggle", "default": 0, "group": "Titans IA",
     "label": "Ronin Phase Fair",        "desc": "Ronin ne se suicide plus s'il matérialise dans un Titan ennemi — applique seulement 5000 dégâts."},
    {"key": "ns_fd_disable_respawn_dropship","type":"toggle","default":0,"group":"Gameplay",
     "label": "Respawn sans dropship",   "desc": "Respawn via Drop Pod ou directement près du Harvester au lieu du dropship."},
    {"key": "ns_fd_min_numplayers_to_start","type":"slider","default":1,"min":1,"max":4,"step":1,"group":"Gameplay",
     "label": "Joueurs min pour démarrer","desc": "Nombre minimum de joueurs requis pour lancer les vagues."},
    # ── PLAYLIST VARS ──
    {"key": "fd_allow_elite_titans",      "type": "toggle", "default": 0, "group": "Titans IA",
     "label": "Elite Titans",            "desc": "Autorise les Titans Elite à spawner dans les vagues."},
    {"key": "fd_allow_titanfall_block",   "type": "toggle", "default": 0, "group": "Gameplay",
     "label": "Titanfall Block Event",   "desc": "Autorise certaines maps à utiliser l'événement Titanfall Block."},
    {"key": "fd_arc_titans_uses_arc_cannon","type":"toggle","default":0,"group":"Titans IA",
     "label": "Arc Titans → Arc Cannon", "desc": "Les Arc Titans utilisent l'Arc Cannon au lieu du Leadwall."},
    {"key": "fd_campaign_shield_captains","type": "toggle", "default": 0, "group": "Ennemis",
     "label": "Shield Captains",         "desc": "Fait spawner les Shield Captains de la campagne en Master/Insane."},
    {"key": "fd_campaign_ticks",          "type": "toggle", "default": 0, "group": "Ennemis",
     "label": "Campaign Ticks",          "desc": "Les Ticks des Drop Pods utilisent le modèle campagne et comptent pour la completion des vagues."},
    {"key": "fd_grunts_uses_grenades",    "type": "toggle", "default": 0, "group": "Ennemis",
     "label": "Grenades pour Grunts",    "desc": "Autorise les Grunts à lancer des grenades."},
    {"key": "fd_visible_drop_points",     "type": "toggle", "default": 0, "group": "Gameplay",
     "label": "Drop Points visibles",    "desc": "Affiche les marqueurs Titanfall pour les ennemis qui spawnent."},
    {"key": "fd_smart_pistol_easy_mode",  "type": "toggle", "default": 0, "group": "Gameplay",
     "label": "Smart Pistol Easy",       "desc": "Les joueurs ont le Smart Pistol en secondaire en mode Easy."},
    {"key": "fd_rodeo_highlight",         "type": "toggle", "default": 0, "group": "Gameplay",
     "label": "Rodeo Highlight",         "desc": "Les pilotes deviennent verts en surbrillance quand ils font un rodeo sur un Titan."},
    {"key": "fd_minimap_ping_sound",      "type": "toggle", "default": 0, "group": "Gameplay",
     "label": "Minimap Ping Sound",      "desc": "Joue un son subtil quand la minimap ping un ennemi qui spawne."},
    {"key": "fd_dropship_battery_drop",   "type": "toggle", "default": 0, "group": "Ennemis",
     "label": "Battery Drop Dropship",   "desc": "Les Dropships IMC lâchent une Amped Battery si détruits."},
    {"key": "enable_rocket_turrets",      "type": "toggle", "default": 0, "group": "Gameplay",
     "label": "Rocket Turrets",          "desc": "Remplace les Sentry Turrets par les Rocket Turrets inutilisées."},
    {"key": "fd_grunt_at_weapon_users",   "type": "slider", "default": 0, "min": 0, "max": 4, "step": 1, "group": "Ennemis",
     "label": "Grunts AT Weapons",       "desc": "Nombre de squads de Grunts utilisant des armes anti-Titan (0-4, 4 = tous)."},
    {"key": "fd_grunt_shield_captains",   "type": "slider", "default": 0, "min": 0, "max": 4, "step": 1, "group": "Ennemis",
     "label": "Shield Captains count",   "desc": "Nombre de squads de Grunts qui deviennent des Shield Captains (0-4)."},
    {"key": "fd_wave_buy_time",           "type": "slider", "default": 60, "min": 10, "max": 300, "step": 10, "group": "Gameplay",
     "label": "Temps inter-vagues (s)",  "desc": "Durée de la pause entre les vagues pour acheter (défaut : 60s)."},
    {"key": "rodeo_battery_disembark_to_pickup","type":"toggle","default":1,"group":"Gameplay",
     "label": "Battery pickup en Titan", "desc": "Passer sur une batterie en Titan la ramasse (désactiver = comportement campagne)."},
    {"key": "enable_spectre_hacking",     "type": "toggle", "default": 0, "group": "Ennemis",
     "label": "Spectre Hacking (TF1)",   "desc": "Réactive le hacking des Spectres comme dans Titanfall 1."},
]

CONSOLE_KEYS = {p["key"] for p in FD_PARAMS if p["key"].startswith("ns_")}
PLAYLIST_KEYS = {p["key"] for p in FD_PARAMS if not p["key"].startswith("ns_")}

def load_compose():
    with open(COMPOSE_PATH) as f:
        return yaml.safe_load(f)

def save_compose(data):
    with open(COMPOSE_PATH, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

def get_env(compose):
    return compose["services"][SERVICE_NAME]["environment"]

def get_extra_args(compose):
    return get_env(compose).get("NS_EXTRA_ARGUMENTS", "")

def set_arg(args, key, value):
    pattern = r"\+" + re.escape(key) + r"\s+\S+"
    rep = "+" + key + " " + str(value)
    if re.search(pattern, args):
        return re.sub(pattern, rep, args)
    return args.rstrip() + "\n        +" + key + " " + str(value) + "\n"

def get_playlist_overrides(args):
    m = re.search(r"\+setplaylistvaroverrides\s+\"([^\"]*)\"", args)
    return m.group(1) if m else ""

def set_playlist_overrides(args, overrides_str):
    pattern = r'\+setplaylistvaroverrides\s+"[^"]*"'
    rep = '+setplaylistvaroverrides "' + overrides_str + '"'
    if re.search(pattern, args):
        return re.sub(pattern, rep, args)
    return args.rstrip() + "\n        " + rep + "\n"

def parse_overrides(overrides_str):
    result = {}
    pairs = overrides_str.strip().split()
    for i in range(0, len(pairs)-1, 2):
        result[pairs[i]] = pairs[i+1]
    return result

def build_overrides(d):
    return " ".join(k + " " + str(v) for k, v in d.items())

def get_current_settings():
    try:
        args = get_extra_args(load_compose())
        m = re.search(r"\+map\s+(\S+)", args)
        d = re.search(r"\+setplaylist\s+(\S+)", args)
        overrides_str = get_playlist_overrides(args)
        overrides = parse_overrides(overrides_str)
        params = {}
        for p in FD_PARAMS:
            k = p["key"]
            if k in CONSOLE_KEYS:
                pat = r"\+" + re.escape(k) + r"\s+(\S+)"
                match = re.search(pat, args)
                params[k] = match.group(1) if match else str(p["default"])
            else:
                params[k] = overrides.get(k, str(p["default"]))
        return {
            "map": m.group(1) if m else "mp_forwardbase_kodai",
            "difficulty": d.group(1) if d else "fd_normal",
            "params": params,
        }
    except Exception as e:
        return {"map": "mp_forwardbase_kodai", "difficulty": "fd_normal", "params": {}, "error": str(e)}

def docker_exec(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr

@app.route("/")
def index():
    s = get_current_settings()
    groups = {}
    for p in FD_PARAMS:
        g = p["group"]
        if g not in groups:
            groups[g] = []
        groups[g].append({**p, "current": s["params"].get(p["key"], str(p["default"]))})
    return render_template("index.html", maps=FD_MAPS, difficulties=FD_DIFFICULTIES,
                           current_map=s["map"], current_difficulty=s["difficulty"],
                           param_groups=groups)

@app.route("/api/status")
def api_status():
    code, out, _ = docker_exec("docker inspect -f '{{.State.Status}}' " + CONTAINER_NAME)
    running = out.strip() == "running"
    _, logs, _ = docker_exec("docker logs --tail 200 " + CONTAINER_NAME + " 2>&1")
    players = []
    for line in logs.splitlines():
        m = re.search(r"Player connect started.*player (.+?) \[", line)
        if m:
            name = m.group(1).strip()
            if name not in players:
                players.append(name)
        d = re.search(r"Player (.+?) disconnected", line)
        if d:
            name = d.group(1).strip()
            if name in players:
                players.remove(name)
    return jsonify({"running": running, "players": players, "player_count": len(players), **get_current_settings()})

@app.route("/api/apply", methods=["POST"])
def api_apply():
    data = request.json
    try:
        compose = load_compose()
        args = get_extra_args(compose)
        if data.get("map"):
            args = set_arg(args, "map", data["map"])
        if data.get("difficulty"):
            args = set_arg(args, "setplaylist", data["difficulty"])
            args = set_arg(args, "mp_gamemode", data["difficulty"])
        # Console vars
        for k, v in (data.get("params") or {}).items():
            if k in CONSOLE_KEYS:
                args = set_arg(args, k, v)
        # Playlist vars
        overrides_str = get_playlist_overrides(args)
        overrides = parse_overrides(overrides_str)
        for k, v in (data.get("params") or {}).items():
            if k in PLAYLIST_KEYS:
                overrides[k] = v
        args = set_playlist_overrides(args, build_overrides(overrides))
        compose["services"][SERVICE_NAME]["environment"]["NS_EXTRA_ARGUMENTS"] = args
        save_compose(compose)
        return jsonify({"ok": True, "message": "Config sauvegardee. Redemarre pour appliquer."})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500

@app.route("/api/restart", methods=["POST"])
def api_restart():
    code, out, err = docker_exec("docker restart " + CONTAINER_NAME)
    return jsonify({"ok": code == 0, "message": "Serveur redemarre." if code == 0 else err or out})

@app.route("/api/stop", methods=["POST"])
def api_stop():
    code, _, err = docker_exec("docker stop " + CONTAINER_NAME)
    return jsonify({"ok": code == 0, "message": "Serveur arrete." if code == 0 else err})

@app.route("/api/start", methods=["POST"])
def api_start():
    code, _, err = docker_exec("docker start " + CONTAINER_NAME)
    return jsonify({"ok": code == 0, "message": "Serveur demarre." if code == 0 else err})

@app.route("/api/logs/stream")
def logs_stream():
    def generate():
        proc = subprocess.Popen(
            ["docker", "logs", "-f", "--tail", "100", CONTAINER_NAME],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
        )
        try:
            for line in proc.stdout:
                yield "data: " + line.rstrip() + "\n\n"
        finally:
            proc.terminate()
    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
