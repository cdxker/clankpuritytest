from django.contrib import admin

from .models import MetricsSnapshot


@admin.register(MetricsSnapshot)
class MetricsSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "total_traces",
        "successful_traces",
        "total_agent_text_words",
        "total_human_text_words",
        "created_at",
    )

# Register your models here.
