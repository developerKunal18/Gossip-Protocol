import pytest
import app as module


@pytest.fixture(autouse=True)
def reset_cluster():
    module.cluster = module.GossipCluster()
    yield


@pytest.fixture
def client():
    module.app.config["TESTING"] = True
    return module.app.test_client()


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_add_node(client):
    assert client.post("/api/nodes", json={"node_id": "node-4"}).status_code == 201
    assert client.post("/api/nodes", json={"node_id": "node-4"}).status_code == 409


def test_gossip_merges_state(client):
    client.put("/api/state", json={
        "node_id": "node-1", "key": "status", "value": "online"
    })
    response = client.post("/api/gossip/node-2", json={"source": "node-1"})
    assert response.status_code == 200
    state = client.get("/api/state/node-2").get_json()["state"]
    assert state["status"]["value"] == "online"


def test_newer_state_wins(client):
    client.put("/api/state", json={
        "node_id": "node-1", "key": "mode", "value": "old"
    })
    client.put("/api/state", json={
        "node_id": "node-2", "key": "mode", "value": "new"
    })
    client.post("/api/gossip/node-2", json={"source": "node-1"})
    state = client.get("/api/state/node-1").get_json()["state"]
    assert state["mode"]["value"] == "new"


def test_gossip_requires_source(client):
    assert client.post("/api/gossip/node-2", json={}).status_code == 400
