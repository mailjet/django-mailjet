from email.utils import parseaddr

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import sanitize_address, DEFAULT_ATTACHMENT_MIME_TYPE
from .messageFormat.messageFormatStrategy import *
from .messageFormat.messageFormatV3 import *
from .messageFormat.messageFormatV3_1 import *

from mailjet_rest import Client

from .exceptions import MailjetError, MailjetAPIError


class MailjetBackend(BaseEmailBackend):
    """
    Mailjet email backend for Django
    """

    def __init__(self, fail_silently=False, *args, **kwargs):
        super(MailjetBackend, self).__init__(fail_silently=fail_silently, *args, **kwargs)

        try:
            self._api_key = settings.MAILJET_API_KEY
            self._api_secret = settings.MAILJET_API_SECRET
        except AttributeError:
            if not fail_silently:
                raise ImproperlyConfigured("Please set MAILJET_API_KEY and MAILJET_API_SECRET in settings.py to use Mailjet")

        self.client = Client(auth=(self._api_key, self._api_secret))
        if settings.SEND_API_VERSION=='v3.1':
            self.messageFormater = MessageFormatStrategy(MessageFormatV31)
        else:
            self.messageFormater = MessageFormatStrategy(MessageFormatV3)


    def open(self):
        pass

    def close(self):
        pass



    def _send(self, message):
        message.mailjet_response = None
        if not message.recipients():
            return False

        try:
            payload = self.messageFormater.build_send_payload(message)
            response = self.post_to_mailjet(payload, message)

            message.mailjet_response = self.parse_response(response, payload, message)

        except MailjetError:
            if not self.fail_silently:
                raise
            return False

        return True

    def send_messages(self, email_messages):
        if not email_messages:
            return

        num_sent = 0
        for message in email_messages:
            if self._send(message):
                num_sent += 1

        return num_sent

    def post_to_mailjet(self, payload, message):
        response = self.client.send.create(data=payload)
        if response.status_code != 200:
            raise MailjetAPIError(email_message=message, payload=payload, response=response)
        return response

    def parse_response(self, response, payload, message):
        try:
            return response.json()
        except ValueError:
            raise MailjetAPIError("Invalid JSON in Mailjet API response",
                                  email_message=message, payload=payload, response=response)
