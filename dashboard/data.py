# ========== IMPORTS ==========
from fyers_apiv3 import fyersModel  # Fyers API for option chain data
import pandas as pd  # Data manipulation
import json  # JSON file operations
from datetime import datetime  # Date/time handling
import pytz  # Timezone conversions
import os  # File operations
import time  # Timestamp operations
from py_vollib.black_scholes.implied_volatility import implied_volatility as iv  # IV calculation
from py_vollib.black_scholes.greeks.analytical import delta, gamma, theta, vega  # Greeks calculation

# ========== FYERS API CREDENTIALS ==========
client_id = "OWRV3NJHQP-100"  # Fyers client ID
secret_key = "IB47SMWB8B"  # Fyers secret key
redirect_uri = "https://www.angelone.in/trade/watchlist/chart"  # OAuth redirect URI
response_type = "code"  # OAuth response type

# Initialize Fyers session for authentication
session = fyersModel.SessionModel(
    client_id=client_id,
    secret_key=secret_key, 
    redirect_uri=redirect_uri, 
    response_type=response_type,
    grant_type="authorization_code"  # Initial token generation
)

# ========== TOKEN MANAGEMENT ==========
TOKEN_FILE = 'fyers_tokens.json'  # File to store access and refresh tokens

def save_tokens(access_token, refresh_token):
    """
    Save access and refresh tokens to JSON file with timestamp
    Tokens are valid for 24 hours (access) and 15 days (refresh)
    
    Args:
        access_token (str): Fyers access token for API calls
        refresh_token (str): Refresh token to generate new access token
    """
    token_data = {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'timestamp': time.time()  # Store when tokens were saved
    }
    try:
        with open(TOKEN_FILE, 'w') as f:
            json.dump(token_data, f)
    except Exception as e:
        print(f"Error saving tokens: {e}")

def load_tokens():
    """
    Load saved tokens from JSON file
    
    Returns:
        dict: Token data with access_token, refresh_token, timestamp
        None: If file doesn't exist or error occurs
    """
    try:
        with open(TOKEN_FILE, 'r') as f:
            return json.load(f)
    except:
        return None  # File not found or invalid JSON

def refresh_access_token(refresh_token):
    """
    Generate new access token using refresh token
    Called automatically when access token expires (24 hours)
    
    Args:
        refresh_token (str): Valid refresh token (valid for 15 days)
    
    Returns:
        str: New access token if successful
        None: If refresh fails
    """
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
    """
    Get valid access token - attempts to refresh if expired
    Falls back to generating new token from auth_token if refresh fails
    
    Returns:
        str: Valid access token for API calls
    """
    token_data = load_tokens()
    
    if token_data and 'refresh_token' in token_data:
        refreshed_token = refresh_access_token(token_data['refresh_token'])
        if refreshed_token:
            return refreshed_token
    
    # Fallback: Use auth_token to generate new tokens (valid for 15 days from generation)
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

# Initialize access token on module load
access_token = get_valid_access_token()

# ========== FYERS LOGIN ==========
def login_fyers():
    """
    Login to Fyers API and return authenticated FyersModel instance
    Automatically refreshes token if expired
    
    Returns:
        FyersModel: Authenticated Fyers API instance
        None: If login fails
    """
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

# ========== DATE/TIME UTILITIES ==========
def get_expiry_timestamp_ist(date_str: str, time_str: str = "15:30") -> int:
    """
    Convert expiry date string to Unix timestamp in IST timezone
    Options expire at 3:30 PM IST on expiry date
    
    Args:
        date_str (str): Date in DD-MM-YYYY format
        time_str (str): Time in HH:MM format (default: 15:30)
    
    Returns:
        int: Unix timestamp in seconds
    """
    dt_naive = datetime.strptime(f"{date_str} {time_str}", "%d-%m-%Y %H:%M")
    ist = pytz.timezone("Asia/Kolkata")
    dt_ist = ist.localize(dt_naive)
    return int(dt_ist.timestamp())

def calculate_days_to_expiry(expiry_date_str):
    """
    Calculate number of days remaining until expiry
    Used for Greeks calculation (time to expiry)
    
    Args:
        expiry_date_str (str): Expiry date in DD-MM-YYYY format
    
    Returns:
        int: Days to expiry (minimum 1, default 7 if error)
    """
    try:
        expiry_date = datetime.strptime(expiry_date_str, "%d-%m-%Y")
        today = datetime.now()
        days = (expiry_date - today).days
        return max(1, days)  # Minimum 1 day to avoid division by zero
    except:
        return 7  # Default 7 days if date parsing fails

