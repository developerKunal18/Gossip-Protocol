# Gossip Protocol

A small Flask service demonstrating a gossip protocol for spreading node state through a distributed cluster.

## Features
- Register and remove cluster nodes
- Store versioned key/value state
- Gossip state between peers
- Merge newer state automatically
- Track gossip rounds and peer activity
- Thread-safe in-memory state
- Health endpoint
- Pytest tests

## Run
```bash
pip install -r requirements.txt
python app.py
```

## API
- `POST /api/nodes` — register a node
- `GET /api/nodes` — list nodes
- `DELETE /api/nodes/<node_id>` — remove a node
- `PUT /api/state` — set node state
- `GET /api/state/<node_id>` — read node state
- `POST /api/gossip/<peer>` — gossip from `source` to a peer
- `GET /api/cluster` — inspect cluster state
- `GET /health` — health check

Example:
```json
PUT /api/state
{
  "node_id": "node-1",
  "key": "status",
  "value": "online"
}
```

Then:
```json
POST /api/gossip/node-2
{
  "source": "node-1"
}
```

## Concepts
Gossip protocol, eventual consistency, state dissemination, versioned conflict resolution, peer-to-peer communication, distributed systems.
