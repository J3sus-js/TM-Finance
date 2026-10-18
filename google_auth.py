import base64
import hashlib
import hmac
import json
import secrets
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"
STATE_MAX_AGE_SECONDS = 600


class GoogleAuthError(RuntimeError):
    pass


def _validate_configuration(client_id, client_secret, redirect_uri):
    if not client_id or not client_secret or not redirect_uri:
        raise GoogleAuthError(
            "Configura GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET y GOOGLE_REDIRECT_URI."
        )
    parsed_uri = urlsplit(redirect_uri)
    is_local = parsed_uri.hostname in {"localhost", "127.0.0.1", "::1"}
    if not parsed_uri.netloc or (parsed_uri.scheme != "https" and not (is_local and parsed_uri.scheme == "http")):
        raise GoogleAuthError("La URL de retorno de Google debe usar HTTPS.")


def _signed_state(client_secret, timestamp, nonce):
    message = f"{timestamp}.{nonce}"
    signature = hmac.new(
        client_secret.encode(), message.encode(), hashlib.sha256
    ).hexdigest()
    return f"{message}.{signature}"


def _code_challenge(verifier):
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def authorization_request(client_id, client_secret, redirect_uri, now=None):
    _validate_configuration(client_id, client_secret, redirect_uri)
    timestamp = int(time.time() if now is None else now)
    nonce = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    state = _signed_state(client_secret, timestamp, nonce)
    parameters = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "code_challenge": _code_challenge(verifier),
        "code_challenge_method": "S256",
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{AUTHORIZATION_ENDPOINT}?{urlencode(parameters)}", state, verifier


def consume_authorization_request(transaction_store, state):
    transaction = transaction_store.get("google_oauth_transaction")
    if not isinstance(transaction, dict):
        raise GoogleAuthError("El inicio con Google expiró o no es válido. Inténtalo de nuevo.")

    expected_state = transaction.get("state")
    verifier = transaction.get("code_verifier")
    if (
        not isinstance(state, str)
        or not isinstance(expected_state, str)
        or not hmac.compare_digest(state, expected_state)
        or not isinstance(verifier, str)
    ):
        raise GoogleAuthError("La verificación de Google no es válida. Inténtalo de nuevo.")

    transaction_store.pop("google_oauth_transaction")
    return verifier


def _verified_state(client_secret, state, now=None):
    try:
        timestamp_text, nonce, signature = state.split(".", 2)
        timestamp = int(timestamp_text)
    except (AttributeError, TypeError, ValueError) as error:
        raise GoogleAuthError("El inicio con Google expiró o no es válido. Inténtalo de nuevo.") from error

    current_time = int(time.time() if now is None else now)
    if current_time - timestamp < 0 or current_time - timestamp > STATE_MAX_AGE_SECONDS:
        raise GoogleAuthError("El inicio con Google expiró. Inténtalo de nuevo.")
    expected = _signed_state(client_secret, timestamp, nonce).rsplit(".", 1)[1]
    if not hmac.compare_digest(signature, expected):
        raise GoogleAuthError("La verificación de Google no es válida. Inténtalo de nuevo.")


def _post_form(url, values):
    request = Request(
        url,
        data=urlencode(values).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    return _read_json(request)


def _read_json(request):
    try:
        with urlopen(request, timeout=15) as response:
            result = json.loads(response.read())
    except HTTPError as error:
        raise GoogleAuthError("Google rechazó la solicitud de inicio de sesión.") from error
    except (URLError, TimeoutError, OSError) as error:
        raise GoogleAuthError("No se pudo conectar con Google. Inténtalo de nuevo.") from error
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise GoogleAuthError("Google devolvió una respuesta no válida.") from error
    if not isinstance(result, dict):
        raise GoogleAuthError("Google devolvió una respuesta no válida.")
    return result


def user_profile(code, state, code_verifier, client_id, client_secret, redirect_uri):
    _validate_configuration(client_id, client_secret, redirect_uri)
    _verified_state(client_secret, state)
    if (
        not isinstance(code_verifier, str)
        or not 43 <= len(code_verifier) <= 128
        or any(
            character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~"
            for character in code_verifier
        )
    ):
        raise GoogleAuthError("La solicitud de inicio con Google no es válida. Inténtalo de nuevo.")
    token_data = _post_form(TOKEN_ENDPOINT, {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "code_verifier": code_verifier,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    })
    access_token = token_data.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise GoogleAuthError("Google no completó la autorización. Inténtalo de nuevo.")

    request = Request(
        USERINFO_ENDPOINT,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    profile = _read_json(request)
    email = profile.get("email")
    name = profile.get("name")
    if (
        profile.get("email_verified") is not True
        or not isinstance(email, str)
        or not email.strip()
        or not isinstance(name, str)
        or not name.strip()
        or not isinstance(profile.get("sub"), str)
        or not profile["sub"]
    ):
        raise GoogleAuthError("La cuenta de Google no proporcionó un perfil verificado.")
    return {"email": email.strip().lower(), "name": name.strip()}
