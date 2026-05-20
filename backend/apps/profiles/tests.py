from django.test import Client, TestCase


CLIENT_ID = "test-client"


class FavoriteApiTests(TestCase):
    def test_favorite_can_be_added_listed_and_removed(self):
        response = self.client.post(
            "/api/favorites",
            {"favorite_type": "notice", "object_id": 101},
            content_type="application/json",
            HTTP_X_FIRSTHOME_CLIENT_ID=CLIENT_ID,
        )
        self.assertEqual(response.status_code, 201)

        response = self.client.get("/api/favorites", HTTP_X_FIRSTHOME_CLIENT_ID=CLIENT_ID)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["favorite_type"], "notice")
        self.assertEqual(response.json()[0]["object_id"], 101)
        self.assertTrue(response.json()[0]["item"]["title"])

        response = self.client.delete(
            "/api/favorites",
            {"favorite_type": "notice", "object_id": 101},
            content_type="application/json",
            HTTP_X_FIRSTHOME_CLIENT_ID=CLIENT_ID,
        )
        self.assertEqual(response.status_code, 204)

        response = self.client.get("/api/favorites", HTTP_X_FIRSTHOME_CLIENT_ID=CLIENT_ID)
        self.assertEqual(response.json(), [])

    def test_product_and_policy_favorites_include_item_payload(self):
        self.client.post(
            "/api/favorites",
            {"favorite_type": "product", "object_id": 201},
            content_type="application/json",
            HTTP_X_FIRSTHOME_CLIENT_ID=CLIENT_ID,
        )
        self.client.post(
            "/api/favorites",
            {"favorite_type": "policy", "object_id": 301},
            content_type="application/json",
            HTTP_X_FIRSTHOME_CLIENT_ID=CLIENT_ID,
        )

        response = self.client.get("/api/favorites", HTTP_X_FIRSTHOME_CLIENT_ID=CLIENT_ID)
        favorites = response.json()

        self.assertEqual({favorite["favorite_type"] for favorite in favorites}, {"product", "policy"})
        self.assertTrue(all(favorite["item"]["name"] for favorite in favorites))

    def test_favorites_persist_across_clients_with_same_client_id(self):
        self.client.post(
            "/api/favorites",
            {"favorite_type": "policy", "object_id": 301},
            content_type="application/json",
            HTTP_X_FIRSTHOME_CLIENT_ID=CLIENT_ID,
        )

        fresh_client = Client()
        response = fresh_client.get("/api/favorites", HTTP_X_FIRSTHOME_CLIENT_ID=CLIENT_ID)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["favorite_type"], "policy")

    def test_different_client_id_has_separate_favorites(self):
        self.client.post(
            "/api/favorites",
            {"favorite_type": "policy", "object_id": 301},
            content_type="application/json",
            HTTP_X_FIRSTHOME_CLIENT_ID=CLIENT_ID,
        )

        response = self.client.get("/api/favorites", HTTP_X_FIRSTHOME_CLIENT_ID="other-client")

        self.assertEqual(response.json(), [])
