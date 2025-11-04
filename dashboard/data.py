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
    token_data = load_tokens()
    
    if token_data and 'refresh_token' in token_data:
        refreshed_token = refresh_access_token(token_data['refresh_token'])
        if refreshed_token:
            return refreshed_token
    
    auth_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcHBfaWQiOiJPV1JWM05KSFFQIiwidXVpZCI6IjQwMjJhMjE3Mzc1YzRkNzI4MzM5Yzc2YzJmZTEwOGMxIiwiaXBBZGRyIjoiIiwibm9uY2UiOiIiLCJzY29wZSI6IiIsImRpc3BsYXlfbmFtZSI6IlhWMDI3NzQiLCJvbXMiOiJLMSIsImhzbV9rZXkiOiI0NWJhMDYzMGFkMzU1YWZjMzhmNmE1ZThlZmMwMTQyMGJhNTIzMDIyMzVlMDQ3MDk2YzhjNDM1ZSIsImlzRGRwaUVuYWJsZWQiOiJOIiwiaXNNdGZFbmFibGVkIjoiTiIsImF1ZCI6IltcImQ6MVwiLFwiZDoyXCIsXCJ4OjBcIixcIng6MVwiLFwieDoyXCJdIiwiZXhwIjoxNzYyMjk5MTI4LCJpYXQiOjE3NjIyNjkxMjgsImlzcyI6ImFwaS5sb2dpbi5meWVycy5pbiIsIm5iZiI6MTc2MjI2OTEyOCwic3ViIjoiYXV0aF9jb2RlIn0.3UNvfIcL7VWH28DqHlFs_xLZlKJ_Foahut2Gy304Vv8'
    session.set_token(auth_token)
    
    try:
        response = session.generate_token()
        if response and response.get('code') == 200:
            access_token = response['access_token']
            refresh_token = response.get('refresh_token')
            if refresh_token:
                save_tokens(access_token, refresh_token)
                print(f"✅ New tokens generated and saved")
            return access_token
        else:
            return auth_token
    except Exception as e:
        print(f"Error generating token: {e}")
        return auth_token

access_token = get_valid_access_token()

def login_fyers():
    global access_token
    try:
        current_token = get_valid_access_token()
        if current_token != access_token:
            access_token = current_token
            
        if not access_token:
            return None
            
        fyers = fyersModel.FyersModel(client_id=client_id, is_async=False, token=access_token, log_path="")
        profile_response = fyers.get_profile()
        
        if profile_response and profile_response.get('code') == 200:
            print("🟢 Login successful.")
            return fyers
        else:
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
    dt_naive = datetime.strptime(f"{date_str} {time_str}", "%d-%m-%Y %H:%M")
    ist = pytz.timezone("Asia/Kolkata")
    dt_ist = ist.localize(dt_naive)
    return int(dt_ist.timestamp())

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

def get_mock_data(symbol):
    import random
    base_price = 24000 if 'NIFTY' in symbol else 50000
    strikes = [base_price + (i * 50) for i in range(-5, 6)]
    
    mock_data = []
    for strike in strikes:
        mock_data.append({
            'CALL_OICH': random.randint(-100, 100),
            'CALL_OI': random.randint(1000, 50000),
            'CALL_PMCOI': random.randint(10, 100),
            'CALL_VOLUME': random.randint(100, 5000),
            'CALL_PMCV': random.randint(5, 95),
            'CALL_LTPCH': random.uniform(-50, 50),
            'CALL_LTP': random.uniform(10, 500),
            'STRIKE_PRICE': strike,
            'PUT_LTP': random.uniform(10, 500),
            'PUT_LTPCH': random.uniform(-50, 50),
            'PUT_PMPV': random.randint(5, 95),
            'PUT_VOLUME': random.randint(100, 5000),
            'PUT_PMPOI': random.randint(10, 100),
            'PUT_OI': random.randint(1000, 50000),
            'PUT_OICH': random.randint(-100, 100)
        })
    
    return pd.DataFrame(mock_data), base_price

