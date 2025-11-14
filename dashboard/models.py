from django.db import models
from django.contrib.auth.models import User

class UserSession(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=40, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.session_key}"

class FyersToken(models.Model):
    access_token = models.TextField()
    refresh_token = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'fyers_tokens'
    
    def __str__(self):
        return f"Fyers Token - {self.created_at}"
