import unittest
import requests
import json

class TestFlaskServer(unittest.TestCase):
    def setUp(self):
        """Set up test configuration"""
        self.base_url = 'http://localhost:3000'
        self.test_payloads = [
            {
                "username": "test_user1",
                "query": "What are your business hours?"
            },
            {
                "username": "test_user2",
                "query": "Tell me about your return policy."
            },
            {
                "username": "test_user3",
                "query": "How can I contact customer service?"
            }
        ]

    def test_query_endpoint(self):
        """Test the /query endpoint with different payloads"""
        for payload in self.test_payloads:
            # Send request to the Flask server
            response = requests.post(
                f"{self.base_url}/query",
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            
            # Print detailed test information
            print(f"\nTesting payload: {json.dumps(payload, indent=2)}")
            print(f"Response status code: {response.status_code}")
            print(f"Response content: {response.text}")
            
            # Basic assertions to verify response structure
            self.assertEqual(response.status_code, 200)
            self.assertIn('response', response.json())
            self.assertTrue(isinstance(response.json()['response'], str))

if __name__ == '__main__':
    unittest.main(verbosity=2)