# ========== IMPORTS ==========
from fyers_apiv3 import fyersModel
import pandas as pd
import json
from datetime import datetime
import pytz
import os
import time
from py_vollib.black_scholes.implied_volatility import implied_volatility as iv
from py_vollib.black_scholes.greeks.analytical import delta, gamma, theta, vega
from .fyers_auth import login_fyers


# Use absolute path for file operations
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ========== GLOBAL INSTANCES ==========
fyers = None
data_cache = {}



def get_lot_size(symbol):
    try:
        symbol_file = os.path.join(BASE_DIR, 'dashboard', 'static', 'symbol.json')
        with open(symbol_file, 'r') as f:
            data = json.load(f)
        return data.get('lot_sizes', {}).get(symbol, 1)
    except:
        return 1

# ========== CURRENT SELECTION STATE ==========
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

# ========== DATE/TIME UTILITIES ==========
def get_expiry_timestamp_ist(date_str: str, time_str: str = "15:30") -> int:
    dt_naive = datetime.strptime(f"{date_str} {time_str}", "%d-%m-%Y %H:%M")
    ist = pytz.timezone("Asia/Kolkata")
    dt_ist = ist.localize(dt_naive)
    return int(dt_ist.timestamp())

def calculate_days_to_expiry(expiry_date_str):
    try:
        expiry_date = datetime.strptime(expiry_date_str, "%d-%m-%Y")
        today = datetime.now()
        days = (expiry_date - today).days
        return max(1, days)
    except:
        return 7

# ========== GREEKS CALCULATION ==========
def calculate_greeks(spot_price, strike_price, days_to_expiry, option_type, ltp):
    try:
        r = 0.10
        T = days_to_expiry / 365.0
        S = float(spot_price)
        K = float(strike_price)
        price = float(ltp)
        
        if T <= 0 or S <= 0 or K <= 0 or price <= 0:
            return {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0, 'iv': 0}
        
        flag = 'c' if option_type == 'CE' else 'p'
        
        try:
            sigma = iv(price, S, K, T, r, flag)
        except:
            sigma = 0.15
        
        delta_val = delta(flag, S, K, T, r, sigma)
        gamma_val = gamma(flag, S, K, T, r, sigma) * 100
        theta_val = theta(flag, S, K, T, r, sigma) / 365
        vega_val = vega(flag, S, K, T, r, sigma) / 100
        
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

# ========== MOCK DATA ==========
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

# ========== SYMBOL QUOTE ==========
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

# ========== MAIN DATA FUNCTION ==========
def getLiveData(symbol=None, expiry=None, strikecount=None):
    global data_cache, fyers
    
    try:
        use_symbol = symbol or current_symbol
        use_expiry = expiry or current_expiry
        use_strikecount = strikecount or current_strikecount
        
        cache_key = f"{use_symbol}_{use_expiry}_{use_strikecount}"
        current_time = time.time()
        
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
            print(f"🔍 API Response Code: {response.get('code') if response else 'None'}")
            print(f"🔍 API Response: {response}")
            
            if response and response.get('code') == 200 and response.get('data', {}).get('optionsChain'):
                print(f"✅ Got real option chain data for {use_symbol}")
                
                # Extract real LTP from API response (first item is index data)
                option_data = response['data']['optionsChain']
                index_data = option_data[0] if option_data else {}
                quote_data = {
                    'ltp': index_data.get('ltp', 0),
                    'prev_close': index_data.get('ltp', 0) - index_data.get('ltpch', 0),
                    'change_points': round(index_data.get('ltpch', 0), 2),
                    'change_percent': round(index_data.get('ltpchp', 0), 2)
                }
                calls = [item for item in option_data if item['option_type'] == 'CE']
                puts = [item for item in option_data if item['option_type'] == 'PE']
                
                if calls and puts:
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
        
        print(f"⚠️ Using mock data for {use_symbol}")
        quote_data = get_symbol_quote(use_symbol)
        mock_df, base_price = get_mock_data(use_symbol)
        
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
