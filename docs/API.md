# TMS API Documentation

Base URL: `https://myappnf.ru/api/v1`

## Authentication

All private endpoints require a Bearer token:
`Authorization: Bearer <JWT_TOKEN>`

---

## Routing API

### Get Route
`GET /routing/route`

**Query Parameters:**
- `origin_lat` (float): Latitude of origin
- `origin_lon` (float): Longitude of origin
- `destination_lat` (float): Latitude of destination
- `destination_lon` (float): Longitude of destination
- `with_geometry` (bool, optional): Default true. Include polyline.

**Response:**
```json
{
  "distance_meters": 1200.5,
  "distance_km": 1.2,
  "duration_seconds": 300,
  "duration_minutes": 5.0,
  "geometry": "encoded_polyline_string",
  "base_price": "300.00",
  "distance_price": "25.00",
  "total_price": "325.00"
}
```

---

## Drivers API

### List Drivers
`GET /drivers`

### Get Driver
`GET /drivers/{id}`

### Get Driver Stats
`GET /drivers/{id}/stats`
**Query Parameters:**
- `days` (int): Number of days for stats (e.g., 30)

---

## Monitoring

- **Health Check**: `GET /health`
- **Metrics**: `GET /metrics` (Prometheus format)
