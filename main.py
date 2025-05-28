import os
import requests
import time
import logging
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Load environment variables from .env file
# This block ensures configuration values are loaded and logs if there's an issue.
try:
    load_dotenv()
except Exception as e:
    print(f"Error loading .env file: {e}")

# Configure logging with detailed format including level and time
# All log messages are written to 'order_status_updater.log'
logging.basicConfig(
    filename='order_status_updater.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# Define domains and load API keys from environment variables.
# Each domain is represented as a dictionary with keys 'subdomain' and 'api_key'.
DOMAINS = [
    {"subdomain": "centricity-test-store",
     "api_key": os.getenv("CENTRICITY_TEST_STORE_API_KEY")},
    {"subdomain": "bonappetit",
     "api_key": os.getenv("BON_APPETIT_API_KEY")},
    {"subdomain": "amentuminventory",
     "api_key": os.getenv("AMENTUM_INVENTORY_API_KEY")},
]

# API_PATH is the constant endpoint for order-related API calls.
API_PATH = "/api/v2.6.1/orders"


def log_and_print(message, level="info"):
    """
    Logs a message and prints it to stdout.

    Args:
        message (str): The message to log.
        level (str): The logging level, e.g., "info", "warning", "error".

    The function tries to use the logging library at the desired level. If an error occurs
    during logging, it writes an error message to the log. The message is then printed to
    stdout for immediate feedback.
    """
    try:
        getattr(logging, level)(message)
    except Exception as e:
        logging.error(f"Error logging message: {message} - {e}")
    print(message)


def fetch_orders(subdomain, api_key, created_at_from, created_at_to):
    """
    Fetch orders from the API for a specified subdomain within a defined time range.

    Args:
        subdomain (str): The subdomain for the store.
        api_key (str): API key for authentication.
        created_at_from (str): ISO formatted starting timestamp for order creation.
        created_at_to (str): ISO formatted ending timestamp for order creation.

    Returns:
        list: List of orders returned by the API, or an empty list if an error occurs.

    The function constructs the API URL, sets the required query parameters, and performs a GET 
    request. It logs the request and response details. If a request exception or an unexpected 
    error occurs, it logs the error and returns an empty list.
    """
    # Build complete API endpoint URL
    url = f"https://{subdomain}.mybrightsites.com{API_PATH}?token={api_key}"
    params = {"created_at_from": created_at_from,
              "created_at_to": created_at_to}
    log_and_print(f"Sending GET request to {url} with params: {params}")

    try:
        response = requests.get(url, params=params, timeout=30)
        log_and_print(
            f"Response from {url}: {response.status_code} - {response.text}")
        # Trigger an exception for HTTP error responses.
        response.raise_for_status()
        # Return orders from the JSON response, or an empty list if the key is missing.
        return response.json().get("orders", [])
    except requests.exceptions.RequestException as e:
        log_and_print(f"Error fetching orders for {subdomain}: {e}", "error")
        return []
    except Exception as e:
        log_and_print(f"Unexpected error in fetch_orders: {e}", "error")
        return []


def update_order(subdomain, api_key, order_id):
    """
    Update the order status to 'in_progress' for a given order.

    Args:
        subdomain (str): The subdomain for the store.
        api_key (str): API key for authentication.
        order_id (str): The unique identifier of the order.

    The function builds the PUT request URL and payload, logs the outgoing request details,
    and executes the request. It logs the API response and errors if the order update fails.
    """
    url = f"https://{subdomain}.mybrightsites.com{API_PATH}/{order_id}?token={api_key}"
    data = {"order": {"status": "in_progress"}}
    log_and_print(f"Sending PUT request to {url} with data: {data}")

    try:
        response = requests.put(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            json=data,
            timeout=30
        )
        log_and_print(
            f"Response from {url}: {response.status_code} - {response.text}")
        response.raise_for_status()  # Ensure that HTTP errors are raised.
        log_and_print(
            f"Order {order_id} updated to 'in_progress' on {subdomain}.")
    except requests.exceptions.RequestException as e:
        log_and_print(
            f"Error updating order {order_id} on {subdomain}: {e}", "error")
    except Exception as e:
        log_and_print(
            f"Unexpected error in update_order for order {order_id}: {e}", "error")


def process_orders(subdomain, api_key):
    """
    Process and update orders based on creation time and status.

    Args:
        subdomain (str): The subdomain for the store.
        api_key (str): API key for authentication.

    The function calculates the current UTC time and defines a time window. It fetches orders 
    created before now minus two hours and processes each order. Orders are evaluated based on 
    their status and creation time. If an order has a 'new' status and is older than two hours,
    its status is updated. Detailed logging is applied throughout to track the processing flow.
    """
    now = datetime.utcnow()
    # Define a time window for fetching orders:
    # - 'created_at_from' is set far in the past (1900) to include all orders.
    # - 'created_at_to' is set to two hours ago to only capture orders older than now minus 2 hours.
    # Setting an early date to include all potential orders.
    created_at_from = "1900-01-01T00:00:00"
    created_at_to = (now - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S")
    log_and_print(
        f"Fetching orders for {subdomain} from {created_at_from} to {created_at_to}.")

    orders = fetch_orders(subdomain, api_key, created_at_from, created_at_to)
    if not orders:
        log_and_print(f"No orders found for {subdomain}.")
        return

    for order in orders:
        try:
            order_id = order.get("order_id")
            status = order.get("status")
            created_at = order.get("created_at")

            # Validate that the order has the required fields.
            if not order_id or not created_at:
                log_and_print(f"Skipping invalid order: {order}", "warning")
                continue

            log_and_print(
                f"Processing order {order_id} with status '{status}'...")

            # Ensure that the order's creation timestamp is ISO 8601 compliant.
            # Replace 'Z' (Zulu time indicator) with '+00:00' for proper parsing.
            created_at_clean = created_at.replace('Z', '+00:00')
            created_at_dt = datetime.fromisoformat(
                created_at_clean
            ).astimezone(timezone.utc).replace(tzinfo=None)

            # Only update orders that are:
            # - New (status equals 'new')
            # - Created more than 2 hours ago (older than now - 2 hours)
            if status == "new" and (now - created_at_dt) > timedelta(hours=2):
                log_and_print(
                    f"Order {order_id} qualifies for update. Initiating update process...")
                update_order(subdomain, api_key, order_id)
            else:
                log_and_print(
                    f"Order {order_id} does not meet update criteria.")

        except ValueError as ve:
            # Capture errors related to datetime parsing.
            log_and_print(
                f"Error parsing 'created_at' for order {order.get('order_id', 'unknown')}: {ve}. Raw value: {created_at}", "error")
        except Exception as e:
            # Log any unexpected errors during processing.
            log_and_print(
                f"Unexpected error while processing order {order.get('order_id', 'unknown')}: {e}", "error")


def main():
    """
    Main entry point for processing orders across all defined domains.

    The function iterates over the list of domains and processes orders for each one. Each 
    domain requires a valid subdomain and API key. Errors related to missing configurations 
    or unexpected exceptions during the processing loop are logged.
    """
    try:
        for domain in DOMAINS:
            subdomain = domain.get("subdomain")
            api_key = domain.get("api_key")

            # Ensure that the essential configuration for each domain is present.
            if not subdomain or not api_key:
                log_and_print(
                    f"Missing required configuration for domain: {domain}", "error")
                continue

            log_and_print(f"Processing orders for {subdomain}...")
            process_orders(subdomain, api_key)
    except Exception as e:
        log_and_print(f"Critical error in main loop: {e}", "error")


if __name__ == "__main__":
    main()
