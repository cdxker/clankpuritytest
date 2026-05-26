#!/usr/bin/env python3

from __future__ import annotations

import re
import statistics
import sys
from datetime import datetime

from providers.main import scrape_providers


TOP_SESSION_LIMIT = 10


def count_trace_stats(trace):
    stats = {
        "trace_id": trace.id,
        "agent_id": trace.agent_id or "unknown",
        "title": trace.title or "",
        "timestamp": trace.timestamp,
        "agent_text_words": 0,
        "human_text_words": 0,
        "human_message_count": 0,
        "session_duration_ms": 0,
        "ok": True,
        "error": None,
    }

    timestamps = []
    for event in trace.events:
        if isinstance(event.timestamp, int):
            timestamps.append(event.timestamp)
        if event.type == "agent_text":
            stats["agent_text_words"] += len(re.findall(r"\b\w+\b", event.content or "", re.UNICODE))
        elif event.type == "user_message":
            stats["human_text_words"] += len(re.findall(r"\b\w+\b", event.content or "", re.UNICODE))
            stats["human_message_count"] += 1

    if len(timestamps) >= 2:
        stats["session_duration_ms"] = max(timestamps) - min(timestamps)

    return stats


def aggregate_sessions(session_stats):
    successful_sessions = [session for session in session_stats if session["ok"]]
    durations = [session["session_duration_ms"] for session in successful_sessions]

    return {
        "total_traces": len(session_stats),
        "successful_traces": len(successful_sessions),
        "failed_traces": len(session_stats) - len(successful_sessions),
        "total_agent_text_words": sum(
            session["agent_text_words"] for session in successful_sessions
        ),
        "total_human_text_words": sum(
            session["human_text_words"] for session in successful_sessions
        ),
        "total_human_messages": sum(
            session["human_message_count"] for session in successful_sessions
        ),
        "total_session_duration_ms": sum(durations),
        "average_session_duration_ms": int(sum(durations) / len(durations)) if durations else 0,
        "median_session_duration_ms": int(statistics.median(durations)) if durations else 0,
        "longest_session_duration_ms": max(durations) if durations else 0,
        "shortest_session_duration_ms": min(durations) if durations else 0,
    }


