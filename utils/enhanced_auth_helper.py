# utils/enhanced_auth_helper.py
# Simplified version - see FyersORB project for full implementation

"""Enhanced Fyers Authentication Helper for Arbitrage Strategy"""

import hashlib
import requests
import logging
import os

logger = logging.getLogger(__name__)


class FyersAuthManager:
    """Fyers authentication manager with token refresh support"""

    def __init__(self):
        self.client_id = os.environ.get('FYERS_CLIENT_ID')
        self.secret_key = os.environ.get('FYERS_SECRET_KEY')
        self.access_token = os.environ.get('FYERS_ACCESS_TOKEN')
        self.refresh_token = os.environ.get('FYERS_REFRESH_TOKEN')
        self.pin = os.environ.get('FYERS_PIN')
        self.redirect_uri = os.environ.get('FYERS_REDIRECT_URI',
                                           "https://trade.fyers.in/api-login/redirect-to-app")

        # API endpoints
        self.auth_url = "https://api-t1.fyers.in/api/v3/generate-authcode"
        self.token_url = "https://api-t1.fyers.in/api/v3/validate-authcode"
        self.refresh_url = "https://api-t1.fyers.in/api/v3/validate-refresh-token"
        self.profile_url = "https://api-t1.fyers.in/api/v3/profile"

    def save_to_env(self, key: str, value: str) -> bool:
        """Save to .env file"""
        try:
            env_file = '.env'
            env_vars = {}

            if os.path.exists(env_file):
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and '=' in line and not line.startswith('#'):
                            k, v = line.split('=', 1)
                            env_vars[k] = v

            env_vars[key] = value

            with open(env_file, 'w') as f:
                for k, v in env_vars.items():
                    f.write(f"{k}={v}\n")

            os.environ[key] = value
            logger.debug(f"Saved {key} to .env")
            return True
        except Exception as e:
            logger.error(f"Error saving to .env: {e}")
            return False

    def get_app_id_hash(self) -> str:
        """Generate app_id_hash for API calls"""
        app_id = f"{self.client_id}:{self.secret_key}"
        return hashlib.sha256(app_id.encode()).hexdigest()

    def is_token_valid(self, access_token: str) -> bool:
        """Check if access token is valid"""
        if not access_token or not self.client_id:
            return False

        try:
            headers = {'Authorization': f"{self.client_id}:{access_token}"}
            response = requests.get(self.profile_url, headers=headers, timeout=10)

            if response.status_code == 200:
                result = response.json()
                return result.get('s') == 'ok'
            return False
        except Exception as e:
            logger.debug(f"Token validation error: {e}")
            return False

    def generate_auth_url(self) -> str:
        """Generate authorization URL"""
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'state': 'sample_state'
        }
        url = f"{self.auth_url}?" + "&".join([f"{k}={v}" for k, v in params.items()])
        return url

    def get_tokens_from_auth_code(self, auth_code: str):
        """Exchange auth code for tokens"""
        try:
            logger.info("Exchanging auth code for tokens...")

            data = {
                "grant_type": "authorization_code",
                "appIdHash": self.get_app_id_hash(),
                "code": auth_code
            }

            response = requests.post(self.token_url, json=data, timeout=30)
            result = response.json()

            if response.status_code == 200 and result.get('s') == 'ok':
                access_token = result.get('access_token')
                refresh_token = result.get('refresh_token')
                logger.info("Successfully obtained tokens")
                return access_token, refresh_token
            else:
                error_msg = result.get('message', 'Unknown error')
                logger.error(f"Token exchange failed: {error_msg}")
                return None, None

        except Exception as e:
            logger.error(f"Token exchange error: {e}")
            return None, None

    def generate_access_token_with_refresh(self, refresh_token: str, pin: str):
        """Generate new access token using refresh token"""
        try:
            logger.info("Refreshing access token...")

            data = {
                "grant_type": "refresh_token",
                "appIdHash": self.get_app_id_hash(),
                "refresh_token": refresh_token,
                "pin": pin
            }

            response = requests.post(self.refresh_url, json=data, timeout=30)
            result = response.json()

            if response.status_code == 200 and result.get('s') == 'ok':
                new_access_token = result.get('access_token')
                new_refresh_token = result.get('refresh_token')
                logger.info("Successfully refreshed token")
                return new_access_token, new_refresh_token
            else:
                error_msg = result.get('message', 'Unknown error')
                logger.error(f"Token refresh failed: {error_msg}")
                return None, None

        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return None, None

    def get_valid_access_token(self) -> str:
        """Get valid access token, refreshing if needed"""
        # Check if current token is valid
        if self.access_token and self.is_token_valid(self.access_token):
            logger.info("Current access token is valid")
            return self.access_token

        logger.info("Access token is invalid or expired")

        # Try refresh if available
        if self.refresh_token and self.pin:
            logger.info("Attempting to refresh token...")
            new_access_token, new_refresh_token = self.generate_access_token_with_refresh(
                self.refresh_token, self.pin
            )

            if new_access_token:
                self.save_to_env('FYERS_ACCESS_TOKEN', new_access_token)
                self.access_token = new_access_token

                if new_refresh_token:
                    self.save_to_env('FYERS_REFRESH_TOKEN', new_refresh_token)
                    self.refresh_token = new_refresh_token

                return new_access_token

        logger.info("Full re-authentication required")
        return None


