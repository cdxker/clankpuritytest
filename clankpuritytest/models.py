from django.db import models


class MetricsSnapshot(models.Model):
    total_traces = models.PositiveIntegerField()
    successful_traces = models.PositiveIntegerField()
    failed_traces = models.PositiveIntegerField()
    total_agent_text_words = models.PositiveIntegerField()
    total_human_text_words = models.PositiveIntegerField()
    total_human_messages = models.PositiveIntegerField()
    total_session_duration_ms = models.PositiveBigIntegerField()
    average_session_duration_ms = models.PositiveBigIntegerField()
    median_session_duration_ms = models.PositiveBigIntegerField()
    longest_session_duration_ms = models.PositiveBigIntegerField()
    shortest_session_duration_ms = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Metrics snapshot #{self.pk or 'new'}"
