from __future__ import annotations

import threading
import time
import unittest
from urllib.parse import parse_qs, urlparse

from PyQt6.QtCore import QCoreApplication

from src.spotify.playback_service import SpotifyPlaybackService, SpotifyPlaybackServiceResult, SpotifyPlaybackServiceStatus
from src.spotify.qt_playback_runtime import SpotifyQtPlaybackRuntime
from src.spotify.web_api import SPOTIFY_API_BASE_URL, SpotifyWebApiClient
from tests.spotify.playback.test_spotify_transport_service import LegacyApi, make_service


class SeekResponse:
    def __init__(self, status=204, body=b""):
        self.status = status
        self._body = body
        self._url = ""
        self.closed = False
        self.headers = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
        return False

    def geturl(self):
        return self._url

    def getcode(self):
        return self.status

    def read(self, size=-1):
        return self._body if size is None or size < 0 else self._body[:size]

    def close(self):
        self.closed = True


class SeekRecordingUrlOpen:
    def __init__(self, response):
        self.response = response
        self.requests = []
        self.timeouts = []

    def __call__(self, request, *, timeout):
        self.requests.append(request)
        self.timeouts.append(timeout)
        self.response._url = request.full_url
        return self.response


class SeekApi(LegacyApi):
    def __init__(self, devices):
        self.devices = devices
        self.calls = []

    def get_available_devices(self, access_token):
        self.calls.append(("devices", access_token, None))
        return self.devices

    def seek_to_position(self, access_token, position_ms, *, device_id=None):
        self.calls.append(("seek", access_token, position_ms, device_id))


class CountingSession:
    def __init__(self):
        self.calls = 0

    def resolve(self):
        self.calls += 1
        raise AssertionError("Session should not be resolved.")


def ready_result():
    return SpotifyPlaybackServiceResult(status=SpotifyPlaybackServiceStatus.READY, message="ready")


class RuntimeSeekService:
    def __init__(self, positions, thread_ids):
        self.positions = positions
        self.thread_ids = thread_ids

    def seek_to_seconds(self, seconds):
        self.positions.append(seconds)
        self.thread_ids.append(threading.get_ident())
        return ready_result()


class SpotifySeekFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def wait_until(self, predicate, timeout_seconds=3.0):
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            QCoreApplication.processEvents()
            if predicate():
                return True
            time.sleep(0.005)
        QCoreApplication.processEvents()
        return bool(predicate())

    def test_web_seek_uses_put_position_and_device(self):
        response = SeekResponse()
        transport = SeekRecordingUrlOpen(response)
        client = SpotifyWebApiClient(urlopen=transport, timeout_seconds=6.5)
        self.assertIsNone(client.seek_to_position("test-access-token", 90500, device_id="desktop123"))
        self.assertEqual(len(transport.requests), 1)
        request = transport.requests[0]
        parsed = urlparse(request.full_url)
        self.assertEqual(request.get_method(), "PUT")
        self.assertEqual(parsed.scheme + "://" + parsed.netloc + parsed.path, SPOTIFY_API_BASE_URL + "/me/player/seek")
        self.assertEqual(parse_qs(parsed.query), {"position_ms": ["90500"], "device_id": ["desktop123"]})
        self.assertEqual(request.get_header("Authorization"), "Bearer test-access-token")
        self.assertEqual(request.get_header("Accept"), "application/json")
        self.assertIsNone(request.get_header("Content-type"))
        self.assertIsNone(request.data)
        self.assertEqual(transport.timeouts, [6.5])
        self.assertTrue(response.closed)

    def test_web_seek_without_device_has_only_position(self):
        response = SeekResponse()
        transport = SeekRecordingUrlOpen(response)
        client = SpotifyWebApiClient(urlopen=transport)
        client.seek_to_position("token", 0)
        query = parse_qs(urlparse(transport.requests[0].full_url).query)
        self.assertEqual(query, {"position_ms": ["0"]})

    def test_web_seek_rejects_invalid_milliseconds_before_network(self):
        transport = SeekRecordingUrlOpen(SeekResponse())
        client = SpotifyWebApiClient(urlopen=transport)
        for value in (True, -1, 1.5, "1000", None):
            with self.subTest(value=value):
                with self.assertRaises((TypeError, ValueError)):
                    client.seek_to_position("token", value)
        self.assertEqual(transport.requests, [])

    def test_service_seek_converts_seconds_and_prefers_active_device(self):
        api = SeekApi({"devices": [
            {"id": "phone123", "type": "Smartphone", "is_active": False, "is_restricted": False},
            {"id": "desktop123", "type": "Computer", "is_active": True, "is_restricted": False},
        ]})
        result = make_service(api).seek_to_seconds(90.5)
        self.assertEqual(result.status, SpotifyPlaybackServiceStatus.READY)
        self.assertEqual(api.calls, [
            ("devices", "access-token", None),
            ("seek", "access-token", 90500, "desktop123"),
        ])

    def test_service_seek_rejects_invalid_seconds_before_session(self):
        session = CountingSession()
        service = SpotifyPlaybackService(session, api_client=LegacyApi())
        for value in (True, -0.1, float("nan"), float("inf"), "not-a-number", None):
            with self.subTest(value=value):
                result = service.seek_to_seconds(value)
                self.assertEqual(result.status, SpotifyPlaybackServiceStatus.ERROR)
                self.assertEqual(result.error_code, "invalid_seek_position")
        self.assertEqual(session.calls, 0)

    def test_service_missing_seek_api_is_safe(self):
        result = make_service(LegacyApi()).seek_to_seconds(12.0)
        self.assertEqual(result.status, SpotifyPlaybackServiceStatus.ERROR)
        self.assertEqual(result.error_code, "invalid_playback_api")

    def test_runtime_seek_passes_argument_off_calling_thread(self):
        positions = []
        thread_ids = []
        caller = threading.get_ident()
        runtime = SpotifyQtPlaybackRuntime(lambda: RuntimeSeekService(positions, thread_ids))
        self.addCleanup(runtime.shutdown)
        runtime.seek_to_seconds(42.25)
        self.assertTrue(runtime.busy)
        self.assertTrue(self.wait_until(lambda: not runtime.busy))
        self.assertEqual(positions, [42.25])
        self.assertEqual(len(thread_ids), 1)
        self.assertNotEqual(thread_ids[0], caller)

    def test_runtime_seek_rejects_invalid_seconds_before_worker(self):
        positions = []
        thread_ids = []
        runtime = SpotifyQtPlaybackRuntime(lambda: RuntimeSeekService(positions, thread_ids))
        self.addCleanup(runtime.shutdown)
        for value in (True, -1, float("nan"), float("inf"), "bad", None):
            with self.subTest(value=value):
                with self.assertRaises((TypeError, ValueError)):
                    runtime.seek_to_seconds(value)
        self.assertFalse(runtime.busy)
        self.assertEqual(positions, [])
        self.assertEqual(thread_ids, [])

    def test_runtime_seek_uses_control_lifecycle_signals(self):
        positions = []
        thread_ids = []
        events = []
        runtime = SpotifyQtPlaybackRuntime(lambda: RuntimeSeekService(positions, thread_ids))
        self.addCleanup(runtime.shutdown)
        runtime.control_started.connect(lambda name: events.append(("started", name)))
        runtime.control_finished.connect(lambda name: events.append(("finished", name)))
        runtime.seek_to_seconds(0)
        self.assertTrue(self.wait_until(lambda: not runtime.busy))
        self.assertIn(("started", "seek_to_seconds"), events)
        self.assertIn(("finished", "seek_to_seconds"), events)
        self.assertEqual(positions, [0.0])


if __name__ == "__main__":
    unittest.main()