# Convenience functions
def setup_auth_only():
    """Setup authentication"""
    print("=" * 60)
    print("FYERS API AUTHENTICATION SETUP")
    print("=" * 60)

    auth_manager = FyersAuthManager()

    # Get credentials if not exists
    if not auth_manager.client_id:
        print("\nEnter your Fyers API credentials:")
        client_id = input("Client ID: ").strip()
        secret_key = input("Secret Key: ").strip()

        auth_manager.save_to_env('FYERS_CLIENT_ID', client_id)
        auth_manager.save_to_env('FYERS_SECRET_KEY', secret_key)
        auth_manager.client_id = client_id
        auth_manager.secret_key = secret_key

    # Generate auth URL
    auth_url = auth_manager.generate_auth_url()
    print(f"\n AUTHENTICATION STEPS:")
    print(f"\n1. Open this URL in your browser:")
    print(f"   {auth_url}")
    print(f"\n2. Complete the authorization")
    print(f"3. Copy the authorization code from redirect URL")

    auth_code = input("\n Enter authorization code: ").strip()

    if not auth_code:
        print(" No authorization code provided")
        return False

    # Exchange for tokens
    access_token, refresh_token = auth_manager.get_tokens_from_auth_code(auth_code)

    if access_token:
        auth_manager.save_to_env('FYERS_ACCESS_TOKEN', access_token)
        if refresh_token:
            auth_manager.save_to_env('FYERS_REFRESH_TOKEN', refresh_token)

        # Get PIN for future refreshes
        try:
            pin = input("\n Enter trading PIN (for automatic refresh): ").strip()
            if pin and len(pin) >= 4:
                auth_manager.save_to_env('FYERS_PIN', pin)
                print(" PIN saved for automatic token refresh")
        except:
            print(" PIN setup skipped")

        print("\n AUTHENTICATION SUCCESSFUL!")
        return True
    else:
        print("\n Authentication failed")
        return False


def authenticate_fyers(config_dict: dict) -> bool:
    """Authenticate Fyers with auto-refresh"""
    try:
        auth_manager = FyersAuthManager()
        access_token = auth_manager.get_valid_access_token()

        if access_token:
            config_dict['fyers_config'].access_token = access_token
            logger.info("Fyers authentication successful")
            return True
        else:
            logger.error("Fyers authentication failed")
            return False

    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return False


def test_authentication():
    """Test authentication without running strategy"""
    print("\n" + "=" * 60)
    print("FYERS AUTHENTICATION TEST")
    print("=" * 60)

    auth_manager = FyersAuthManager()

    if not all([auth_manager.client_id, auth_manager.secret_key]):
        print(" Missing API credentials")
        print("Run: python main.py auth")
        return False

    print(" Testing authentication...")
    access_token = auth_manager.get_valid_access_token()

    if not access_token:
        print(" Authentication failed")
        return False

    print(" Authentication successful!")

    # Try to get profile
    try:
        headers = {'Authorization': f"{auth_manager.client_id}:{access_token}"}
        response = requests.get(auth_manager.profile_url, headers=headers, timeout=10)

        if response.status_code == 200:
            result = response.json()
            if result.get('s') == 'ok':
                profile = result.get('data', {})
                print(f" Name: {profile.get('name', 'Unknown')}")
                print(f" Email: {profile.get('email', 'Unknown')}")
    except:
        pass

    return True