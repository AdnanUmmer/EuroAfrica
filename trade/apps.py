from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig

class EuroAfricaAdminConfig(AdminConfig):
    default_site = 'trade.admin_site.EuroAfricaAdminSite'

class TradeConfig(AppConfig):
    name = 'trade'
    verbose_name = 'EuroAfrica content'
    def ready(self):
        from . import signals
