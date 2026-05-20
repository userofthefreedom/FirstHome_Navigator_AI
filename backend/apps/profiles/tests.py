from django.test import Client, TestCase

from apps.profiles.models import Favorite, UserProfile


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

    def test_register_creates_authenticated_user_profile(self):
        response = self.client.post(
            "/api/auth/register",
            {"username": "firsthome", "password": "strongpass123", "email": "firsthome@example.com"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["user"]["is_authenticated"])
        self.assertEqual(response.json()["user"]["username"], "firsthome")
        self.assertEqual(UserProfile.objects.get(user__username="firsthome").birth_year, 1999)

    def test_authenticated_profile_is_saved_to_user_profile(self):
        self.client.post(
            "/api/auth/register",
            {"username": "owner", "password": "strongpass123"},
            content_type="application/json",
        )

        response = self.client.put(
            "/api/profile",
            {"name": "계정사용자", "birth_year": 1995, "annual_income": 42000000},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        profile = UserProfile.objects.get(user__username="owner")
        self.assertEqual(profile.name, "계정사용자")
        self.assertEqual(profile.birth_year, 1995)
        self.assertEqual(profile.annual_income, 42000000)

    def test_authenticated_favorites_are_user_scoped(self):
        self.client.post(
            "/api/auth/register",
            {"username": "alpha", "password": "strongpass123"},
            content_type="application/json",
        )
        self.client.post(
            "/api/favorites",
            {"favorite_type": "notice", "object_id": 101},
            content_type="application/json",
        )

        second_client = Client()
        second_client.post(
            "/api/auth/register",
            {"username": "beta", "password": "strongpass123"},
            content_type="application/json",
        )

        self.assertEqual(Favorite.objects.count(), 1)
        self.assertEqual(Favorite.objects.get().user.username, "alpha")
        self.assertEqual(second_client.get("/api/favorites").json(), [])

    def test_client_favorites_are_merged_on_login(self):
        self.client.post(
            "/api/favorites",
            {"favorite_type": "policy", "object_id": 301},
            content_type="application/json",
            HTTP_X_FIRSTHOME_CLIENT_ID=CLIENT_ID,
        )

        response = self.client.post(
            "/api/auth/register",
            {"username": "merge-user", "password": "strongpass123"},
            content_type="application/json",
            HTTP_X_FIRSTHOME_CLIENT_ID=CLIENT_ID,
        )

        self.assertEqual(response.status_code, 201)
        self.assertFalse(Favorite.objects.filter(user__isnull=True, client_id=CLIENT_ID).exists())
        self.assertTrue(Favorite.objects.filter(user__username="merge-user", favorite_type="policy", object_id=301).exists())
