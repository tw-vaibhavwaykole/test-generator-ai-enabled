import requests
import pytest

# Static details
base_url = "https://decision-delivery-internal.stage.ideasrms.com"
client_environment_url = "https://abc.com"
client_code = "CLIENT123"
property_code = "PROP456"

# Test case details
endpoint = f"/api/v1/decisiondelivery/requests/{client_code}/{property_code}"
method = "POST"
timeout = 5

# Merged payload, headers, and query parameters
merged_payload = {
    "decisionUploadType": "FULL",
    "decisionType": "Approval",
    "clientEnvironmentUrl": client_environment_url,
    "vendorId": "default"  # Replacing <value> with a default
}

merged_headers = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

merged_query_params = {}

def log_response(response):
    print("Response Status Code:", response.status_code)
    print("Response Content:", response.json())

def test_setup_decision_delivery_request():
    print("Starting test: SetupDecisionDeliveryRequestTest")
    url = base_url + endpoint
    try:
        response = requests.post(url, json=merged_payload, headers=merged_headers, params=merged_query_params, timeout=timeout)
        assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}"
        log_response(response)
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Request failed: {e}")
    print("Test ended: SetupDecisionDeliveryRequestTest")

if __name__ == "__main__":
    pytest.main([__file__])