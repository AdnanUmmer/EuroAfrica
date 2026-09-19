import time
from unittest.mock import patch
from .antispam import timing_token


def enquiry_data(**changes):
    with patch('trade.antispam.time.time', return_value=time.time() - 5):
        token = timing_token()
    result = dict(name='Visitor', email='visitor@example.org', message='A question about this category.',
                  category='general', privacy_consent='on', form_token=token)
    result.update(changes)
    return result
