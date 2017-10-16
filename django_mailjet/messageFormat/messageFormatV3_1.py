from .messageFormatStrategy import *
import mimetypes
from django.core.mail.message import sanitize_address, DEFAULT_ATTACHMENT_MIME_TYPE
from email.mime.base import MIMEBase
from base64 import b64encode
from email.utils import parseaddr
from django.conf import settings
#add init.py


class MessageFormatV31(MessageFormatStrategy):

    def build_send_payload(self, message):
        msg_payload = self._build_standard_message_dict(message)
        self._add_mailjet_options(message, msg_payload)

        if getattr(message, 'alternatives', None):

            self._add_alternatives(message, msg_payload)

        self._add_attachments(message, msg_payload)

        return msg_payload

    def _build_standard_message_dict(self, message):
        msg_payload = {}
        msg = {}

        if len(message.subject):
            msg['Subject'] = message.subject

        if len(message.body):
            msg['TextPart'] = message.body

        sender = sanitize_address(message.from_email, message.encoding)
        from_name, from_email = parseaddr(sender)

        From={}
        From['Email'] = from_email
        From['Name'] = from_name
        msg['From']=From

        if message.cc:
            CcArr={}
            CcArr= ', '.join([sanitize_address(addr, message.encoding) for addr in message.cc])
            msg['Cc'] = CcArr

        if message.bcc:
            BccArr = {}
            BccArr= ', '.join([sanitize_address(addr, message.encoding) for addr in message.bcc])
            msg['Bcc'] = BccArr
        #No longer supported in v3.1

            msg['To'] = ', '.join([sanitize_address(addr, message.encoding) for addr in message.to])

        if message.reply_to:
            reply_to = [sanitize_address(addr, message.encoding) for addr in message.reply_to]
            msg['ReplyTo'] = {'ReplyTo': ', '.join(reply_to)}

        if message.extra_headers:
            msg['Headers'] = msg_payload.get('Headers', {})
            msg['Headers'].update(message.extra_headers)

        msg_payload['Messages'] = [msg];
        return msg_payload

    def _add_mailjet_options(self, message, msg_payload):
        mailjet_attrs = {
            'template_id': 'TemplateID',
            'template_language': 'TemplateLanguage',
            'template_error_reporting': 'TemplateErrorReporting',
            'template_error_deliver': 'TemplateErrorDeliver',
            'mailjet_priority': 'Priority',
            'campaign': 'CustomCampaign',
            'deduplicate_campaign': 'DeduplicateCampaign',
            'mailjet_track_open':'TrackOpens',
            'mailjet_track_click':'TrackClicks',
            'custom_id': 'CustomID',
            'event_payload': 'EventPayload',
            'mailjet_monitoring_category':'MonitoringCategory',
        }

        for attr, mj_attr in mailjet_attrs.items():
            if hasattr(message, attr):
                msg_payload[mj_attr] = getattr(message, attr)

        if hasattr(message, 'template_vars'):
            msg_payload['Varibales'] = message.template_vars

    def _add_alternatives(self, message, msg_payload):
        for alt in message.alternatives:
            content, mimetype = alt
            if mimetype == 'text/html':
                msg_payload['HTMLPart'] = content
                break

    def _add_attachments(self, message, msg_payload):
        if not message.attachments:
            return

        str_encoding = message.encoding or settings.DEFAULT_CHARSET
        mj_attachments = []
        mj_inline_attachments = []
        for attachment in message.attachments:
            att_dict, is_inline = self._make_attachment(attachment, str_encoding)
            if is_inline:
                mj_inline_attachments.append(att_dict)
            else:
                mj_attachments.append(att_dict)

        if mj_attachments:
            msg_payload['Attachments'] = mj_attachments
        if mj_inline_attachments:
            msg_payload['InlinedAttachments'] = mj_inline_attachments

    def _make_attachment(self, attachment, str_encoding=None):
        """Returns EmailMessage.attachments item formatted for sending with Mailjet

        Returns mailjet_dict, is_inline_image
        """
        is_inline_image = False
        if isinstance(attachment, MIMEBase):
            name = attachment.get_filename()
            content = attachment.get_payload(decode=True)
            mimetype = attachment.get_content_type()

            if attachment.get_content_maintype() == 'image' and attachment['Content-ID'] is not None:
                is_inline_image = True
                name = attachment['Content-ID']
        else:
            (name, content, mimetype) = attachment

        # Guess missing mimetype from filename, borrowed from
        # django.core.mail.EmailMessage._create_attachment()
        if mimetype is None and name is not None:
            mimetype, _ = mimetypes.guess_type(name)
        if mimetype is None:
            mimetype = DEFAULT_ATTACHMENT_MIME_TYPE

        try:
            # noinspection PyUnresolvedReferences
            if isinstance(content, unicode):
                # Python 2.x unicode string
                content = content.encode(str_encoding)
        except NameError:
            # Python 3 doesn't differentiate between strings and unicode
            # Convert python3 unicode str to bytes attachment:
            if isinstance(content, str):
                content = content.encode(str_encoding)

        content_b64 = b64encode(content)

        mj_attachment = {
            'ContentType': mimetype,
            'Filename': name or '',
            'Base64Content': content_b64.decode('ascii'),
        }
        if is_inline_image:
            mj_attachment['ContentID']=name

        return mj_attachment, is_inline_image

    def _parse_recipients(self, message, recipients):
        rcpts = []
        recipient_vars = getattr(message, 'recipient_vars', {})

        for addr in recipients:
            rcpt = {}
            to_name, to_email = parseaddr(sanitize_address(addr, message.encoding))

            if to_name:
                rcpt['Name'] = to_name
            if to_email:
                rcpt['Email'] = to_email

            if recipient_vars.get(addr):
                rcpt['Variables'] = recipient_vars.get(addr)

            rcpts.append(rcpt)
        return rcpts
