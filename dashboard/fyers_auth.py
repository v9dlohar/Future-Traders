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

# Stored tokens - these will be updated when new tokens are generated
STORED_ACCESS_TOKEN = None
STORED_REFRESH_TOKEN = None

# Ensure credentials are set
if not client_id or not secret_key or not redirect_uri:
    raise ValueError('FYERS credentials not configured')

def save_tokens(access_token, refresh_token):
    global STORED_ACCESS_TOKEN, STORED_REFRESH_TOKEN
    STORED_ACCESS_TOKEN = access_token
    STORED_REFRESH_TOKEN = refresh_token
    
    # Also update the file with new token values
    update_tokens_in_file(access_token, refresh_token)

def load_tokens():
    global STORED_ACCESS_TOKEN, STORED_REFRESH_TOKEN
    if STORED_ACCESS_TOKEN and STORED_REFRESH_TOKEN:
        return {'access_token': STORED_ACCESS_TOKEN, 'refresh_token': STORED_REFRESH_TOKEN}
    return None

def update_tokens_in_file(access_token, refresh_token):
    """Update the token variables in this file"""
    import re
    
    file_path = __file__
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Update tokens in file
    content = re.sub(r'STORED_ACCESS_TOKEN = .*', f'STORED_ACCESS_TOKEN = "{access_token}"', content)
    content = re.sub(r'STORED_REFRESH_TOKEN = .*', f'STORED_REFRESH_TOKEN = "{refresh_token}"', content)
    
    with open(file_path, 'w') as f:
        f.write(content)

def refresh_access_token(refresh_token):
    try:
        import requests
        import json
        
        app_id_hash = os.getenv('FYERS_APP_ID_HASH')
        pin = os.getenv('FYERS_PIN')
        
        print(f"Refresh token method: app_id_hash={bool(app_id_hash)}, pin={bool(pin)}")
        print(f"Using refresh token: {refresh_token}")
        
        if not app_id_hash or not pin:
            print("Missing FYERS_APP_ID_HASH or FYERS_PIN environment variables")
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
        
        print("Status Code:", response.status_code)
        print("Response JSON:", response.json())
        
        if response.status_code == 200:
            result = response.json()
            if result.get('code') == 200:
                new_access_token = result.get('access_token')
                if new_access_token:
                    print("✅ Refresh token method WORKING - New access token generated")
                    save_tokens(new_access_token, refresh_token)
                    return new_access_token
                else:
                    print("❌ Refresh token method FAILED - No access token in response")
            else:
                error_code = result.get('code')
                if error_code == -1009:
                    print("❌ Refresh token EXPIRED - Need fresh authentication (15 days expired)")
                else:
                    print(f"❌ Refresh token method FAILED - API error code: {error_code}")
        else:
            print(f"❌ Refresh token method FAILED - HTTP error: {response.status_code}")
        
        return None
    except Exception as e:
        print(f"❌ Refresh token method FAILED - Exception: {e}")
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
        return None
    
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
