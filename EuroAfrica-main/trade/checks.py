from django.conf import settings
from django.core.checks import Warning, register, Tags


@register(Tags.security, deploy=True)
def contact_configuration(app_configs, **kwargs):
    from .antispam import turnstile_configured
    if not settings.DEBUG and not turnstile_configured():
        return [Warning('Production enquiries are closed until real Turnstile site/secret keys are configured.', id='trade.W001')]
    return []
