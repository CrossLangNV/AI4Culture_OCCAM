from django.urls import path
from .views import RegisterAPIView, LoginAPIView, TokenRefreshAPIView

urlpatterns = [
    path('register/', RegisterAPIView.as_view(), name='register'),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshAPIView.as_view(), name='token_refresh'),
]