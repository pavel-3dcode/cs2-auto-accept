import queue
import threading
import unittest
from unittest.mock import Mock

from accept import AutoAcceptApp, find_color, screen_position, validate_area


class Image:
    size = (11, 11)

    def __init__(self, point=None):
        self.point = point

    def getpixel(self, point):
        return (19, 60, 8) if point == self.point else (0, 0, 0)


class DetectionTests(unittest.TestCase):
    def test_finds_sampled_pixel(self):
        self.assertEqual(find_color(Image((5, 10)), (19, 60, 8)), (5, 10))

    def test_no_match(self):
        self.assertIsNone(find_color(Image(), (19, 60, 8)))

    def test_step_can_skip_pixel(self):
        self.assertIsNone(find_color(Image((1, 1)), (19, 60, 8)))
        self.assertEqual(find_color(Image((1, 1)), (19, 60, 8), 1), (1, 1))

    def test_invalid_step(self):
        with self.assertRaises(ValueError):
            find_color(Image(), (19, 60, 8), 0)

    def test_region_offset(self):
        self.assertEqual(screen_position((5, 10), (100, 200, 11, 11)), (105, 210))

    def test_region_boundaries(self):
        validate_area((0, 0, 1280, 1024), (1280, 1024))
        for area in [(0, 0, 1280, 1024), (-1, 0, 1, 1), (0, 0, 0, 1)]:
            with self.assertRaises(ValueError):
                validate_area(area, (1280, 720))


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.app = AutoAcceptApp.__new__(AutoAcceptApp)
        self.app.events = queue.Queue()
        self.app.stop_event = threading.Event()
        self.app.automation = Mock()
        self.app.automation.FailSafeException = type("FailSafeException", (Exception,), {})

    def test_single_click_and_stop(self):
        self.app.automation.screenshot.return_value = Image((5, 10))
        self.app.search_loop()
        self.app.automation.click.assert_called_once_with(5, 10)
        self.assertTrue(self.app.stop_event.is_set())

    def test_stopped_worker_does_not_click(self):
        self.app.stop_event.set()
        self.app.search_loop()
        self.app.automation.screenshot.assert_not_called()
        self.app.automation.click.assert_not_called()

    def test_capture_error_stops_worker(self):
        self.app.automation.screenshot.side_effect = OSError("capture failed")
        self.app.search_loop()
        self.assertIn("capture failed", self.app.events.get_nowait())
        self.assertTrue(self.app.stop_event.is_set())
        self.app.automation.click.assert_not_called()

    def test_fail_safe_stops_worker(self):
        self.app.automation.screenshot.return_value = Image((5, 10))
        self.app.automation.click.side_effect = self.app.automation.FailSafeException()
        self.app.search_loop()
        self.assertIn("Аварийная остановка", self.app.events.get_nowait())
        self.assertTrue(self.app.stop_event.is_set())


if __name__ == "__main__":
    unittest.main()
