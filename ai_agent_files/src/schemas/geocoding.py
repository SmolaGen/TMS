from typing import List, Optional
from pydantic import BaseModel

class GeocodingResult(BaseModel):
    name: str
    lat: float
    lon: float
    address_full: Optional[str] = None
    osm_id: Optional[int] = None
    osm_key: Optional[str] = None
    osm_value: Optional[str] = None
