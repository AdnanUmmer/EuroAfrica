import time
from unittest.mock import patch
from .antispam import timing_token


def enquiry_data(**changes):
    with patch('trade.antispam.time.time', return_value=time.time() - 5):
        token = timing_token()
    result = dict(name='Visitor', email='visitor@example.org', message='A question about this category.',
                  interest='general', category='general', privacy_consent='on', form_token=token)
    result.update(changes)
    return result


def page_inline_data(obj):
    rows=list(obj.sections.all())
    result={'sections-TOTAL_FORMS':str(len(rows)), 'sections-INITIAL_FORMS':str(len(rows)), 'sections-MIN_NUM_FORMS':'0','sections-MAX_NUM_FORMS':'1000'}
    for i,row in enumerate(rows):
        for key,value in {'id':row.pk,'page':obj.pk,'heading':row.heading,'text':row.text,'order':row.order}.items():result[f'sections-{i}-{key}']=value
    return result
