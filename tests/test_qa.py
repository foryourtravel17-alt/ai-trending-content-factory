import unittest
from agents.qa import validate

class QATests(unittest.TestCase):
    def valid(self):
        return {
            "signal_id": "test-long", "symbol": "TEST", "direction": "LONG",
            "entry": 100.0, "stop_loss": 96.0, "tp1": 104.0,
            "tp2": 106.0, "tp3": 108.0, "rr_tp2": 1.5,
            "as_of": "2026-01-01T00:00:00+00:00",
        }
    def test_accepts_valid_rr(self):
        ok, reason = validate(self.valid(), {"signals": {}})
        self.assertTrue(ok, reason)
    def test_rejects_low_rr(self):
        signal = self.valid()
        signal.update(tp2=105.0, rr_tp2=1.25)
        ok, _ = validate(signal, {"signals": {}})
        self.assertFalse(ok)
    def test_rejects_inconsistent_rr(self):
        signal = self.valid()
        signal["rr_tp2"] = 2.5
        ok, reason = validate(signal, {"signals": {}})
        self.assertFalse(ok)
        self.assertIn("does not match", reason)
    def test_rejects_duplicate(self):
        signal = self.valid()
        ok, _ = validate(signal, {"signals": {signal["signal_id"]: signal}})
        self.assertFalse(ok)
    def test_rejects_bad_long_order(self):
        signal = self.valid()
        signal["stop_loss"] = 101.0
        ok, _ = validate(signal, {"signals": {}})
        self.assertFalse(ok)
if __name__ == "__main__":
    unittest.main()
