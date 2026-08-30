import os
import pickle
import tempfile
import unittest

from app.ml.manager import ModelManager


class _FakeSvdModel:
    """Minimal picklable stand-in for a Surprise SVD model."""

    pass


class ModelManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.manager = ModelManager(model_dir=self.tmpdir)

    def tearDown(self):
        for filename in os.listdir(self.tmpdir):
            os.remove(os.path.join(self.tmpdir, filename))
        os.rmdir(self.tmpdir)

    def _write_pickle(self, filename: str, data):
        path = os.path.join(self.tmpdir, filename)
        with open(path, "wb") as f:
            pickle.dump(data, f)
        return path

    def test_get_svd_model_loads_on_first_call(self):
        fake_model = _FakeSvdModel()
        self._write_pickle("svd_v1.pkl", fake_model)

        model = self.manager.get_svd_model()

        self.assertIsNotNone(model)
        self.assertIsInstance(model, _FakeSvdModel)

    def test_get_svd_model_returns_cached_on_second_call(self):
        fake_model = _FakeSvdModel()
        self._write_pickle("svd_v1.pkl", fake_model)

        first = self.manager.get_svd_model()
        second = self.manager.get_svd_model()

        self.assertIs(first, second)

    def test_get_svd_model_returns_none_when_missing(self):
        model = self.manager.get_svd_model()

        self.assertIsNone(model)

    def test_get_svd_model_returns_none_on_corrupt_pickle(self):
        path = os.path.join(self.tmpdir, "svd_v1.pkl")
        with open(path, "wb") as f:
            f.write(b"not-a-pickle")

        model = self.manager.get_svd_model()

        self.assertIsNone(model)

    def test_invalidate_svd_clears_cache(self):
        first_model = _FakeSvdModel()
        self._write_pickle("svd_v1.pkl", first_model)

        first = self.manager.get_svd_model()
        self.assertIsNotNone(first)
        self.manager.invalidate_svd()

        second_model = _FakeSvdModel()
        self._write_pickle("svd_v1.pkl", second_model)

        second = self.manager.get_svd_model()

        self.assertIsNotNone(second)
        self.assertIsInstance(second, _FakeSvdModel)


if __name__ == "__main__":
    unittest.main()
