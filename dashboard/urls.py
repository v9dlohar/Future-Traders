# ========== URL ROUTING ==========
# Maps URLs to view functions

from django.urls import path
from .views import home_view, login_view, dashboard_view, optionchain_view, get_live_data
from .admin_views import update_expiry_dates
from django.contrib.auth.views import LoginView

urlpatterns = [
    path('', home_view, name='home'),  # Home page (public)
    path('login/', login_view, name='login'),  # Login page (public)
    path('dashboard/', dashboard_view, name='dashboard'),  # Dashboard (protected)
    path('optionchain/', optionchain_view, name='optionchain'),  # Main option chain page (protected)
    path('get-live-data/', get_live_data, name='get_live_data'),  # API endpoint for live data (protected)
    path('manage/expiry/', update_expiry_dates, name='admin_expiry'),  # Admin: Update expiry dates (protected)
]
