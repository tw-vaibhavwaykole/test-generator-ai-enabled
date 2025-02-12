import requests
import pytest

BASE_URL = "http://petstore.swagger.io/v2"

def create_user(user_data):
    """Create a new user."""
    response = requests.post(f"{BASE_URL}/user", json=user_data)
    response.raise_for_status()
    return response.json()

def login_user(username, password):
    """Log in a user and return the response."""
    response = requests.get(f"{BASE_URL}/user/login", params={"username": username, "password": password})
    response.raise_for_status()
    return response.text

def add_new_pet(pet_data):
    """Add a new pet to the store."""
    response = requests.post(f"{BASE_URL}/pet", json=pet_data)
    response.raise_for_status()
    return response.json()

def upload_pet_image(pet_id, image_data):
    """Upload an image for a pet."""
    response = requests.post(f"{BASE_URL}/pet/{pet_id}/uploadImage", files=image_data)
    response.raise_for_status()
    return response.json()

def find_pets_by_status(status):
    """Find pets by their status."""
    response = requests.get(f"{BASE_URL}/pet/findByStatus", params={"status": status})
    response.raise_for_status()
    return response.json()

def place_order(order_data):
    """Place a new order."""
    response = requests.post(f"{BASE_URL}/store/order", json=order_data)
    response.raise_for_status()
    return response.json()

def get_order_details(order_id):
    """Retrieve details of an order."""
    response = requests.get(f"{BASE_URL}/store/order/{order_id}")
    response.raise_for_status()
    return response.json()

def logout_user():
    """Log out the user."""
    response = requests.get(f"{BASE_URL}/user/logout")
    response.raise_for_status()
    return response.status_code

def test_end_to_end_pet_adoption_and_order_process():
    """Test the end-to-end pet adoption and order process."""
    
    # Step 1: User Account Creation
    user_data = {
        "id": 0,
        "username": "testuser",
        "firstName": "Test",
        "lastName": "User",
        "email": "testuser@example.com",
        "password": "password",
        "phone": "123-456-7890",
        "userStatus": 1
    }
    create_user(user_data)

    # Step 2: User Login
    login_response = login_user("testuser", "password")
    assert "logged in" in login_response

    # Step 3: Adding a New Pet
    pet_data = {
        "id": 0,
        "category": {"id": 1, "name": "Dogs"},
        "name": "Buddy",
        "photoUrls": ["http://example.com/buddy.jpg"],
        "tags": [{"id": 1, "name": "friendly"}],
        "status": "available"
    }
    new_pet = add_new_pet(pet_data)
    assert new_pet['name'] == "Buddy"

    # Step 4: Uploading a Pet Image
    pet_id = new_pet['id']
    image_data = {'file': open('path/to/image.jpg', 'rb')}
    upload_response = upload_pet_image(pet_id, image_data)
    assert upload_response['code'] == 200

    # Step 5: Finding Pets by Status
    pets = find_pets_by_status("available")
    assert len(pets) > 0

    # Step 6: Placing an Order
    order_data = {
        "id": 0,
        "petId": pet_id,
        "quantity": 1,
        "shipDate": "2023-10-01T00:00:00.000Z",
        "status": "placed",
        "complete": True
    }
    order = place_order(order_data)
    assert order['status'] == "placed"

    # Step 7: Retrieving Order Details
    order_id = order['id']
    order_details = get_order_details(order_id)
    assert order_details['id'] == order_id

    # Step 8: User Logout
    logout_status = logout_user()
    assert logout_status == 200

if __name__ == "__main__":
    pytest.main()