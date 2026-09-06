"""Versioned explicit route grammar. Units: metres, degrees, right-handed Z up."""
from copy import deepcopy
from pathlib import Path
import math
import yaml

DEFAULTS = {
    "schema_version": 1, "name": "cave", "split": "development",
    "corridor": {"width": 4.5, "height": 3.8, "variation": 0.17, "section": "irregular"},
    "robot": {"radius": 0.35, "margin": 0.2},
    "geology": {"amplitude": 0.32, "strata": 0.18, "formations": 10},
    "mesh": {"visual_voxel": 0.20, "collision_voxel": 0.34, "max_voxels": 18000000},
    "material": {"style": "limestone", "seed": 100, "roughness": 0.87},
    "branches": [], "chambers": [], "bottlenecks": [],
    "validation": {"max_slope_degrees": 40.0},
}
SECTIONS = {"oval", "elliptical", "flattened", "tall", "triangular", "asymmetric", "fracture", "irregular"}


def merge(base, override):
    result = deepcopy(base)
    for k, v in override.items():
        result[k] = merge(result[k], v) if isinstance(v, dict) and isinstance(result.get(k), dict) else deepcopy(v)
    return result


def number(value, name, lo, hi):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lo <= value <= hi:
        raise ValueError(f"{name} must be finite in [{lo}, {hi}]")


def check_commands(commands, name="route"):
    if not isinstance(commands, list) or not commands:
        raise ValueError(f"{name} must contain route commands")
    for c in commands:
        unknown = set(c) - {"straight", "turn", "radius", "slope", "width", "height", "section"}
        if unknown or (("straight" in c) == ("turn" in c)):
            raise ValueError(f"Invalid {name} command: {c}")
        if "straight" in c:
            number(c["straight"], "straight", 0.5, 500)
        else:
            number(c["turn"], "turn", -180, 180)
            if abs(c["turn"]) < 1:
                raise ValueError("Use a straight for turns below 1 degree")
            number(c.get("radius", 4), "radius", 1, 100)
        number(c.get("slope", 0), "slope", -70, 70)
        if c.get("section", "irregular") not in SECTIONS:
            raise ValueError("Unknown cross-section")


def load_spec(config):
    raw = yaml.safe_load(Path(config).read_text(encoding="utf-8")) if isinstance(config, (str, Path)) else deepcopy(config)
    if not isinstance(raw, dict):
        raise ValueError("CaveSpec must be a mapping")
    unknown = set(raw) - (set(DEFAULTS) | {"route", "description", "ood_factors", "sampling"})
    if unknown:
        raise ValueError(f"Unknown CaveSpec keys: {sorted(unknown)}")
    for key in ("corridor", "robot", "geology", "mesh", "material", "validation"):
        allowed = set(DEFAULTS[key]) | ({"palette", "prior_source", "detail_anisotropy"} if key == "material" else set())
        if set(raw.get(key, {})) - allowed:
            raise ValueError(f"Unknown {key} parameters")
    s = merge(DEFAULTS, raw)
    if 'sampling' in s:
        if not isinstance(s['sampling'], dict) or set(s['sampling']) != {'algorithm', 'family', 'layout_attempts', 'rejected_layouts', 'factor_scope'}:
            raise ValueError('Invalid sampling provenance')
        number(s['sampling']['layout_attempts'], 'sampling.layout_attempts', 1, 1000)
    if s["schema_version"] != 1:
        raise ValueError("Only schema_version: 1 is supported")
    check_commands(s.get("route"))
    number(s["robot"]["radius"], "robot.radius", 0.05, 5)
    number(s["robot"]["margin"], "robot.margin", 0.02, 2)
    safety = s["robot"]["radius"] + s["robot"]["margin"]
    for dimension in ("width", "height"):
        number(s["corridor"][dimension], dimension, safety * 2 + 0.2, 30)
    number(s["corridor"]["variation"], "variation", 0, 0.4)
    if s["corridor"]["section"] not in SECTIONS:
        raise ValueError("Unknown corridor section")
    for c in s["route"] + [c for b in s["branches"] for c in b.get("route", [])]:
        for d in ("width", "height"):
            if d in c:
                number(c[d], d, safety * 2 + 0.2, 30)
    for key in ("visual_voxel", "collision_voxel"):
        number(s["mesh"][key], key, 0.08, 0.8)
    minimum_dimension=2*(safety+2.1*s["mesh"]["collision_voxel"])+0.1
    for item in [s['corridor']]+s['route']+[c for b in s['branches'] for c in b['route']]+s['bottlenecks']:
        for dimension in ('width','height'):
            if dimension in item and item[dimension]<minimum_dimension:
                raise ValueError(f'{dimension} is incompatible with robot safety and voxel allowance; need >= {minimum_dimension:.3f} m or smaller collision_voxel')
    number(s["mesh"]["max_voxels"], "max_voxels", 1000, 100000000)
    number(s["geology"]["amplitude"], "amplitude", 0, 1.2)
    number(s["geology"]["strata"], "strata", 0, 0.6)
    number(s["geology"]["formations"], "formations", 0, 200)
    number(s["material"]["roughness"], "roughness", 0, 1)
    number(s['material'].get('detail_anisotropy',1),'detail_anisotropy',1,4)
    if 'palette' in s['material']:
        palette=s['material']['palette']
        if not isinstance(palette,list) or len(palette)!=3 or any(not isinstance(row,list) or len(row)!=3 for row in palette):
            raise ValueError('material.palette must be three RGB triplets')
        for row in palette:
            for channel in row: number(channel,'palette channel',0,1)
    for item,key in [(s['geology'],'formations'),(s['mesh'],'max_voxels')]+[(ch,'lobes') for ch in s['chambers'] if 'lobes' in ch]:
        if isinstance(item[key],bool) or int(item[key])!=item[key]: raise ValueError(f'{key} must be an integer')
    number(s['validation']['max_slope_degrees'],'max_slope_degrees',0,70)
    for b in s["branches"]:
        if set(b) - {"at", "heading", "route", "rejoin_at"}:
            raise ValueError("Unknown branch keys")
        number(b["at"], "branch.at", 0.05, 0.95)
        number(b.get("heading", 90), "branch.heading", -180, 180)
        check_commands(b["route"], "branch.route")
        if "rejoin_at" in b:
            number(b["rejoin_at"], "rejoin_at", 0.05, 0.95)
    for ch in s["chambers"]:
        if set(ch) - {"at", "radii", "lobes", "style"}:
            raise ValueError("Unknown chamber keys")
        number(ch["at"], "chamber.at", 0.05, 0.95)
        if len(ch["radii"]) != 3:
            raise ValueError("Chamber radii must be three metre values")
        for r in ch["radii"]:
            number(r, "chamber radius", 1, 25)
        number(ch.get("lobes", 5), "lobes", 2, 12)
    for b in s["bottlenecks"]:
        if set(b) - {"at", "length", "width", "height"}:
            raise ValueError("Unknown bottleneck keys")
        number(b["at"], "bottleneck.at", 0.05, 0.95)
        number(b["length"], "bottleneck.length", 1, 30)
        for d in ("width", "height"):
            number(b[d], f"bottleneck.{d}", safety * 2 + 0.2, 15)
    return s