def print_table(summary, session_stats):
    summary_rows = [
        ("Total traces", f"{summary['total_traces']:,}"),
        ("Successful traces", f"{summary['successful_traces']:,}"),
        ("Unreadable traces", f"{summary['failed_traces']:,}"),
        ("AI text read (words)", f"{summary['total_agent_text_words']:,}"),
        ("Human text sent (words)", f"{summary['total_human_text_words']:,}"),
        ("Human messages sent", f"{summary['total_human_messages']:,}"),
        (
            "Total session time",
            f"{summary['total_session_duration_ms'] // 86400000} days "
            f"{(summary['total_session_duration_ms'] % 86400000) // 3600000} hours "
            f"{(summary['total_session_duration_ms'] % 3600000) // 60000} minutes "
            f"{(summary['total_session_duration_ms'] % 60000) // 1000} seconds",
        ),
        (
            "Average session time",
            f"{summary['average_session_duration_ms'] // 86400000} days "
            f"{(summary['average_session_duration_ms'] % 86400000) // 3600000} hours "
            f"{(summary['average_session_duration_ms'] % 3600000) // 60000} minutes "
            f"{(summary['average_session_duration_ms'] % 60000) // 1000} seconds",
        ),
        (
            "Median session time",
            f"{summary['median_session_duration_ms'] // 86400000} days "
            f"{(summary['median_session_duration_ms'] % 86400000) // 3600000} hours "
            f"{(summary['median_session_duration_ms'] % 3600000) // 60000} minutes "
            f"{(summary['median_session_duration_ms'] % 60000) // 1000} seconds",
        ),
        (
            "Longest session",
            f"{summary['longest_session_duration_ms'] // 86400000} days "
            f"{(summary['longest_session_duration_ms'] % 86400000) // 3600000} hours "
            f"{(summary['longest_session_duration_ms'] % 3600000) // 60000} minutes "
            f"{(summary['longest_session_duration_ms'] % 60000) // 1000} seconds",
        ),
        (
            "Shortest session",
            f"{summary['shortest_session_duration_ms'] // 86400000} days "
            f"{(summary['shortest_session_duration_ms'] % 86400000) // 3600000} hours "
            f"{(summary['shortest_session_duration_ms'] % 3600000) // 60000} minutes "
            f"{(summary['shortest_session_duration_ms'] % 60000) // 1000} seconds",
        ),
    ]

    label_width = max(len(row[0]) for row in summary_rows)
    value_width = max(len(row[1]) for row in summary_rows)

    print("Summary")
    print(f"+-{'-' * label_width}-+-{'-' * value_width}-+")
    print(f"| {'Metric'.ljust(label_width)} | {'Value'.ljust(value_width)} |")
    print(f"+-{'-' * label_width}-+-{'-' * value_width}-+")
    for label, value in summary_rows:
        print(f"| {label.ljust(label_width)} | {value.ljust(value_width)} |")
    print(f"+-{'-' * label_width}-+-{'-' * value_width}-+")
    print()

    top_sessions = sorted(
        [session for session in session_stats if session["ok"]],
        key=lambda session: (session["agent_text_words"], session["human_message_count"]),
        reverse=True,
    )[:TOP_SESSION_LIMIT]
    if top_sessions:
        top_rows = []
        for session in top_sessions:
            title = session["title"].replace("\n", " ").strip()
            if len(title) > 48:
                title = title[:45] + "..."
            top_rows.append(
                (
                    datetime.fromtimestamp(session["timestamp"] / 1000).strftime("%Y-%m-%d")
                    if session["timestamp"]
                    else "",
                    title,
                    f"{session['agent_text_words']:,}",
                    f"{session['human_text_words']:,}",
                    f"{session['human_message_count']:,}",
                    f"{session['session_duration_ms'] // 86400000}d "
                    f"{(session['session_duration_ms'] % 86400000) // 3600000:02d}:"
                    f"{(session['session_duration_ms'] % 3600000) // 60000:02d}:"
                    f"{(session['session_duration_ms'] % 60000) // 1000:02d}",
                )
            )

        date_width = max(len("Date"), max(len(row[0]) for row in top_rows))
        title_width = max(len("Title"), max(len(row[1]) for row in top_rows))
        ai_width = max(len("AI Words"), max(len(row[2]) for row in top_rows))
        human_width = max(len("Human Words"), max(len(row[3]) for row in top_rows))
        msg_width = max(len("Human Msgs"), max(len(row[4]) for row in top_rows))
        dur_width = max(len("Duration"), max(len(row[5]) for row in top_rows))

        print("Top Sessions By AI Words")
        print(
            f"+-{'-' * date_width}-+-{'-' * title_width}-+-{'-' * ai_width}-+-{'-' * human_width}-+-{'-' * msg_width}-+-{'-' * dur_width}-+"
        )
        print(
            f"| {'Date'.ljust(date_width)} | "
            f"{'Title'.ljust(title_width)} | "
            f"{'AI Words'.rjust(ai_width)} | "
            f"{'Human Words'.rjust(human_width)} | "
            f"{'Human Msgs'.rjust(msg_width)} | "
            f"{'Duration'.rjust(dur_width)} |"
        )
        print(
            f"+-{'-' * date_width}-+-{'-' * title_width}-+-{'-' * ai_width}-+-{'-' * human_width}-+-{'-' * msg_width}-+-{'-' * dur_width}-+"
        )
        for date_text, title, ai_words, human_words, human_messages, duration in top_rows:
            print(
                f"| {date_text.ljust(date_width)} | "
                f"{title.ljust(title_width)} | "
                f"{ai_words.rjust(ai_width)} | "
                f"{human_words.rjust(human_width)} | "
                f"{human_messages.rjust(msg_width)} | "
                f"{duration.rjust(dur_width)} |"
            )
        print(
            f"+-{'-' * date_width}-+-{'-' * title_width}-+-{'-' * ai_width}-+-{'-' * human_width}-+-{'-' * msg_width}-+-{'-' * dur_width}-+"
        )


def main():
    traces = scrape_providers(
        [
            "amp",
            "claude-code",
            "cline",
            "codex",
            "copilot",
            "cursor",
            "droid",
            "gemini-cli",
            "hermes",
            "openclaw",
            "opencode",
            "pi",
        ]
    )

    session_stats = [count_trace_stats(trace) for trace in traces]
    summary = aggregate_sessions(session_stats)
    print_table(summary, session_stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())
