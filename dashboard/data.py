from fyers_apiv3 import fyersModel
import pandas as pd
import json
from datetime import datetime
import pytz
import os
import time







client_id = "OWRV3NJHQP-100"
secret_key = "IB47SMWB8B"
redirect_uri = "https://www.angelone.in/trade/watchlist/chart"
response_type = "code"

session = fyersModel.SessionModel(
    client_id=client_id,
    secret_key=secret_key, 
    redirect_uri=redirect_uri, 
    response_type=response_type,
    grant_type="authorization_code"
    
)

# Token storage file
TOKEN_FILE = 'fyers_tokens.json'

def save_tokens(access_token, refresh_token):
    """Save tokens to file with timestamp"""
    token_data = {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'timestamp': time.time()
    }
    try:
        with open(TOKEN_FILE, 'w') as f:
            json.dump(token_data, f)
    except Exception as e:
        print(f"Error saving tokens: {e}")

def load_tokens():
    """Load tokens from file"""
    try:
        with open(TOKEN_FILE, 'r') as f:
            return json.load(f)
    except:
        return None

def refresh_access_token(refresh_token):
    """Generate new access token using refresh token"""
    try:
        refresh_session = fyersModel.SessionModel(
            client_id=client_id,
            secret_key=secret_key,
            redirect_uri=redirect_uri,
            response_type=response_type,
            grant_type="refresh_token"
        )
        refresh_session.set_token(refresh_token)
        response = refresh_session.generate_token()
        
        if response and response.get('code') == 200:
            new_access_token = response['access_token']
            new_refresh_token = response.get('refresh_token', refresh_token)
            save_tokens(new_access_token, new_refresh_token)
            print("🔄 Token refreshed successfully")
            return new_access_token
        else:
            print(f"Token refresh failed: {response}")
            return None
    except Exception as e:
        print(f"Error refreshing token: {e}")
        return None

