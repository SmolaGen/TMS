import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from src.workers.ingest_worker import IngestWorker, LocationRecord, BinaryCopyWriter

@pytest.fixture
def mock_redis():
    return AsyncMock()

@pytest.fixture
def ingest_worker(mock_redis):
    return IngestWorker(redis=mock_redis, pg_dsn="postgresql://user:pass@localhost/db")

def test_location_record_parsing():
    entry_id = b"1625097600000-0"
    data = {
        b"driver_id": b"1",
        b"lat": b"43.11",
        b"lon": b"131.88",
        b"ts": b"2021-07-01T00:00:00+00:00"
    }
    record = LocationRecord.from_stream_entry(entry_id, data)
    assert record.driver_id == 1
    assert record.latitude == 43.11
    assert record.longitude == 131.88
    assert record.timestamp.year == 2021

def test_binary_copy_writer():
    writer = BinaryCopyWriter()
    ts = datetime(2021, 7, 1, tzinfo=timezone.utc)
    writer.add_row(driver_id=1, lat=43.11, lon=131.88, recorded_at=ts)
    data = writer.finish()
    assert b"PGCOPY" in data
    assert len(data) > 20

@pytest.mark.asyncio
async def test_worker_setup(ingest_worker, mock_redis):
    await ingest_worker.setup()
    mock_redis.xgroup_create.assert_called_once()

@pytest.mark.asyncio
async def test_process_batch_success(ingest_worker, mock_redis):
    # Mock xreadgroup to return one entry
    mock_redis.xreadgroup.return_value = [
        ("driver:locations", [
            (b"1-0", {b"driver_id": b"1", b"lat": b"43.11", b"lon": b"131.88", b"ts": b"2021-07-01T00:00:00+00:00"})
        ])
    ]
    
    # Mock psycopg.connect
    with patch("psycopg.connect") as mock_connect:
        mock_conn = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        
        # Test _process_batch
        await ingest_worker._process_batch()
        
        # Verify psycopg was used
        mock_connect.assert_called_once()
        # Verify redis xack was called
        mock_redis.xack.assert_called_once_with("driver:locations", "location_ingesters", "1-0")

@pytest.mark.asyncio
async def test_ingest_with_poison_detection(ingest_worker, mock_redis):
    record = LocationRecord(
        entry_id="1-0",
        driver_id=1,
        latitude=43.11,
        longitude=131.88,
        timestamp=datetime.now(timezone.utc)
    )
    
    # Mock psycopg.connect and execute to FAIL
    with patch("psycopg.connect") as mock_connect:
        mock_conn = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        mock_cur = mock_conn.cursor.return_value.__enter__.return_value
        mock_cur.execute.side_effect = Exception("DB Error")
        
        # We need to test the logic that sends to DLQ after MAX_RETRIES
        from src.workers.ingest_worker import MAX_RETRIES
        for _ in range(MAX_RETRIES):
            await ingest_worker._ingest_with_poison_detection([record])
        
        # Verify DLQ was called (xadd)
        mock_redis.xadd.assert_called_once()
        assert "dlq:location_errors" in mock_redis.xadd.call_args[0]
        # Verify record was ACKed in the end to avoid blocking
        assert mock_redis.xack.call_count == 1