# ========== GREEKS CALCULATION ==========
def calculate_greeks(spot_price, strike_price, days_to_expiry, option_type, ltp):
    """
    Calculate Implied Volatility and Greeks using Black-Scholes model
    Uses py_vollib library for accurate calculations
    
    Args:
        spot_price (float): Current spot/futures price
        strike_price (float): Option strike price
        days_to_expiry (int): Days until expiry
        option_type (str): 'CE' for Call or 'PE' for Put
        ltp (float): Last Traded Price of option
    
    Returns:
        dict: {
            'delta': Delta (0-1 for calls, -1-0 for puts),
            'gamma': Gamma (rate of change of delta),
            'theta': Theta (time decay per day),
            'vega': Vega (sensitivity to volatility),
            'iv': Implied Volatility (percentage)
        }
    """
    try:
        r = 0.10  # Risk-free rate (10% annual)
        T = days_to_expiry / 365.0  # Convert days to years
        S = float(spot_price)  # Spot price
        K = float(strike_price)  # Strike price
        price = float(ltp)  # Option price
        
        if T <= 0 or S <= 0 or K <= 0 or price <= 0:
            return {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0, 'iv': 0}
        
        flag = 'c' if option_type == 'CE' else 'p'  # py_vollib uses 'c' for call, 'p' for put
        
        # Calculate Implied Volatility using Newton-Raphson method
        try:
            sigma = iv(price, S, K, T, r, flag)
        except:
            sigma = 0.15  # Default IV if calculation fails
        
        # Calculate Greeks using Black-Scholes formulas
        delta_val = delta(flag, S, K, T, r, sigma)  # Delta: 0-1 for calls, -1-0 for puts
        gamma_val = gamma(flag, S, K, T, r, sigma) * 100  # Gamma: scaled by 100
        theta_val = theta(flag, S, K, T, r, sigma) / 365  # Theta: per day (not per year)
        vega_val = vega(flag, S, K, T, r, sigma) / 100  # Vega: per 1% change in IV
        
        return {
            'delta': round(delta_val, 2),
            'gamma': round(gamma_val, 2),
            'theta': round(theta_val, 2),
            'vega': round(vega_val, 2),
            'iv': round(sigma * 100, 2)
        }
    except Exception as e:
        print(f"Error calculating Greeks: {e}")
        return {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0, 'iv': 0}

# ========== GLOBAL INSTANCES ==========
fyers = login_fyers()  # Initialize Fyers API instance
data_cache = {}  # Cache for option chain data (2 second TTL)

def get_fyers_instance():
    """
    Get or create Fyers API instance
    
    Returns:
        FyersModel: Authenticated Fyers instance
    """
    global fyers
    if fyers is None:
        fyers = login_fyers()
    return fyers

def get_lot_size(symbol):
    """
    Get lot size for a symbol from symbol.json
    Lot size is used to convert OI and Volume from contracts to lots
    
    Args:
        symbol (str): Symbol name (e.g., 'NSE:NIFTY50-INDEX')
    
    Returns:
        int: Lot size (default 1 if not found)
    """
    try:
        with open('dashboard/static/symbol.json', 'r') as f:
            data = json.load(f)
        return data.get('lot_sizes', {}).get(symbol, 1)
    except:
        return 1  # Default lot size

# ========== CURRENT SELECTION STATE ==========
current_symbol = 'NSE:NIFTY50-INDEX'  # Default symbol
current_expiry = '30-10-2025'  # Default expiry
current_strikecount = 10  # Default strike count

def update_symbol_expiry(symbol, expiry):
    """
    Update current symbol and expiry selection
    
    Args:
        symbol (str): Symbol name
        expiry (str): Expiry date in DD-MM-YYYY format
    
    Returns:
        tuple: (symbol, expiry)
    """
    global current_symbol, current_expiry
    current_symbol = symbol
    current_expiry = expiry
    return current_symbol, current_expiry

def update_strikecount(strikecount):
    """
    Update current strike count selection
    
    Args:
        strikecount (int): Number of strikes to display
    
    Returns:
        int: Updated strike count
    """
    global current_strikecount
    current_strikecount = strikecount
    return current_strikecount

# ========== MOCK DATA (FALLBACK) ==========
def get_mock_data(symbol):
    """
    Generate mock option chain data for testing/fallback
    Used when Fyers API is unavailable
    
    Args:
        symbol (str): Symbol name
    
    Returns:
        tuple: (DataFrame with mock data, base_price)
    """
    import random
    base_price = 24000 if 'NIFTY' in symbol else 50000  # Base price for strikes
    strikes = [base_price + (i * 50) for i in range(-5, 6)]  # 11 strikes
    
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

# ========== SYMBOL QUOTE ==========
def get_symbol_quote(symbol):
    """
    Get current LTP and change data for a symbol
    
    Args:
        symbol (str): Symbol name (e.g., 'NSE:NIFTY50-INDEX')
    
    Returns:
        dict: {
            'ltp': Last Traded Price,
            'prev_close': Previous close price,
            'change_points': Change in points,
            'change_percent': Change in percentage
        }
    """
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

