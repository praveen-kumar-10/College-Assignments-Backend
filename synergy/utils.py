from users.models import *
from rest_framework.authentication import get_authorization_header, BaseAuthentication
from rest_framework.exceptions import ValidationError, ErrorDetail, AuthenticationFailed
import jwt
from synergy.settings import *


def ValidateAuthenticationToken(func):
	def JWTcheck(*args, **kwargs):
		request = args[0]
		auth = get_authorization_header(request).split()
		if not auth or auth[0].lower() != b'bearer':
			raise AuthenticationFailed({"success": "0", "message": "Please provide token"})
		if len(auth) == 1:
			raise AuthenticationFailed({"success": "0", "message": "Please provide token"})
		elif len(auth) > 2:
			raise AuthenticationFailed({"success": "0", "message": "Please provide token"})
		try:
			token = auth[1]
			if token == "null":
				raise AuthenticationFailed({"success": "0", "message": "Invalid token header"})
			token = token.decode("utf-8")
			payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
			user_id = payload['user_id']
			user = User.objects.get(id=int(user_id))
			kwargs['user'] = user
		except UnicodeError:
			raise AuthenticationFailed({"success": "3", "message": "Invalid token"})
		except jwt.ExpiredSignatureError or jwt.DecodeError or jwt.InvalidTokenError:
			raise AuthenticationFailed({"success": "4", "message": "Incorrect Credentials/ Token Expired"})
		return func(*args, **kwargs)

	return JWTcheck
