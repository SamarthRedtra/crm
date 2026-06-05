from crm.api.redtra.fcm import is_darify_firebase_enabled
from raven.raven.doctype.raven_push_token.raven_push_token import RavenPushToken


class CustomRavenPushToken(RavenPushToken):
	def after_insert(self):
		if is_darify_firebase_enabled():
			return
		super().after_insert()

	def on_trash(self):
		if is_darify_firebase_enabled():
			return
		super().on_trash()
