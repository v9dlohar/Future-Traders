from django.urls import path
from .views import home_view, login_view, dashboard_view, optionchain_view, get_live_data
from .admin_views import update_expiry_dates
from django.contrib.auth.views import LoginView

urlpatterns = [
    path('', home_view, name='home'),
    path('login/', login_view, name='login'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('optionchain/', optionchain_view, name='optionchain'),
    path('get-live-data/', get_live_data, name='get_live_data'),
    path('manage/expiry/', update_expiry_dates, name='admin_expiry'),
]
