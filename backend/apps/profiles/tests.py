from django.test import SimpleTestCase


class FavoriteApiTests(SimpleTestCase):
    def test_favorite_can_be_added_listed_and_removed(self):
        response = self.client.post(
            "/api/favorites",
            {"favorite_type": "notice", "object_id": 101},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

        response = self.client.get("/api/favorites")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["favorite_type"], "notice")
        self.assertEqual(response.json()[0]["object_id"], 101)
        self.assertEqual(response.json()[0]["item"]["title"], "서울 강동 뉴홈 청년특별공급")

        response = self.client.delete(
            "/api/favorites",
            {"favorite_type": "notice", "object_id": 101},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 204)

        response = self.client.get("/api/favorites")
        self.assertEqual(response.json(), [])

    def test_product_and_policy_favorites_include_item_payload(self):
        self.client.post(
            "/api/favorites",
            {"favorite_type": "product", "object_id": 201},
            content_type="application/json",
        )
        self.client.post(
            "/api/favorites",
            {"favorite_type": "policy", "object_id": 301},
            content_type="application/json",
        )

        response = self.client.get("/api/favorites")
        favorites = response.json()

        self.assertEqual(favorites[0]["item"]["name"], "청년 첫집 준비 적금")
        self.assertEqual(favorites[1]["item"]["name"], "청년월세 한시 특별지원")
