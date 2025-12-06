import requests
import hmac
import hashlib
import time
import json
from django.conf import settings
from campus_marketplace.settings import LALAMOVE_API_KEY as API_KEY
from campus_marketplace.settings import LALAMOVE_API_SECRET as API_SECRET
from campus_marketplace.settings import LALAMOVE_MARKET as MARKET
from campus_marketplace.settings import LALAMOVE_BASE_URL as BASE_URL   

def _generate_signature(api_secret, timestamp, method, path, body_json=""):
    """Internal helper to generate the HMAC-SHA256 signature."""
    raw_signature = f"{timestamp}\r\n{method}\r\n{path}\r\n\r\n{body_json}"
    print('\nraw_signature\n',raw_signature,'\n')
    return hmac.new(
        bytes(api_secret, 'utf-8'),
        bytes(raw_signature, 'utf-8'),
        hashlib.sha256
    ).hexdigest()

def _make_lalamove_request(method, path, data=None):
    """Internal helper to handle signed HTTP requests."""
    
    timestamp = str(int(time.time() * 1000))
    body_json = json.dumps(data) if data else ""
    signature = _generate_signature(API_SECRET, timestamp, method, path, body_json)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"hmac {API_KEY}:{timestamp}:{signature}",
        "X-LLM-Country": MARKET,
        'Market': MARKET
    }
    
    url = f"{BASE_URL}{path}"
    
    response = requests.request(method, url, headers=headers, data=body_json)
    response.raise_for_status() # Raises an exception for 4xx/5xx responses
    print('\nresponse.json()\n\n',json.dumps( response.json),"\n", timestamp, method, path, body_json, signature, headers, url, "\n" )
    return response.json()

# --- Public Interface Functions ---

def get_lalamove_quotation(order_details_payload):
    """
    Requests a price estimate from the Lalamove API.
    Returns the JSON response (including 'quotedTotalFee').
    """
    path = "/v3/quotations"
    print('\norder_details_payload\n',json.dumps( order_details_payload),"\n", order_details_payload,"\n")
    return _make_lalamove_request("POST", path, data=order_details_payload)

def create_lalamove_order(order_details_payload):
    """
    Places a final delivery order using a previously obtained quotation ID.
    Returns the JSON response with the order details.
    """
    path = "/v3/orders"
    # Ensure the payload includes the quotationId from the previous step
    return _make_lalamove_request("POST", path, data=order_details_payload)