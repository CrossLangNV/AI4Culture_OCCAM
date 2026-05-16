from django.urls import path
from .views import LoginAPIView, TokenRefreshAPIView

urlpatterns = [
    path('login/', LoginAPIView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshAPIView.as_view(), name='token_refresh'),
]