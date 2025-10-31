from django.shortcuts import render, redirect
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse
from django.contrib import messages
import json
import os
from django.conf import settings

def is_admin(user):
    return user.is_superuser

@user_passes_test(is_admin)
def update_expiry_dates(request):
    if request.method == 'POST':
        try:
            symbol = request.POST.get('symbol')
            expiry_dates = request.POST.get('expiry_dates')
            
            # Parse expiry dates (comma-separated)
            dates_list = [date.strip() for date in expiry_dates.split(',')]
            
            # Load current symbol.json
            symbol_file_path = os.path.join(settings.BASE_DIR, 'dashboard', 'static', 'symbol.json')
            with open(symbol_file_path, 'r') as f:
                data = json.load(f)
            
            # Update the symbol's expiry dates
            data['expiry_dates'][symbol] = dates_list
            
            # Save back to file
            with open(symbol_file_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            messages.success(request, f'Updated expiry dates for {symbol}')
            return redirect('admin_expiry')
            
        except Exception as e:
            messages.error(request, f'Error updating expiry dates: {str(e)}')
    
    # Load current data for display
    try:
        symbol_file_path = os.path.join(settings.BASE_DIR, 'dashboard', 'static', 'symbol.json')
        with open(symbol_file_path, 'r') as f:
            data = json.load(f)
        symbols_data = data['expiry_dates']
    except:
        symbols_data = {}
    
    return render(request, 'dashboard/admin_expiry.html', {'symbols_data': symbols_data})