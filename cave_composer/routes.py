"""Exact circular plan-view arcs, grade profiles, and semantic navigation graph."""
import numpy as np


def build_route(commands, corridor, origin=(0, 0, 0), heading=0, step=0.30):
    pos = np.array(origin, dtype=float)
    yaw = float(heading)
    points = [pos.copy()]
    widths, heights, sections = [], [], []
    events = []
    width, height = corridor["width"], corridor["height"]
    for ci, c in enumerate(commands):
        if 'curve' in c:
            # Cubic Bezier controls use the current forward/left/world-up frame.
            # Arc-length resampling gives the same maximum polyline step contract
            # as the legacy straight/circular commands, without corner seams.
            controls = np.vstack([np.zeros(3), np.asarray(c['curve'], dtype=float)])
            polygon_length = np.linalg.norm(np.diff(controls, axis=0), axis=1).sum()
            dense_count = max(64, int(np.ceil(polygon_length / step)) * 12)
            t = np.linspace(0, 1, dense_count + 1)[:, None]
            dense = (1-t)**3*controls[0] + 3*(1-t)**2*t*controls[1] + 3*(1-t)*t**2*controls[2] + t**3*controls[3]
            arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(dense, axis=0), axis=1))]
            if arc[-1] < .01 or np.any(np.diff(arc) < 1e-10):
                raise ValueError('Degenerate cubic route')
            samples = np.linspace(0, arc[-1], max(2, int(np.ceil(arc[-1] / step))) + 1)
            local = np.column_stack([np.interp(samples, arc, dense[:, k]) for k in range(3)])
            rotation = np.array([[np.cos(yaw), -np.sin(yaw), 0], [np.sin(yaw), np.cos(yaw), 0], [0, 0, 1]])
            world = local @ rotation.T + pos
            start_index = len(points) - 1
            points.extend(world[1:])
            width_end, height_end = c.get('width', width), c.get('height', height)
            f = samples[1:] / samples[-1]
            smooth = f*f*(3-2*f)
            widths.extend(width*(1-smooth) + width_end*smooth)
            heights.extend(height*(1-smooth) + height_end*smooth)
            sections.extend([c.get('section', corridor['section'])] * len(f))
            end_tangent = controls[3] - controls[2]
            yaw_change = np.arctan2(end_tangent[1], end_tangent[0])
            events.append({'command': ci, 'start_index': start_index, 'end_index': len(points)-1,
                           'type': 'curve', 'angle_degrees': float(np.rad2deg(yaw_change)), 'radius': None,
                           'slope_degrees': float(np.rad2deg(np.arctan2(world[-1, 2]-world[0, 2], np.linalg.norm(world[-1, :2]-world[0, :2])))),
                           'length': float(arc[-1]), 'length_method': 'dense cubic arc-length approximation'})
            pos = world[-1].copy()
            yaw += yaw_change
            width, height = width_end, height_end
            continue
        slope = np.deg2rad(c.get("slope", 0))
        angle = np.deg2rad(c.get("turn", 0))
        radius = c.get("radius", 4)
        planar = c["straight"] * np.cos(slope) if "straight" in c else radius * abs(angle)
        length = c["straight"] if "straight" in c else planar / np.cos(slope)
        n = max(2, int(np.ceil(length / step)))
        start_index = len(points) - 1
        width_end, height_end = c.get("width", width), c.get("height", height)
        for j in range(1, n + 1):
            t = j / n
            if "straight" in c:
                xy = np.array([np.cos(yaw), np.sin(yaw)]) * planar * t
            else:
                direction = np.sign(angle)
                a = yaw + angle * t
                xy = direction * radius * np.array([np.sin(a) - np.sin(yaw), -np.cos(a) + np.cos(yaw)])
            q = pos + np.r_[xy, planar * t * np.tan(slope)]
            points.append(q)
            smooth = t * t * (3 - 2 * t)
            widths.append(width * (1-smooth) + width_end * smooth)
            heights.append(height * (1-smooth) + height_end * smooth)
            sections.append(c.get("section", corridor["section"]))
        events.append({"command": ci, "start_index": start_index, "end_index": len(points)-1,
                       "type": "turn" if angle else ("vertical_transition" if slope else "corridor"),
                       "angle_degrees": float(c.get("turn", 0)), "radius": radius if angle else None,
                       "slope_degrees": float(c.get("slope", 0)), "length": float(length)})
        pos = points[-1].copy()
        yaw += angle
        width, height = width_end, height_end
    return {"points": np.asarray(points), "widths": np.r_[corridor["width"], widths],
            "heights": np.r_[corridor["height"], heights], "sections": [sections[0]]+sections, "events": events}


