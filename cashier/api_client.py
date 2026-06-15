"""Thin synchronous wrapper around httpx for Qt (no async in Qt main thread)."""
import httpx

from cashier.config import API_BASE_URL

_token: str | None = None


def set_token(token: str | None) -> None:
    global _token
    _token = token


def _headers() -> dict:
    h = {"Content-Type": "application/json"}
    if _token:
        h["Authorization"] = f"Bearer {_token}"
    return h


def _client() -> httpx.Client:
    return httpx.Client(base_url=API_BASE_URL, headers=_headers(), timeout=10.0)


def pin_login(location_id: str, pin: str) -> dict | None:
    try:
        with _client() as c:
            r = c.post("/auth/pin-login", json={"location_id": location_id, "pin": pin})
            if r.status_code == 200:
                return r.json()
            return None
    except httpx.RequestError:
        return None


def get_product_by_barcode(code: str) -> dict | None:
    try:
        with _client() as c:
            r = c.get(f"/catalog/products/by-barcode/{code}")
            return r.json() if r.status_code == 200 else None
    except httpx.RequestError:
        return None


def get_product_by_plu(tenant_id: str, plu: str) -> dict | None:
    try:
        with _client() as c:
            r = c.get(f"/catalog/products/by-plu/{plu}", params={"tenant_id": tenant_id})
            return r.json() if r.status_code == 200 else None
    except httpx.RequestError:
        return None


def search_products(tenant_id: str, query: str) -> list[dict]:
    try:
        with _client() as c:
            r = c.get("/catalog/products", params={"tenant_id": tenant_id, "limit": 20})
            if r.status_code == 200:
                items = r.json()
                q = query.lower()
                return [p for p in items if q in p["name"].lower() or q in p["plu"].lower()]
    except httpx.RequestError:
        pass
    return []


def open_cash_session(location_id: str, user_id: str, opening_float: float) -> dict | None:
    try:
        with _client() as c:
            r = c.post("/cash-sessions", json={
                "location_id": location_id,
                "user_id": user_id,
                "opening_float": str(opening_float),
            })
            return r.json() if r.status_code == 201 else None
    except httpx.RequestError:
        return None


def close_cash_session(session_id: str, closing_float: float) -> dict | None:
    try:
        with _client() as c:
            r = c.post(f"/cash-sessions/{session_id}/close", json={"closing_float": str(closing_float)})
            return r.json() if r.status_code == 200 else None
    except httpx.RequestError:
        return None


def get_x_report(session_id: str) -> dict | None:
    try:
        with _client() as c:
            r = c.get(f"/cash-sessions/{session_id}/x-report")
            return r.json() if r.status_code == 200 else None
    except httpx.RequestError:
        return None


def create_sale(sale_payload: dict) -> dict | None:
    try:
        with _client() as c:
            r = c.post("/sales", json=sale_payload)
            return r.json() if r.status_code == 201 else None
    except httpx.RequestError:
        return None


def get_price(product_id: str, location_id: str) -> dict | None:
    """Get the active regular price for a product at this location."""
    try:
        with _client() as c:
            r = c.get(f"/catalog/products/{product_id}/prices")
            if r.status_code == 200:
                prices = r.json()
                # prefer location-specific, then regular
                for p in sorted(prices, key=lambda x: (x["price_type"] != "location", x["price_type"] != "regular")):
                    if p["is_active"]:
                        return p
    except httpx.RequestError:
        pass
    return None