def get_valid_access_token():
    """Get valid access token, refresh if needed"""
    # Try to load existing tokens first (for server restarts)
    token_data = load_tokens()
    
    if token_data and 'refresh_token' in token_data:
        # Always try refresh token first for server restarts
        refreshed_token = refresh_access_token(token_data['refresh_token'])
        if refreshed_token:
            return refreshed_token
    
    # Fallback to generate new token from auth code
    auth_token = os.getenv('FYERS_AUTH_TOKEN', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcHBfaWQiOiJPV1JWM05KSFFQIiwidXVpZCI6Ijg2NzcyYmU0ZGM2ZTRhNjk4YWYxMTlmMGFkZWVjZjIwIiwiaXBBZGRyIjoiIiwibm9uY2UiOiIiLCJzY29wZSI6IiIsImRpc3BsYXlfbmFtZSI6IlhWMDI3NzQiLCJvbXMiOiJLMSIsImhzbV9rZXkiOiI0NWJhMDYzMGFkMzU1YWZjMzhmNmE1ZThlZmMwMTQyMGJhNTIzMDIyMzVlMDQ3MDk2YzhjNDM1ZSIsImlzRGRwaUVuYWJsZWQiOiJOIiwiaXNNdGZFbmFibGVkIjoiTiIsImF1ZCI6IltcImQ6MVwiLFwiZDoyXCIsXCJ4OjBcIixcIng6MVwiLFwieDoyXCJdIiwiZXhwIjoxNzYxOTU4OTQxLCJpYXQiOjE3NjE5Mjg5NDEsImlzcyI6ImFwaS5sb2dpbi5meWVycy5pbiIsIm5iZiI6MTc2MTkyODk0MSwic3ViIjoiYXV0aF9jb2RlIn0.mXvZkooz_hgRLe0ljlsH9SSSWGQknm7-N6pMjoO2XCo')
    session.set_token(auth_token)
    
    try:
        response = session.generate_token()
        if response and response.get('code') == 200:
            access_token = response['access_token']
            refresh_token = response.get('refresh_token')
            if refresh_token:
                save_tokens(access_token, refresh_token)
                print(f"New tokens generated and saved: {access_token[:50]}...")
            return access_token
        else:
            print(f"Token generation failed: {response}")
            return auth_token
    except Exception as e:
        print(f"Error generating token: {e}")
        return auth_token

# Get valid access token
access_token = get_valid_access_token()

def login_fyers():
    global access_token
    try:
        # Get fresh token if current one is invalid
        current_token = get_valid_access_token()
        if current_token != access_token:
            access_token = current_token
            
        if not access_token:
            print("No access token available")
            return None
            
        fyers = fyersModel.FyersModel(client_id=client_id, is_async=False, token=access_token, log_path="")
        profile_response = fyers.get_profile()
        
        if profile_response and profile_response.get('code') == 200:
            print("🟢 Login successful.")
            return fyers
        else:
            # Try refreshing token if login failed
            print("🔄 Attempting token refresh...")
            access_token = get_valid_access_token()
            fyers = fyersModel.FyersModel(client_id=client_id, is_async=False, token=access_token, log_path="")
            profile_response = fyers.get_profile()
            
            if profile_response and profile_response.get('code') == 200:
                print("🟢 Login successful after refresh.")
                return fyers
            else:
                print("🚨 Login failed.")
                return None
    except Exception as e:
        print(f"Error in login_fyers: {e}")
        return None



def get_expiry_timestamp_ist(date_str: str, time_str: str = "15:30") -> int:
    """
    Given a date in DD-MM-YYYY, return the Unix timestamp (seconds since epoch UTC)
    for that date at the exchange expiry time (15:30 IST).
    """
    # 1. Parse date + expiry time
    dt_naive = datetime.strptime(f"{date_str} {time_str}", "%d-%m-%Y %H:%M")
    # 2. Localize to IST
    ist = pytz.timezone("Asia/Kolkata")
    dt_ist = ist.localize(dt_naive)
    # 3. Return the UTC‐based Unix timestamp
    return int(dt_ist.timestamp())


# Pre-initialize fyers for instant response
fyers = login_fyers()

data_cache = {}

def get_fyers_instance():
    global fyers
    if fyers is None:
        fyers = login_fyers()
    return fyers

def get_lot_size(symbol):
    try:
        with open('dashboard/static/symbol.json', 'r') as f:
            data = json.load(f)
        return data.get('lot_sizes', {}).get(symbol, 1)
    except:
        return 1

current_symbol = 'NSE:NIFTY50-INDEX'
current_expiry = '30-10-2025'
current_strikecount = 10


def update_symbol_expiry(symbol, expiry):
    global current_symbol, current_expiry
    current_symbol = symbol
    current_expiry = expiry
    return current_symbol, current_expiry

def update_strikecount(strikecount):
    global current_strikecount
    current_strikecount = strikecount
    return current_strikecount


def getLiveData(symbol=None, expiry=None, strikecount=None):
    global data_cache, fyers
    
    try:
        # Use parameters if provided, otherwise fall back to globals
        use_symbol = symbol or current_symbol
        use_expiry = expiry or current_expiry
        use_strikecount = strikecount or current_strikecount
        
        cache_key = f"{use_symbol}_{use_expiry}_{use_strikecount}"
        current_time = time.time()
        
        # Return cached data if less than 2 seconds old
        if cache_key in data_cache and (current_time - data_cache[cache_key]['timestamp']) < 2:
            return data_cache[cache_key]['data'], data_cache[cache_key]['ltp']
        
        data = {
        "symbol":use_symbol,
        "strikecount":use_strikecount,
        "timestamp": get_expiry_timestamp_ist(use_expiry)
        }
        
        # Get fyers instance with token refresh if needed
        if not fyers:
            fyers = login_fyers()
        if not fyers:
            return None
            
        response = fyers.optionchain(data=data)
        
        # If API call fails due to token expiry, try refreshing
        if response.get('code') == 401 or response.get('code') == 403:
            print("🔄 Token expired, refreshing...")
            fyers = login_fyers()
            if fyers:
                response = fyers.optionchain(data=data)
        
        if response.get('code') != 200 or not response.get('data', {}).get('optionsChain'):
            print(f"Invalid response or no data for {use_symbol} {use_expiry}: {response.get('message', 'Unknown error')}")
            return None

        # Get LTP from option chain response if available, otherwise make separate call
        ltp_current_symbol = response.get('data', {}).get('ltp', 0)
        if not ltp_current_symbol:
            ltp_response = fyers.quotes({"symbols":use_symbol})
            ltp_current_symbol = ltp_response['d'][0]['v']['lp'] if ltp_response.get('code') == 200 else 0

        option_data = response['data']['optionsChain']
        if not option_data:
            return None

        # Separate calls and puts without pandas for speed
        calls = [item for item in option_data if item['option_type'] == 'CE']
        puts = [item for item in option_data if item['option_type'] == 'PE']
        
        if not calls or not puts:
            return None
        
        # Calculate max values for percentage calculations
        max_call_volume = max(item['volume'] for item in calls)
        max_call_oi = max(item['oi'] for item in calls)
        max_put_volume = max(item['volume'] for item in puts)
        max_put_oi = max(item['oi'] for item in puts)
        
        # Build combined data directly
        combined_data = []
        for i in range(len(calls)):
            call = calls[i]
            put = puts[i] if i < len(puts) else {}
            
            # Get lot size for volume calculation
            lot_size = get_lot_size(use_symbol)
            
            # Calculate percentages
            call_pmcv = round((call['volume'] / max_call_volume) * 100, 2) if max_call_volume > 0 else 0
            call_pmcoi = round((call['oi'] / max_call_oi) * 100, 2) if max_call_oi > 0 else 0
            put_pmpv = round((put.get('volume', 0) / max_put_volume) * 100, 2) if max_put_volume > 0 else 0
            put_pmpoi = round((put.get('oi', 0) / max_put_oi) * 100, 2) if max_put_oi > 0 else 0
            
            row = {
                'CALL_OICH': call.get('oich', 0) // lot_size,  # Divide by lot size
                'CALL_OI': call.get('oi', 0) // lot_size,  # Divide by lot size
                'CALL_PMCOI': call_pmcoi,
                'CALL_VOLUME': call.get('volume', 0) // lot_size,  # Divide by lot size
                'CALL_PMCV': call_pmcv,
                'CALL_LTPCH': call.get('ltpch', 0),
                'CALL_LTP': call.get('ltp', 0),
                'STRIKE_PRICE': call.get('strike_price', 0),
                'PUT_LTP': put.get('ltp', 0),
                'PUT_LTPCH': put.get('ltpch', 0),
                'PUT_PMPV': put_pmpv,
                'PUT_VOLUME': put.get('volume', 0) // lot_size,  # Divide by lot size
                'PUT_PMPOI': put_pmpoi,
                'PUT_OI': put.get('oi', 0) // lot_size,  # Divide by lot size
                'PUT_OICH': put.get('oich', 0) // lot_size  # Divide by lot size
            }
            combined_data.append(row)
        
        # Convert to DataFrame for compatibility
        df_combined = pd.DataFrame(combined_data)
        
        # Cache the result
        data_cache[cache_key] = {
            'data': df_combined,
            'ltp': ltp_current_symbol,
            'timestamp': current_time
        }
        
        return df_combined, ltp_current_symbol
        

    except Exception as e:
        print("Error in getLiveData:", e)
        return None

