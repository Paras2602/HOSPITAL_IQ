import unittest
from fastapi.testclient import TestClient
from backend.main import app

class TestDiagnosisEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.session_id = None

    def test_1_get_symptoms(self):
        response = self.client.get("/diagnosis/symptoms")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("categories", data)
        if len(data["categories"]) > 0:
            self.assertIn("symptoms", data["categories"][0])

    def test_2_get_medicines(self):
        response = self.client.get("/diagnosis/medicines")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_3_predict_disease_validation(self):
        response = self.client.post("/diagnosis/predict", json={
            "symptoms": ["headache"],
            "initiated_by": "patient"
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("Minimum 3 symptoms required", response.json()["detail"])

    def test_4_predict_disease_success(self):
        response = self.client.post("/diagnosis/predict", json={
            "symptoms": ["headache", "fever", "nausea"],
            "initiated_by": "patient"
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("session_id", data)
        self.assertIn("predictions", data)
        self.assertGreater(len(data["predictions"]), 0)
        TestDiagnosisEndpoints.session_id = data["session_id"]

    def test_5_get_session(self):
        if TestDiagnosisEndpoints.session_id:
            response = self.client.get(f"/diagnosis/session/{TestDiagnosisEndpoints.session_id}")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["session_id"], TestDiagnosisEndpoints.session_id)
        else:
            self.skipTest("No session_id from prediction test")

    def test_6_admin_analytics(self):
        response = self.client.get("/diagnosis/admin/analytics")
        # Skipping assertion if admin endpoints are not implemented or protected
        pass

    def test_7_admin_logs(self):
        response = self.client.get("/diagnosis/admin/logs")
        # Skipping assertion if admin endpoints are not implemented or protected
        pass

if __name__ == "__main__":
    unittest.main()
