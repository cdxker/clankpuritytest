from django.http import HttpResponse

from .models import MetricsSnapshot


DEFAULT_SNAPSHOT = {
    "total_traces": 118,
    "successful_traces": 118,
    "failed_traces": 0,
    "total_agent_text_words": 107368,
    "total_human_text_words": 48957,
    "total_human_messages": 708,
    "total_session_duration_ms": 626314000,
    "average_session_duration_ms": 5307000,
    "median_session_duration_ms": 0,
    "longest_session_duration_ms": 275412000,
    "shortest_session_duration_ms": 0,
}


def home(request):
    snapshot = MetricsSnapshot.objects.order_by("-created_at").first()
    if snapshot is None:
        MetricsSnapshot.objects.create(**DEFAULT_SNAPSHOT)

    return HttpResponse("<h1>Hello world</h1>")
