# ========== FYERS AUTHENTICATION FOR THIRD PARTY USERS ==========
from fyers_apiv3 import fyersModel
import os
import json
from pathlib import Path

# Load .env file
from dotenv import load_dotenv
env_path = Path(__file__).resolve().parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path, override=True)
else:
    # On Railway, environment variables are set directly
    print("No .env file found, using system environment variables")

client_id = os.getenv('FYERS_CLIENT_ID')
secret_key = os.getenv('FYERS_SECRET_KEY')
redirect_uri = os.getenv('FYERS_REDIRECT_URI')
app_id_hash = os.getenv('FYERS_APP_ID_HASH', '')

print(f"Debug: FYERS credentials loaded - client_id={bool(client_id)}, secret_key={bool(secret_key)}, redirect_uri={bool(redirect_uri)}")

if not client_id or not secret_key or not redirect_uri:
    raise ValueError(f'Environment variables not loaded. Check .env file at {env_path}')

# Ensure credentials are set
if not client_id or not secret_key or not redirect_uri:
    raise ValueError('FYERS credentials not configured')

def save_tokens(access_token, refresh_token):
    from .models import FyersToken
    token, created = FyersToken.objects.get_or_create(id=1)
    token.access_token = access_token
    token.refresh_token = refresh_token
    token.save()

def load_tokens():
    from .models import FyersToken
    try:
        token = FyersToken.objects.get(id=1)
        return {'access_token': token.access_token, 'refresh_token': token.refresh_token}
    except FyersToken.DoesNotExist:
        return None

def refresh_access_token(refresh_token):
    try:
        import requests
        import json
        
        app_id_hash = os.getenv('FYERS_APP_ID_HASH')
        pin = os.getenv('FYERS_PIN')
        
        if not app_id_hash or not pin:
            return None
        
        url = "https://api-t1.fyers.in/api/v3/validate-refresh-token"
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "grant_type": "refresh_token",
            "appIdHash": app_id_hash,
            "refresh_token": refresh_token,
            "pin": pin
        }
        
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        if response.status_code == 200:
            result = response.json()
            if result.get('code') == 200:
                new_access_token = result.get('access_token')
                if new_access_token:
                    save_tokens(new_access_token, refresh_token)
                    return new_access_token
        
        return None
    except Exception as e:
        return None

def is_token_valid(access_token):
    """Test if access token is valid by making a simple API call"""
    try:
        fyers = fyersModel.FyersModel(client_id=client_id, is_async=False, token=access_token, log_path="")
        response = fyers.get_profile()
        return response and response.get('code') == 200
    except:
        return False

def get_valid_access_token():
    token_data = load_tokens()
    if not token_data or 'access_token' not in token_data:
        return None
    
    # Test if current access token is valid by making API call
    access_token = token_data['access_token']
    if is_token_valid(access_token):
        return access_token
    
    # Token is expired, try to refresh
    if 'refresh_token' in token_data:
        new_token = refresh_access_token(token_data['refresh_token'])
        if new_token:
            return new_token
    
    return None

def login_fyers():
    access_token = get_valid_access_token()
    if not access_token:
        print("No valid access token available")
        return None
    
    print(f"Using access token: {access_token[:20]}...")
    fyers = fyersModel.FyersModel(client_id=client_id, is_async=False, token=access_token, log_path="")
    return fyers

def generate_auth_url():
    session = fyersModel.SessionModel(
        client_id=client_id,
        secret_key=secret_key,
        redirect_uri=redirect_uri,
        response_type="code",
        # grant_type="authorization_code"
    )
    if app_id_hash:
        return session.generate_authcode() + f"&appIdHash={app_id_hash}"
    return session.generate_authcode()

def generate_tokens_from_auth_code(auth_code):
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
