import pytest
import requests
import logging

# Configure logging to show warnings and errors
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Global constants
BASE_URL = "https://decision-delivery-internal.stage.ideasrms.com"
CLIENT_CODE = "client1234"
PROPERTY_CODE = "property123"

def test_decision_delivery_process():
    """Test the decision delivery process through a series of API calls.

    This test will create a decision delivery request, post daily bars,
    update the request, and retrieve the status of the request.
    """
    correlation_id = None

    # Step 1: Create a Decision Delivery Request
    try:
        # Fixed the string formatting for the URL
        create_request_url = f"{BASE_URL}/api/v1/decisiondelivery/requests/{CLIENT_CODE}/{PROPERTY_CODE}"
        payload = {
            "decisionUploadType": "FULL",
            "decisionType": "Approval",
            "clientEnvironmentUrl": "https://abc.com",
            "vendorId": "1234"
        }
        response = requests.post(create_request_url, json=payload, timeout=10)
        response.raise_for_status()  # Raise an error for bad responses
        correlation_id = response.json().get("correlationId")
        assert correlation_id is not None, "Correlation ID should not be None"
        logger.info(f"Created decision delivery request with correlation ID: {correlation_id}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to create decision delivery request: {e}")
        pytest.fail("Step 1 failed")

    # Step 2: Post Daily Bars
    try:
        # Fixed the string formatting for the URL and used the correct correlation_id
        post_bars_url = f"{BASE_URL}/api/v1/decisiondelivery/dailybars/{CLIENT_CODE}/{PROPERTY_CODE}/{correlation_id}"
        daily_bars_payload = [
            {
                "occupancyDate": "2020-11-20",
                "rateCode": "BAR",
                "currencyCode": "USD",
                "roomTypeCode": "NSK",
                "singleRate": 100,
                "doubleRate": 120,
                "additionalAdultRate": 30,
                "additionalChildRate": 30,
                "taxExcluded": True
            },
            {
                "occupancyDate": "2020-11-21",
                "rateCode": "BAR",
                "currencyCode": "USD",
                "roomTypeCode": "NSK",
                "singleRate": 100,
                "doubleRate": 120,
                "additionalAdultRate": 30,
                "additionalChildRate": 30,
                "taxExcluded": True
            }
        ]
        response = requests.post(post_bars_url, json=daily_bars_payload, timeout=10)
        response.raise_for_status()
        logger.info("Posted daily bars successfully.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to post daily bars: {e}")
        pytest.fail("Step 2 failed")

    # Step 3: Update Decision Delivery Request
    try:
        # Fixed the string formatting for the URL and used the correct correlation_id
        update_request_url = f"{BASE_URL}/api/v1/decisiondelivery/requests/{CLIENT_CODE}/{PROPERTY_CODE}/{correlation_id}"
        response = requests.patch(update_request_url, timeout=10)
        assert response.status_code == 204, "Expected status code 204 for update"
        logger.info("Updated decision delivery request successfully.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to update decision delivery request: {e}")
        pytest.fail("Step 3 failed")

    # Step 4: Get Decision Delivery Status
    try:
        # Fixed the string formatting for the URL and used the correct correlation_id
        get_status_url = f"{BASE_URL}/api/v1/decisiondelivery/requests/{CLIENT_CODE}/{PROPERTY_CODE}/{correlation_id}"
        response = requests.get(get_status_url, timeout=10)
        response.raise_for_status()
        request_status = response.json().get("requestStatus")
        logger.info(f"Request status: {request_status}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get decision delivery status: {e}")
        pytest.fail("Step 4 failed")

if __name__ == "__main__":
    pytest.main()