class TestAuthAPI:
    async def test_register_and_login(self, client):
        credentials = {
            "username": "walker",
            "password": "Walk-by-the-river-27!",
        }
        response = await client.post("/api/auth/register/", json=credentials)
        assert response.status_code == 201
        assert response.json()["username"] == "walker"
        assert "password" not in response.json()

        response = await client.post("/api/auth/register/", json=credentials)
        assert response.status_code == 400

        wrong_credentials = {**credentials, "password": "wrong-password"}
        response = await client.post("/api/auth/login/", json=wrong_credentials)
        assert response.status_code == 400

        response = await client.post("/api/auth/login/", json=credentials)
        assert response.status_code == 200
        token = response.json()["access_token"]

        response = await client.get("/api/tasks/")
        assert response.status_code == 401

        headers = {"Authorization": "Bearer not-a-token"}
        response = await client.get("/api/tasks/", headers=headers)
        assert response.status_code == 401

        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("/api/tasks/", headers=headers)
        assert response.status_code == 200
