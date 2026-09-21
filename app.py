from copy import deepcopy
from threading import RLock
from typing import Any
from flask import Flask, jsonify, request

app = Flask(__name__)
LOCK = RLock()
DEFAULT_NODES = ("node-1", "node-2", "node-3")


class GossipCluster:
    def __init__(self):
        self.nodes = {}
        self.rounds = 0
        self.gossip_counts = {}
        for node in DEFAULT_NODES:
            self.add_node(node)

    def add_node(self, node_id):
        if not node_id or len(node_id) > 64:
            raise ValueError("node_id must contain 1-64 characters")
        if node_id not in self.nodes:
            self.nodes[node_id] = {}
            self.gossip_counts[node_id] = 0

    def remove_node(self, node_id):
        if node_id in self.nodes:
            del self.nodes[node_id]
            self.gossip_counts.pop(node_id, None)
            return True
        return False

    def set_state(self, node_id, key, value):
        if node_id not in self.nodes:
            raise KeyError("node not found")
        if not key or len(key) > 128:
            raise ValueError("key must contain 1-128 characters")
        old = self.nodes[node_id].get(key)
        version = old["version"] + 1 if old else 1
        record = {"value": value, "version": version, "origin": node_id}
        self.nodes[node_id][key] = record
        return deepcopy(record)

    @staticmethod
    def merge(target, incoming):
        changed = 0
        for key, record in incoming.items():
            current = target.get(key)
            if current is None or (record["version"], record["origin"]) > (
                current["version"], current["origin"]
            ):
                target[key] = deepcopy(record)
                changed += 1
        return changed

    def gossip(self, source, peer):
        if source not in self.nodes or peer not in self.nodes:
            raise KeyError("node not found")
        if source == peer:
            raise ValueError("source and peer must be different")

        source_state = deepcopy(self.nodes[source])
        peer_state = deepcopy(self.nodes[peer])

        source_changes = self.merge(self.nodes[source], peer_state)
        peer_changes = self.merge(self.nodes[peer], source_state)

        source_changes += self.merge(self.nodes[source], self.nodes[peer])
        peer_changes += self.merge(self.nodes[peer], self.nodes[source])

        self.rounds += 1
        self.gossip_counts[source] += 1
        self.gossip_counts[peer] += 1
        return {
            "round": self.rounds,
            "source_changes": source_changes,
            "peer_changes": peer_changes,
        }

    def snapshot(self):
        return {
            "nodes": {n: deepcopy(s) for n, s in self.nodes.items()},
            "rounds": self.rounds,
            "gossip_counts": dict(self.gossip_counts),
        }


cluster = GossipCluster()


@app.get("/health")
def health():
    return jsonify({"status": "ok", "nodes": len(cluster.nodes)})


@app.get("/api/nodes")
def list_nodes():
    with LOCK:
        return jsonify({"nodes": sorted(cluster.nodes)})


@app.post("/api/nodes")
def add_node():
    body = request.get_json(silent=True) or {}
    node_id = str(body.get("node_id", "")).strip()
    try:
        with LOCK:
            if node_id in cluster.nodes:
                return jsonify({"error": "node already exists"}), 409
            cluster.add_node(node_id)
        return jsonify({"node_id": node_id, "created": True}), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.delete("/api/nodes/<node_id>")
def remove_node(node_id):
    with LOCK:
        if not cluster.remove_node(node_id):
            return jsonify({"error": "node not found"}), 404
    return jsonify({"node_id": node_id, "removed": True})


@app.put("/api/state")
def set_state():
    body = request.get_json(silent=True) or {}
    node_id = str(body.get("node_id", "")).strip()
    key = str(body.get("key", "")).strip()
    if "value" not in body:
        return jsonify({"error": "value is required"}), 400
    try:
        with LOCK:
            record = cluster.set_state(node_id, key, body["value"])
        return jsonify({"node_id": node_id, "key": key, **record}), 201
    except KeyError:
        return jsonify({"error": "node not found"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.get("/api/state/<node_id>")
def get_state(node_id):
    with LOCK:
        if node_id not in cluster.nodes:
            return jsonify({"error": "node not found"}), 404
        return jsonify({"node_id": node_id, "state": deepcopy(cluster.nodes[node_id])})


@app.post("/api/gossip/<peer>")
def gossip(peer):
    body = request.get_json(silent=True) or {}
    source = str(body.get("source", "")).strip()
    if not source:
        return jsonify({"error": "source is required"}), 400
    try:
        with LOCK:
            result = cluster.gossip(source, peer)
        return jsonify({"source": source, "peer": peer, **result})
    except KeyError:
        return jsonify({"error": "node not found"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.get("/api/cluster")
def cluster_view():
    with LOCK:
        return jsonify(cluster.snapshot())


if __name__ == "__main__":
    app.run(debug=True)