# ========== MAIN DATA FUNCTION ==========
def getLiveData(symbol=None, expiry=None, strikecount=None):
    """
    Fetch live option chain data from Fyers API
    Includes Greeks calculation for all options
    Returns cached data if called within 2 seconds
    
    Args:
        symbol (str): Symbol name (default: current_symbol)
        expiry (str): Expiry date in DD-MM-YYYY format (default: current_expiry)
        strikecount (int): Number of strikes (default: current_strikecount)
    
    Returns:
        tuple: (
            list: Option chain data with Greeks,
            dict: Quote data (LTP, change),
            float: PCR (Put-Call Ratio)
        )
    """
    global data_cache, fyers
    
    try:
        use_symbol = symbol or current_symbol
        use_expiry = expiry or current_expiry
        use_strikecount = strikecount or current_strikecount
        
        # Check cache to avoid excessive API calls
        cache_key = f"{use_symbol}_{use_expiry}_{use_strikecount}"
        current_time = time.time()
        
        # Return cached data if less than 2 seconds old
        if cache_key in data_cache and (current_time - data_cache[cache_key]['timestamp']) < 2:
            return data_cache[cache_key]['data'], data_cache[cache_key]['quote_data'], data_cache[cache_key].get('pcr', 0)
        
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
                    # Calculate max values for percentage calculations
                    max_call_volume = max(item['volume'] for item in calls) or 1
                    max_call_oi = max(item['oi'] for item in calls) or 1
                    max_put_volume = max(item['volume'] for item in puts) or 1
                    max_put_oi = max(item['oi'] for item in puts) or 1
                    
                    spot_price = quote_data.get('ltp', 0)
                    days_to_expiry = calculate_days_to_expiry(use_expiry)
                    
                    combined_data = []
                    for i in range(min(len(calls), len(puts))):
                        call = calls[i]
                        put = puts[i]
                        lot_size = get_lot_size(use_symbol)
                        strike_price = call.get('strike_price', 0)
                        
                        # Calculate Greeks for both Call and Put options
                        call_greeks = calculate_greeks(spot_price, strike_price, days_to_expiry, 'CE', call.get('ltp', 0))
                        put_greeks = calculate_greeks(spot_price, strike_price, days_to_expiry, 'PE', put.get('ltp', 0))
                        
                        row = {
                            'CALL_OICH': call.get('oich', 0) // lot_size,
                            'CALL_OI': call.get('oi', 0) // lot_size,
                            'CALL_PMCOI': round((call.get('oi', 0) / max_call_oi) * 100, 2),
                            'CALL_VOLUME': call.get('volume', 0) // lot_size,
                            'CALL_PMCV': round((call.get('volume', 0) / max_call_volume) * 100, 2),
                            'CALL_LTPCH': call.get('ltpch', 0),
                            'CALL_LTP': call.get('ltp', 0),
                            'CALL_IV': call_greeks['iv'],
                            'CALL_DELTA': call_greeks['delta'],
                            'CALL_GAMMA': call_greeks['gamma'],
                            'CALL_THETA': call_greeks['theta'],
                            'CALL_VEGA': call_greeks['vega'],
                            'STRIKE_PRICE': strike_price,
                            'PUT_LTP': put.get('ltp', 0),
                            'PUT_LTPCH': put.get('ltpch', 0),
                            'PUT_IV': put_greeks['iv'],
                            'PUT_DELTA': put_greeks['delta'],
                            'PUT_GAMMA': put_greeks['gamma'],
                            'PUT_THETA': put_greeks['theta'],
                            'PUT_VEGA': put_greeks['vega'],
                            'PUT_PMPV': round((put.get('volume', 0) / max_put_volume) * 100, 2),
                            'PUT_VOLUME': put.get('volume', 0) // lot_size,
                            'PUT_PMPOI': round((put.get('oi', 0) / max_put_oi) * 100, 2),
                            'PUT_OI': put.get('oi', 0) // lot_size,
                            'PUT_OICH': put.get('oich', 0) // lot_size
                        }
                        combined_data.append(row)
                    
                    # Calculate PCR (Put-Call Ratio) - Market sentiment indicator
                    # PCR > 1: More puts (bearish), PCR < 1: More calls (bullish)
                    total_put_oi = sum(put.get('oi', 0) for put in puts)
                    total_call_oi = sum(call.get('oi', 0) for call in calls)
                    pcr = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 0
                    
                    data_cache[cache_key] = {
                        'data': combined_data,
                        'quote_data': quote_data,
                        'pcr': pcr,
                        'timestamp': current_time
                    }
                    
                    return combined_data, quote_data, pcr
        
        print(f"⚠️ Using mock data for {use_symbol} - API unavailable")
        quote_data = get_symbol_quote(use_symbol)
        mock_df, base_price = get_mock_data(use_symbol)
        
        # Calculate PCR for mock data
        total_put_oi = sum(row['PUT_OI'] for row in mock_df.to_dict('records'))
        total_call_oi = sum(row['CALL_OI'] for row in mock_df.to_dict('records'))
        pcr = round(total_put_oi / total_call_oi, 2) if total_call_oi > 0 else 0
        
        data_cache[cache_key] = {
            'data': mock_df.to_dict('records'),
            'quote_data': quote_data,
            'pcr': pcr,
            'timestamp': current_time
        }
        
        return mock_df.to_dict('records'), quote_data, pcr
        
    except Exception as e:
        print(f"Error in getLiveData: {e}")
        mock_df, _ = get_mock_data(use_symbol or current_symbol)
        quote_data = {'ltp': 0, 'prev_close': 0, 'change_points': 0, 'change_percent': 0}
        return mock_df.to_dict('records'), quote_data, 0
