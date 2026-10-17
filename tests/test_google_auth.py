import json
import unittest
from io import BytesIO
from time import time
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import google_auth


CLIENT_ID = "client-id"
CLIENT_SECRET = "client-secret"
REDIRECT_URI = "https://finance.example.com/"


class GoogleAuthTests(unittest.TestCase):
    def test_authorization_url_uses_signed_state_and_pkce(self):
        url = google_auth.authorization_url(
            CLIENT_ID, CLIENT_SECRET, REDIRECT_URI
        )
        query = parse_qs(urlsplit(url).query)
        state = query["state"][0]

        self.assertEqual(urlsplit(url).scheme, "https")
        self.assertEqual(query["redirect_uri"], [REDIRECT_URI])
        self.assertEqual(query["code_challenge_method"], ["S256"])
        self.assertEqual(query["scope"], ["openid email profile"])
        self.assertEqual(len(state.split(".")), 3)

    def test_user_profile_exchanges_code_and_requires_verified_email(self):
        state = parse_qs(urlsplit(google_auth.authorization_url(
            CLIENT_ID, CLIENT_SECRET, REDIRECT_URI
        )).query)["state"][0]
        token = BytesIO(json.dumps({"access_token": "test-access-token"}).encode())
        profile = BytesIO(json.dumps({
            "sub": "google-user-id",
            "email": "person@example.com",
            "email_verified": True,
            "name": "Person Example",
        }).encode())

        with patch("google_auth.urlopen", side_effect=[token, profile]) as open_url:
            result = google_auth.user_profile(
                "authorization-code", state,
                CLIENT_ID, CLIENT_SECRET, REDIRECT_URI,
            )

        self.assertEqual(result, {
            "email": "person@example.com",
            "name": "Person Example",
        })
        token_request = open_url.call_args_list[0].args[0]
        token_body = parse_qs(token_request.data.decode())
        self.assertEqual(token_body["code"], ["authorization-code"])
        self.assertTrue(token_body["code_verifier"][0])
        self.assertEqual(
            open_url.call_args_list[1].args[0].get_header("Authorization"),
            "Bearer test-access-token",
        )

    def test_invalid_or_expired_state_is_rejected_without_network_request(self):
        state = parse_qs(urlsplit(google_auth.authorization_url(
            CLIENT_ID, CLIENT_SECRET, REDIRECT_URI
        )).query)["state"][0]
        expired_state = state.replace(state.split(".", 1)[0], str(int(time()) - 601), 1)

        with patch("google_auth.urlopen") as open_url:
            with self.assertRaises(google_auth.GoogleAuthError):
                google_auth.user_profile(
                    "authorization-code", expired_state,
                    CLIENT_ID, CLIENT_SECRET, REDIRECT_URI,
                )

        open_url.assert_not_called()

    def test_unverified_google_email_is_rejected(self):
        state = parse_qs(urlsplit(google_auth.authorization_url(
            CLIENT_ID, CLIENT_SECRET, REDIRECT_URI
        )).query)["state"][0]
        token = BytesIO(json.dumps({"access_token": "test-access-token"}).encode())
        profile = BytesIO(json.dumps({
            "sub": "google-user-id",
            "email": "person@example.com",
            "email_verified": False,
            "name": "Person Example",
        }).encode())

        with patch("google_auth.urlopen", side_effect=[token, profile]):
            with self.assertRaises(google_auth.GoogleAuthError):
                google_auth.user_profile(
                    "authorization-code", state,
                    CLIENT_ID, CLIENT_SECRET, REDIRECT_URI,
                )


if __name__ == "__main__":
    unittest.main()
