def test_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "name": "EnergyPulse API",
        "version": "0.1.0"
    }

def test_list_topics_empty(client):
    response = client.get("/api/topics")
    assert response.status_code == 200
    assert response.json() == []

def test_create_and_list_topic(client):
    new_topic = {
        "name": "OPEC Production",
        "query": "OPEC oil supply",
        "keywords": ["OPEC", "supply", "cut"],
        "rss_feeds": ["https://oilprice.com/rss/main"],
        "is_active": True
    }
    response = client.post("/api/topics", json=new_topic)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "OPEC Production"
    assert "OPEC" in data["keywords"]
    
    # List topics should now return 1 topic
    response = client.get("/api/topics")
    assert response.status_code == 200
    assert len(response.json()) == 1

def test_list_articles_empty(client):
    response = client.get("/api/articles")
    assert response.status_code == 200
    data = response.json()
    assert data["articles"] == []
    assert data["total"] == 0