def get_symbol_quote(symbol):
    global fyers
    try:
        if not fyers:
            fyers = login_fyers()
        
        if fyers:
            quote_response = fyers.quotes({"symbols": symbol})
            if quote_response and quote_response.get('code') == 200:
                quote_data = quote_response.get('d', [{}])[0]
                ltp = quote_data.get('v', {}).get('lp', 0)
                change_points = quote_data.get('v', {}).get('ch', 0)
                change_percent = quote_data.get('v', {}).get('chp', 0)
                prev_close = ltp - change_points if ltp and change_points else 0
                
                if ltp:
                    return {
                        'ltp': ltp,
                        'prev_close': prev_close,
                        'change_points': round(change_points, 2),
                        'change_percent': round(change_percent, 2)
                    }
        
        import random
        ltp = 24000 + random.uniform(-200, 200)
        prev_close = 24000
        change_points = round(ltp - prev_close, 2)
        change_percent = round((change_points / prev_close) * 100, 2)
        
        return {
            'ltp': ltp,
            'prev_close': prev_close,
            'change_points': change_points,
            'change_percent': change_percent
        }
    except Exception as e:
        print(f"Error getting quote: {e}")
        return {'ltp': 0, 'prev_close': 0, 'change_points': 0, 'change_percent': 0}

def getLiveData(symbol=None, expiry=None, strikecount=None):
    global data_cache, fyers
    
    try:
        use_symbol = symbol or current_symbol
        use_expiry = expiry or current_expiry
        use_strikecount = strikecount or current_strikecount
        
        cache_key = f"{use_symbol}_{use_expiry}_{use_strikecount}"
        current_time = time.time()
        
        if cache_key in data_cache and (current_time - data_cache[cache_key]['timestamp']) < 2:
            return data_cache[cache_key]['data'], data_cache[cache_key]['quote_data']
        
        if not fyers:
            fyers = login_fyers()
        
        if fyers:
            data = {
                "symbol": use_symbol,
                "strikecount": use_strikecount,
                "timestamp": get_expiry_timestamp_ist(use_expiry)
            }
            
            response = fyers.optionchain(data=data)
            
            if response and response.get('code') == 200 and response.get('data', {}).get('optionsChain'):
                print(f"✅ Got real option chain data for {use_symbol}")
                
                quote_data = get_symbol_quote(use_symbol)
                option_data = response['data']['optionsChain']
                calls = [item for item in option_data if item['option_type'] == 'CE']
                puts = [item for item in option_data if item['option_type'] == 'PE']
                
                if calls and puts:
                    max_call_volume = max(item['volume'] for item in calls) or 1
                    max_call_oi = max(item['oi'] for item in calls) or 1
                    max_put_volume = max(item['volume'] for item in puts) or 1
                    max_put_oi = max(item['oi'] for item in puts) or 1
                    
                    combined_data = []
                    for i in range(min(len(calls), len(puts))):
                        call = calls[i]
                        put = puts[i]
                        lot_size = get_lot_size(use_symbol)
                        
                        row = {
                            'CALL_OICH': call.get('oich', 0) // lot_size,
                            'CALL_OI': call.get('oi', 0) // lot_size,
                            'CALL_PMCOI': round((call.get('oi', 0) / max_call_oi) * 100, 2),
                            'CALL_VOLUME': call.get('volume', 0) // lot_size,
                            'CALL_PMCV': round((call.get('volume', 0) / max_call_volume) * 100, 2),
                            'CALL_LTPCH': call.get('ltpch', 0),
                            'CALL_LTP': call.get('ltp', 0),
                            'STRIKE_PRICE': call.get('strike_price', 0),
                            'PUT_LTP': put.get('ltp', 0),
                            'PUT_LTPCH': put.get('ltpch', 0),
                            'PUT_PMPV': round((put.get('volume', 0) / max_put_volume) * 100, 2),
                            'PUT_VOLUME': put.get('volume', 0) // lot_size,
                            'PUT_PMPOI': round((put.get('oi', 0) / max_put_oi) * 100, 2),
                            'PUT_OI': put.get('oi', 0) // lot_size,
                            'PUT_OICH': put.get('oich', 0) // lot_size
                        }
                        combined_data.append(row)
                    
                    data_cache[cache_key] = {
                        'data': combined_data,
                        'quote_data': quote_data,
                        'timestamp': current_time
                    }
                    
                    return combined_data, quote_data
        
        print(f"⚠️ Using mock data for {use_symbol} - API unavailable")
        quote_data = get_symbol_quote(use_symbol)
        mock_df, base_price = get_mock_data(use_symbol)
        
        data_cache[cache_key] = {
            'data': mock_df.to_dict('records'),
            'quote_data': quote_data,
            'timestamp': current_time
        }
        
        return mock_df.to_dict('records'), quote_data
        
    except Exception as e:
        print(f"Error in getLiveData: {e}")
        mock_df, _ = get_mock_data(use_symbol or current_symbol)
        quote_data = {'ltp': 0, 'prev_close': 0, 'change_points': 0, 'change_percent': 0}
        return mock_df.to_dict('records'), quote_data
