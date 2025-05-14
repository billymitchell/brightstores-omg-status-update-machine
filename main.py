import os
import requests
import time
import logging
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    filename='order_status_updater.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# Constants
DOMAINS = [
    {"subdomain": "centricity-test-store",
        "api_key": os.getenv("CENTRICITY_TEST_STORE_API_KEY")},
    {"subdomain": "dummy-store-1",
        "api_key": os.getenv("DUMMY_STORE_1_API_KEY")},
]
API_PATH = "/api/v2.6.1/orders"
CHECK_INTERVAL = 60 * 60 * 2  # 2 hours in seconds


def log_and_print(message, level="info"):
    """Log and print messages."""
    getattr(logging, level)(message)
    print(message)


def fetch_orders(subdomain, api_key, created_at_from, created_at_to):
    """Fetch orders from the API."""
    url = f"https://{subdomain}.mybrightsites.com{API_PATH}?token={api_key}"
    params = {"created_at_from": created_at_from,
              "created_at_to": created_at_to}
    log_and_print(f"Sending GET request to {url} with params: {params}")

    try:
        response = requests.get(url, params=params, timeout=30)
        log_and_print(
            f"Response from {url}: {response.status_code} - {response.text}")
        response.raise_for_status()
        return response.json().get("orders", [])
    except requests.exceptions.RequestException as e:
        log_and_print(f"Error fetching orders for {subdomain}: {e}", "error")
        return []


def update_order(subdomain, api_key, order_id):
    """Update the status of an order to 'in_progress'."""
    url = f"https://{subdomain}.mybrightsites.com{API_PATH}/{order_id}?token={api_key}"
    data = {"order": {"status": "in_progress"}}
    log_and_print(f"Sending PUT request to {url} with data: {data}")

    try:
        response = requests.put(
            url, headers={"Authorization": f"Bearer {api_key}"}, json=data, timeout=30
        )
        log_and_print(
            f"Response from {url}: {response.status_code} - {response.text}")
        response.raise_for_status()
        log_and_print(
            f"Order {order_id} updated to 'in_progress' on {subdomain}.")
    except requests.exceptions.RequestException as e:
        log_and_print(
            f"Error updating order {order_id} on {subdomain}: {e}", "error")


def process_orders(subdomain, api_key):
    """Process orders for a given subdomain."""
    now = datetime.utcnow()
    created_at_from = (now - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S")
    created_at_to = now.strftime("%Y-%m-%dT%H:%M:%S")
    log_and_print(
        f"Fetching orders for {subdomain} from {created_at_from} to {created_at_to}."
    )

    orders = fetch_orders(subdomain, api_key, created_at_from, created_at_to)
    if not orders:
        log_and_print(f"No orders found for {subdomain}.")
        return

    for order in orders:
        order_id = order.get("order_id")
        status = order.get("status")
        created_at = order.get("created_at")

        if not order_id or not created_at:
            log_and_print(f"Skipping invalid order: {order}", "warning")
            continue

        log_and_print(f"Processing order {order_id} with status '{status}'...")

        try:
            created_at_dt = datetime.fromisoformat(
                created_at).astimezone(timezone.utc).replace(tzinfo=None)

            if status == "new" and (now - created_at_dt) <= timedelta(hours=2):
                log_and_print(
                    f"Order {order_id} is older than two hours with new status.")
                update_order(subdomain, api_key, order_id)

        except ValueError as e:
            log_and_print(
                f"Error parsing 'created_at' for order {order_id}: {e}. Raw value: {created_at}",
                "error",
            )


def main():
    """Process orders for all domains."""
    for domain in DOMAINS:
        log_and_print(f"Processing orders for {domain['subdomain']}...")
        process_orders(domain["subdomain"], domain["api_key"])


if __name__ == "__main__":
    main()
