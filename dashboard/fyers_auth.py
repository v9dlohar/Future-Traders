# ========== FYERS AUTHENTICATION FOR THIRD PARTY USERS ==========
from fyers_apiv3 import fyersModel
import os
import json
from pathlib import Path
from django.conf import settings

# Load .env file
from dotenv import load_dotenv
env_path = Path(__file__).resolve().parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path, override=True)

client_id = os.getenv('FYERS_CLIENT_ID')
secret_key = os.getenv('FYERS_SECRET_KEY')
redirect_uri = os.getenv('FYERS_REDIRECT_URI')
app_id_hash = os.getenv('FYERS_APP_ID_HASH', '')

# Only validate if not in collectstatic mode
if not os.getenv('DJANGO_SETTINGS_MODULE') or 'collectstatic' not in ' '.join(os.sys.argv if hasattr(os, 'sys') else []):
    if not client_id or not secret_key or not redirect_uri:
        print(f'Warning: FYERS environment variables not set. Fyers functionality will be disabled.')

TOKEN_FILE = str(Path(__file__).resolve().parent.parent / 'fyers_tokens.json')

# Check credentials before using functions
def _check_credentials():
    if not client_id or not secret_key or not redirect_uri:
        raise ValueError('FYERS credentials not configured. Set environment variables: FYERS_CLIENT_ID, FYERS_SECRET_KEY, FYERS_REDIRECT_URI')

def save_tokens(access_token, refresh_token):
    with open(TOKEN_FILE, 'w') as f:
        json.dump({'access_token': access_token, 'refresh_token': refresh_token}, f)

def load_tokens():
    try:
        with open(TOKEN_FILE, 'r') as f:
            return json.load(f)
    except:
        return None

def refresh_access_token(refresh_token):
    _check_credentials()
    try:
        import requests
        
        app_id_hash = os.getenv('FYERS_APP_ID_HASH')
        pin = os.getenv('FYERS_PIN')
        
        if not app_id_hash or not pin:
            print("Missing FYERS_APP_ID_HASH or FYERS_PIN environment variables")
            return None
        
        url = "https://api-t1.fyers.in/api/v3/validate-refresh-token"
        headers = {"Content-Type": "application/json"}
        
        data = {
            "grant_type": "refresh_token",
            "appIdHash": app_id_hash,
            "refresh_token": refresh_token,
            "pin": pin
        }
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('code') == 200:
                new_access_token = result.get('access_token')
                if new_access_token:
                    # Keep existing refresh token, only update access token
                    save_tokens(new_access_token, refresh_token)
                    return new_access_token
        
        print(f"Token refresh failed: {response.status_code}, {response.json()}")
        return None
    except Exception as e:
        print(f"Error refreshing token: {e}")
        return None

def is_token_valid(access_token):
    """Test if access token is valid by making a simple API call"""
    try:
        fyers = fyersModel.FyersModel(client_id=client_id, is_async=False, token=access_token, log_path="")
        response = fyers.get_profile()
        print(f"Token validation response: {response}")
        is_valid = response and response.get('code') == 200
        print(f"Token is valid: {is_valid}")
        return is_valid
    except Exception as e:
        print(f"Token validation error: {e}")
        return False

def get_valid_access_token():
    _check_credentials()
    token_data = load_tokens()
    if not token_data or 'access_token' not in token_data:
        print("No token data found")
        return None
    
    # Test if current access token is valid by making API call
    access_token = token_data['access_token']
    print(f"Testing access token validity...")
    if is_token_valid(access_token):
        print("Access token is valid")
        return access_token
    
    # Token is expired, try to refresh
    print("Access token is invalid, attempting refresh...")
    if 'refresh_token' in token_data:
        print("Refresh token found, attempting to refresh access token")
        new_token = refresh_access_token(token_data['refresh_token'])
        if new_token:
            print("Successfully refreshed access token")
            return new_token
        else:
            print("Failed to refresh access token")
    else:
        print("No refresh token found")
    
    return None

def login_fyers():
    _check_credentials()
    access_token = get_valid_access_token()
    if not access_token:
        return None
    
    fyers = fyersModel.FyersModel(client_id=client_id, is_async=False, token=access_token, log_path="")
    return fyers

def generate_auth_url():
    _check_credentials()
    session = fyersModel.SessionModel(
        client_id=client_id,
        secret_key=secret_key,
        redirect_uri=redirect_uri,
        response_type="code",
        grant_type="authorization_code"
    )
    if app_id_hash:
        return session.generate_authcode() + f"&appIdHash={app_id_hash}"
    return session.generate_authcode()

def generate_tokens_from_auth_code(auth_code):
    _check_credentials()
    session = fyersModel.SessionModel(
        client_id=client_id,
        secret_key=secret_key,
        redirect_uri=redirect_uri,
        response_type="code",
        grant_type="authorization_code"
    )
    session.set_token(auth_code)
    response = session.generate_token()
    
    if response and response.get('code') == 200:
        save_tokens(response['access_token'], response.get('refresh_token'))
        return {'access_token': response['access_token'], 'refresh_token': response.get('refresh_token')}
    return None
