from django.apps import AppConfig


class AiAssistantConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ai_assistant"

    def ready(self):
        from .tools import register_ai_tools

        register_ai_tools()