def build_routes(spec):
    main = build_route(spec["route"], spec["corridor"])
    main["id"] = "main"
    main["join_start"] = main["join_end"] = None
    routes = [main]
    for i, branch in enumerate(spec["branches"]):
        idx = int(round(branch["at"] * (len(main["points"])-1)))
        tangent = main["points"][idx+1] - main["points"][idx-1]
        yaw = np.arctan2(tangent[1], tangent[0]) + np.deg2rad(branch.get("heading", 90))
        route = build_route(branch["route"], spec["corridor"], main["points"][idx], yaw)
        route["id"] = f"branch_{i}"
        route["join_start"] = idx
        route["join_end"] = None
        if "rejoin_at" in branch:
            target = int(round(branch["rejoin_at"] * (len(main["points"])-1)))
            q = main["points"][target]
            last = route["points"][-1]
            distance = float(np.linalg.norm(q-last))
            if distance > 1e-8:
                n = max(2, int(np.ceil(distance/0.3)))
                route["points"] = np.vstack([route["points"], np.linspace(last, q, n+1)[1:]])
                for k in ("widths", "heights"):
                    route[k] = np.r_[route[k], np.full(n, route[k][-1])]
                route["sections"] += [route["sections"][-1]]*n
            else:
                route['points'][-1] = q
            route["join_end"] = target
        routes.append(route)
    for route in routes:
        p = route["points"]
        route["s"] = np.r_[0, np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))]
        if route["id"] == "main":
            for b in spec["bottlenecks"]:
                weight = np.exp(-((route["s"]-b["at"]*route["s"][-1]) / (b["length"]/2))**4)
                for key, dim in (("widths", "width"), ("heights", "height")):
                    route[key] = route[key]*(1-weight) + b[dim]*weight
    return routes


def navigation_graph(routes, chambers, bottlenecks=()):
    nodes, edges = [], []
    main_ids = []
    for ri, r in enumerate(routes):
        ids = []
        for i, p in enumerate(r["points"]):
            if ri and i == 0:
                ids.append(main_ids[r["join_start"]]); continue
            if ri and i == len(r["points"])-1 and r["join_end"] is not None:
                ids.append(main_ids[r["join_end"]]); continue
            nid = len(nodes)
            ids.append(nid)
            semantic = "corridor"
            for e in r["events"]:
                if e["start_index"] <= i <= e["end_index"] and e["type"] != "corridor":
                    semantic = e["type"]
            if ri == 0:
                for ch in chambers:
                    if abs(i/(len(r["points"])-1) - ch["at"]) < 0.035: semantic = "chamber"
                for b in bottlenecks:
                    if abs(r["s"][i]-b["at"]*r["s"][-1]) < b["length"]/2: semantic = "bottleneck"
            nodes.append({"id": nid, "position": p.tolist(), "local_width": float(r["widths"][i]),
                          "local_height": float(r["heights"][i]), "semantic_type": semantic, "route": r["id"]})
        for a, b in zip(ids[:-1], ids[1:]):
            edges.append({"source": a, "target": b, "length": float(np.linalg.norm(np.array(nodes[a]["position"])-nodes[b]["position"]))})
        if ri == 0: main_ids = ids
    degree = np.zeros(len(nodes), dtype=int)
    for e in edges: degree[e["source"]] += 1; degree[e["target"]] += 1
    for n, deg in zip(nodes, degree):
        n["degree"] = int(deg)
        if deg > 2: n["semantic_type"] = "junction"
        elif deg == 1: n["semantic_type"] = "dead_end"
    nodes[0]["semantic_type"] = "start_cap"
    nodes[main_ids[-1]]["semantic_type"] = "goal_cap"
    return {"coordinate_system": "right-handed, metres, Z-up", "nodes": nodes, "edges": edges,
            "junctions": [n["id"] for n in nodes if n["degree"] > 2],
            "cycle_rank": len(edges)-len(nodes)+1,
            "semantic_events": [{"route": r["id"], **e} for r in routes for e in r["events"]], "chambers": chambers}


def junction_graph(graph):
    """Contract degree-two chains while retaining edge geometry and metric length."""
    adjacency={n['id']:[] for n in graph['nodes']}
    for e in graph['edges']:
        adjacency[e['source']].append((e['target'],e['length']))
        adjacency[e['target']].append((e['source'],e['length']))
    critical={n['id'] for n in graph['nodes'] if n['degree']!=2}
    for chamber in graph['chambers']:
        nearest=min(graph['nodes'],key=lambda n:np.linalg.norm(np.asarray(n['position'])-chamber['position']))
        critical.add(nearest['id'])
    visited=set(); edges=[]
    for start in sorted(critical):
        for nxt,length in adjacency[start]:
            if tuple(sorted((start,nxt))) in visited: continue
            chain=[start,nxt]; total=length; visited.add(tuple(sorted((start,nxt))))
            previous,current=start,nxt
            while current not in critical:
                next_node,dist=next((a,b) for a,b in adjacency[current] if a!=previous)
                visited.add(tuple(sorted((current,next_node)))); chain.append(next_node); total+=dist
                previous,current=current,next_node
            edges.append({'source':start,'target':current,'length':float(total),'sample_node_ids':chain})
    return {'nodes':[graph['nodes'][i] for i in sorted(critical)],'edges':edges,'cycle_rank':graph['cycle_rank'],'chambers':graph['chambers']}
