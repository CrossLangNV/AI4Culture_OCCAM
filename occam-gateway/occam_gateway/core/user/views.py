from rest_framework_simplejwt.views import (
    TokenObtainPairView, TokenRefreshView,
)


# You can also subclass TokenObtainPairView if you need custom logic,
# but out of the box it works for standard username/password fields.
# In your case, “email” is the username field, so DRF + SimpleJWT
# should handle it automatically because your custom user
# defines USERNAME_FIELD = 'email'.

# Login Endpoint:
# POST /api/login/
#   { "email": <your_email>, "password": <your_password> }
#
# The default request body for SimpleJWT is "username" + "password".
# Because you've overridden USERNAME_FIELD to 'email',
# SimpleJWT will accept "email" instead of "username".
class LoginAPIView(TokenObtainPairView):
    pass  # Use as-is unless you need custom behavior.


class TokenRefreshAPIView(TokenRefreshView):
    pass
