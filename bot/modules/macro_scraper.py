"""
Macro Pulse — Couche 1 : Macro Scraper
Scrapes the Finnhub economic calendar for macro events
and calculates the Advanced Surprise Index.
"""

import sys
import os
import logging
import requests
from datetime import datetime, timedelta, timezone
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)


class MacroScraper:
    """Fetches macro-economic calendar data from Finnhub and computes
    the Advanced Surprise Index for each event."""

    FINNHUB_CALENDAR_URL = "https://finnhub.io/api/v1/calendar/economic"
    SURPRISE_CLAMP_MIN = -3.0
    SURPRISE_CLAMP_MAX = 3.0
    MOMENTUM_WINDOW = 10

    def __init__(self):
        self.api_key: str = config.FINNHUB_API_KEY
        self._surprise_history: dict[str, list[float]] = defaultdict(list)
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json"})

    # ------------------------------------------------------------------ #
    #  Public API                                                         #
    # ------------------------------------------------------------------ #

    def fetch_calendar(self, days_ahead: int = 7) -> list[dict]:
        """Fetch economic calendar events from Finnhub for the next
        *days_ahead* days.  Only high/medium impact events (impact >= 2)
        are returned.

        Returns a list of dicts with keys:
            event, country, impact, actual, estimate, previous,
            unit, timestamp
        """
        try:
            now = datetime.now(timezone.utc)
            start_date = now.strftime("%Y-%m-%d")
            end_date = (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

            params = {
                "token": self.api_key,
                "from": start_date,
                "to": end_date,
            }

            logger.info(
                "Fetching Finnhub economic calendar from %s to %s",
                start_date,
                end_date,
            )

            response = self._session.get(
                self.FINNHUB_CALENDAR_URL,
                params=params,
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()

            raw_events = data.get("economicCalendar", [])
            if not raw_events:
                raw_events = data.get("result", [])

            events: list[dict] = []
            for raw in raw_events:
                event = self._normalise_event(raw)
                if event["impact"] >= 2:
                    events.append(event)

            logger.info(
                "Fetched %d high/medium impact events out of %d total",
                len(events),
                len(raw_events),
            )
            return events

        except requests.RequestException as exc:
            logger.error("HTTP error fetching Finnhub calendar: %s", exc)
            return []
        except (ValueError, KeyError) as exc:
            logger.error("Error parsing Finnhub calendar response: %s", exc)
            return []
        except Exception as exc:
            logger.error("Unexpected error in fetch_calendar: %s", exc)
            return []

    # ------------------------------------------------------------------ #

    def calculate_surprise_index(self, event: dict) -> dict:
        """Compute the Advanced Surprise Index for a single event.

        Returns a dict with:
            surprise_score          – raw (actual-forecast)/|forecast|, clamped [-3,3]
            revision_adjusted       – surprise amplified by forecast revision
            cumulative_momentum     – running average of last 10 surprises
                                      for the same indicator category
        All values default to 0.0 when inputs are missing or invalid.
        """
        result = {
            "surprise_score": 0.0,
            "revision_adjusted": 0.0,
            "cumulative_momentum": 0.0,
        }

        try:
            actual = event.get("actual")
            forecast = event.get("estimate")
            previous = event.get("previous")

            # ── 1. Surprise Score ────────────────────────────────────
            if actual is None or forecast is None:
                return result

            actual = float(actual)
            forecast = float(forecast)

            if forecast != 0.0:
                surprise_score = (actual - forecast) / abs(forecast)
            else:
                surprise_score = 0.0

            surprise_score = max(
                self.SURPRISE_CLAMP_MIN,
                min(self.SURPRISE_CLAMP_MAX, surprise_score),
            )
            result["surprise_score"] = round(surprise_score, 6)

            # ── 2. Revision-Adjusted Surprise ────────────────────────
            if previous is not None:
                previous = float(previous)
                if previous != 0.0:
                    revision_factor = 1.0 + abs(forecast - previous) / abs(previous)
                else:
                    revision_factor = 1.0
            else:
                revision_factor = 1.0

            revision_adjusted = surprise_score * revision_factor
            result["revision_adjusted"] = round(revision_adjusted, 6)

            # ── 3. Cumulative Surprise Momentum ──────────────────────
            category = self._indicator_category(event.get("event", ""))
            self._surprise_history[category].append(surprise_score)
            # Keep only the last MOMENTUM_WINDOW entries
            if len(self._surprise_history[category]) > self.MOMENTUM_WINDOW:
                self._surprise_history[category] = self._surprise_history[category][
                    -self.MOMENTUM_WINDOW :
                ]

            history = self._surprise_history[category]
            cumulative_momentum = sum(history) / len(history) if history else 0.0
            result["cumulative_momentum"] = round(cumulative_momentum, 6)

        except (TypeError, ValueError, ZeroDivisionError) as exc:
            logger.warning("Error calculating surprise index: %s", exc)
        except Exception as exc:
            logger.error("Unexpected error in calculate_surprise_index: %s", exc)

        return result

    # ------------------------------------------------------------------ #

    def is_priority_event(self, event_name: str) -> bool:
        """Return True if *event_name* fuzzy-matches any of the
        PRIORITY_INDICATORS defined in config (case-insensitive
        substring match)."""
        if not event_name:
            return False
        try:
            name_lower = event_name.lower()
            for indicator in config.PRIORITY_INDICATORS:
                if indicator.lower() in name_lower:
                    return True
            return False
        except Exception as exc:
            logger.error("Error in is_priority_event: %s", exc)
            return False

    # ------------------------------------------------------------------ #

    def get_upcoming_events(self, minutes_ahead: int = 60) -> list[dict]:
        """Return calendar events happening within the next
        *minutes_ahead* minutes."""
        try:
            events = self.fetch_calendar(days_ahead=1)
            now = datetime.now(timezone.utc)
            cutoff = now + timedelta(minutes=minutes_ahead)

            upcoming: list[dict] = []
            for ev in events:
                ev_time = self._parse_timestamp(ev.get("timestamp"))
                if ev_time is None:
                    continue
                if now <= ev_time <= cutoff:
                    upcoming.append(ev)

            logger.info(
                "Found %d upcoming events within %d minutes",
                len(upcoming),
                minutes_ahead,
            )
            return upcoming

        except Exception as exc:
            logger.error("Error in get_upcoming_events: %s", exc)
            return []

    # ------------------------------------------------------------------ #

    def get_recent_results(self, hours_back: int = 4) -> list[dict]:
        """Return events whose actual value was published in the last
        *hours_back* hours."""
        try:
            events = self.fetch_calendar(days_ahead=1)
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(hours=hours_back)

            recent: list[dict] = []
            for ev in events:
                if ev.get("actual") is None:
                    continue
                ev_time = self._parse_timestamp(ev.get("timestamp"))
                if ev_time is None:
                    continue
                if cutoff <= ev_time <= now:
                    recent.append(ev)

            logger.info(
                "Found %d events with results in the last %d hours",
                len(recent),
                hours_back,
            )
            return recent

        except Exception as exc:
            logger.error("Error in get_recent_results: %s", exc)
            return []

    # ------------------------------------------------------------------ #

    def process_event(self, event: dict) -> dict:
        """Calculate all surprise metrics and return an enriched event
        dict ready for data_store insertion."""
        try:
            surprise = self.calculate_surprise_index(event)
            priority = self.is_priority_event(event.get("event", ""))

            enriched = {
                # Original fields
                "event": event.get("event", ""),
                "country": event.get("country", ""),
                "impact": event.get("impact", 0),
                "actual": event.get("actual"),
                "estimate": event.get("estimate"),
                "previous": event.get("previous"),
                "unit": event.get("unit", ""),
                "timestamp": event.get("timestamp", ""),
                # Surprise metrics
                "surprise_score": surprise["surprise_score"],
                "revision_adjusted": surprise["revision_adjusted"],
                "cumulative_momentum": surprise["cumulative_momentum"],
                # Meta
                "is_priority": priority,
                "indicator_category": self._indicator_category(
                    event.get("event", "")
                ),
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }
            return enriched

        except Exception as exc:
            logger.error("Error in process_event: %s", exc)
            return {
                "event": event.get("event", ""),
                "country": event.get("country", ""),
                "impact": event.get("impact", 0),
                "actual": event.get("actual"),
                "estimate": event.get("estimate"),
                "previous": event.get("previous"),
                "unit": event.get("unit", ""),
                "timestamp": event.get("timestamp", ""),
                "surprise_score": 0.0,
                "revision_adjusted": 0.0,
                "cumulative_momentum": 0.0,
                "is_priority": False,
                "indicator_category": "",
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }

    # ------------------------------------------------------------------ #
    #  Private helpers                                                    #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _normalise_event(raw: dict) -> dict:
        """Map a raw Finnhub calendar entry to our canonical schema."""
        return {
            "event": raw.get("event", ""),
            "country": raw.get("country", ""),
            "impact": int(raw.get("impact", 0)),
            "actual": raw.get("actual"),
            "estimate": raw.get("estimate"),
            "previous": raw.get("prev"),
            "unit": raw.get("unit", ""),
            "timestamp": raw.get("time", raw.get("date", "")),
        }

    @staticmethod
    def _parse_timestamp(ts) -> datetime | None:
        """Best-effort parse of a Finnhub timestamp string into a
        timezone-aware UTC datetime."""
        if ts is None:
            return None
        if isinstance(ts, datetime):
            if ts.tzinfo is None:
                return ts.replace(tzinfo=timezone.utc)
            return ts
        ts_str = str(ts).strip()
        if not ts_str:
            return None

        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(ts_str, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue

        logger.debug("Unable to parse timestamp: %s", ts_str)
        return None

    @staticmethod
    def _indicator_category(event_name: str) -> str:
        """Derive a broad category key from the event name so that
        momentum can be tracked across related indicators.

        Categories group related indicators (e.g. all CPI variants
        map to 'cpi', all PMI variants map to 'pmi').
        """
        if not event_name:
            return "other"

        name = event_name.lower()

        category_keywords = {
            "cpi": ["cpi", "consumer price"],
            "ppi": ["ppi", "producer price"],
            "gdp": ["gdp", "gross domestic"],
            "employment": [
                "payroll",
                "nfp",
                "non-farm",
                "nonfarm",
                "jobless",
                "unemployment",
                "employment",
            ],
            "interest_rate": [
                "interest rate",
                "fed fund",
                "rate decision",
                "monetary policy",
            ],
            "pmi": ["pmi", "purchasing manager"],
            "trade": ["trade balance", "exports", "imports"],
            "sentiment": [
                "consumer sentiment",
                "consumer confidence",
                "michigan",
            ],
            "pce": ["pce", "personal consumption"],
        }

        for category, keywords in category_keywords.items():
            for kw in keywords:
                if kw in name:
                    return category

        return "other"
