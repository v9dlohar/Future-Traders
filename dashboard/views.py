from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.sessions.models import Session
from django.http import JsonResponse
import pandas as pd
from .data import getLiveData
from .data import update_symbol_expiry, update_strikecount
from .models import UserSession

# Cache for storing last successful data
last_successful_data = {}

def home_view(request):
    return render(request, 'dashboard/home.html')

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            
            # Delete old session if exists
            try:
                old_user_session = UserSession.objects.get(user=user)
                old_session = Session.objects.get(session_key=old_user_session.session_key)
                old_session.delete()
                old_user_session.delete()
            except (UserSession.DoesNotExist, Session.DoesNotExist):
                pass
            
            # Login user and create new session tracking
            login(request, user)
            user_session, created = UserSession.objects.get_or_create(user=user, defaults={'session_key': request.session.session_key})
            if not created:
                user_session.session_key = request.session.session_key
                user_session.save()
            
            return redirect('optionchain')
    else:
        form = AuthenticationForm()
    return render(request, 'dashboard/login.html', {'form': form})


@login_required
def dashboard_view(request):
    try:
        data = getLiveData()
    except Exception as e:
        print(f"Error loading dashboard data: {e}")
        data = None
    return render(request, 'dashboard/dashboard.html')


@login_required
def optionchain_view(request):
    # Check if user session is still valid
    try:
        user_session = UserSession.objects.get(user=request.user)
        if user_session.session_key != request.session.session_key:
            return redirect('/login/')
    except UserSession.DoesNotExist:
        return redirect('/login/')
        
    try:
        data = getLiveData()
        optionchain_data = data.to_dict(orient='records') if data is not None else []
    except Exception as e:
        print(f"Error loading optionchain data: {e}")
        optionchain_data = []
    return render(request, 'dashboard/optionchain.html', {'optionchain_data': optionchain_data})

@login_required
def get_live_data(request):
    # Check if user session is still valid (not logged out from another device)
    try:
        user_session = UserSession.objects.get(user=request.user)
        if user_session.session_key != request.session.session_key:
            return JsonResponse({'redirect': '/login/', 'message': 'Logged in Other Device'})
    except UserSession.DoesNotExist:
        return JsonResponse({'redirect': '/login/', 'message': 'Logged in Other Device'})
    
    symbol = request.GET.get('symbol', 'NSE:NIFTY50-INDEX')
    expiry = request.GET.get('expiry', '28-11-2025')
    strikecount = int(request.GET.get('strikecount', '10'))
    update_symbol_expiry(symbol, expiry)
    update_strikecount(strikecount)
    print(f"Fetching data for: {symbol}, {expiry}, {strikecount}")
    
    cache_key = f"{symbol}_{expiry}_{strikecount}"
    
    try:
        result = getLiveData(symbol, expiry, strikecount)
        if result is None:
            print("getLiveData returned None - using previous data")
            # Return previous data if available
            if cache_key in last_successful_data:
                print("Returning cached data")
                return JsonResponse(last_successful_data[cache_key])
            else:
                return JsonResponse({'data': [], 'quote_data': {'ltp': 0, 'prev_close': 0, 'change_points': 0, 'change_percent': 0}, 'pcr': 0})
        
        data, quote_data, pcr = result
        print(f"Data fetched successfully: {len(data)} rows, LTP: {quote_data}, PCR: {pcr}")
        
        # Cache successful data
        response_data = {'data': data, 'quote_data': quote_data, 'pcr': pcr}
        last_successful_data[cache_key] = response_data
        
        return JsonResponse(response_data)
        
    except Exception as e:
        print(f"Error getting live data: {e}")
        import traceback
        traceback.print_exc()
        
        # Return previous data if available
        if cache_key in last_successful_data:
            print("Returning cached data due to error")
            return JsonResponse(last_successful_data[cache_key])
        else:
            return JsonResponse({'data': [], 'quote_data': {'ltp': 0, 'prev_close': 0, 'change_points': 0, 'change_percent': 0}})

