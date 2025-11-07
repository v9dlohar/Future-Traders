# ========== FYERS AUTHENTICATION FOR THIRD PARTY USERS ==========
from fyers_apiv3 import fyersModel
import os
import json
import time
from pathlib import Path

# Load .env file
from dotenv import load_dotenv
env_path = Path(__file__).resolve().parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path, override=True)

client_id = os.getenv('FYERS_CLIENT_ID')
secret_key = os.getenv('FYERS_SECRET_KEY')
redirect_uri = os.getenv('FYERS_REDIRECT_URI')
app_id_hash = os.getenv('FYERS_APP_ID_HASH', '')

if not client_id or not secret_key or not redirect_uri:
    raise ValueError(f'Environment variables not loaded. Check .env file at {env_path}')

TOKEN_FILE = str(Path(__file__).resolve().parent.parent / 'fyers_tokens.json')

# Ensure credentials are set
if not client_id or not secret_key or not redirect_uri:
    raise ValueError('FYERS credentials not configured')

def save_tokens(access_token, refresh_token):
    with open(TOKEN_FILE, 'w') as f:
        json.dump({'access_token': access_token, 'refresh_token': refresh_token, 'timestamp': time.time()}, f)

def load_tokens():
    try:
        with open(TOKEN_FILE, 'r') as f:
            return json.load(f)
    except:
        return None

def refresh_access_token(refresh_token):
    try:
        session = fyersModel.SessionModel(
            client_id=client_id,
            secret_key=secret_key,
            redirect_uri=redirect_uri,
            response_type="code",
            grant_type="refresh_token"
        )
        session.set_token(refresh_token)
        response = session.generate_token()
        
        if response and response.get('code') == 200:
            new_access_token = response['access_token']
            new_refresh_token = response.get('refresh_token', refresh_token)
            save_tokens(new_access_token, new_refresh_token)
            return new_access_token
        return None
    except:
        return None

def get_valid_access_token():
    token_data = load_tokens()
    if not token_data or 'access_token' not in token_data:
        return None
    
    # Check if token is expired (24 hours = 86400 seconds)
    if 'timestamp' in token_data:
        token_age = time.time() - token_data['timestamp']
        if token_age > 86400:  # 24 hours
            # Try to refresh token
            if 'refresh_token' in token_data:
                new_token = refresh_access_token(token_data['refresh_token'])
                if new_token:
                    return new_token
            return None
    
    return token_data['access_token']

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
        grant_type="authorization_code"
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
