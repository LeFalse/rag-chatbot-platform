"""Integration tests for metrics endpoints validation."""

from datetime import date

import pytest
from httpx import AsyncClient


class TestMetricsValidation:
    """Test metrics endpoint validation."""

    @pytest.mark.asyncio
    async def test_daily_missing_start_date(
        self,
        api_client: AsyncClient,
    ):
        """Test daily metrics without start_date."""
        response = await api_client.get(
            "/metrics/daily",
            params={"end_date": date.today().isoformat()},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_daily_missing_end_date(
        self,
        api_client: AsyncClient,
    ):
        """Test daily metrics without end_date."""
        response = await api_client.get(
            "/metrics/daily",
            params={"start_date": date.today().isoformat()},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_hourly_missing_start_date(
        self,
        api_client: AsyncClient,
    ):
        """Test hourly stats without start_date."""
        response = await api_client.get(
            "/metrics/hourly",
            params={"end_date": date.today().isoformat()},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_hourly_missing_end_date(
        self,
        api_client: AsyncClient,
    ):
        """Test hourly stats without end_date."""
        response = await api_client.get(
            "/metrics/hourly",
            params={"start_date": date.today().isoformat()},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_daily_metrics_valid_params(self, api_client: AsyncClient):
        """Test daily metrics with valid parameters."""
        response = await api_client.get(
            "/metrics/daily",
            params={
                "start_date": date.today().isoformat(),
                "end_date": date.today().isoformat(),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_hourly_stats_valid_params(self, api_client: AsyncClient):
        """Test hourly stats with valid parameters."""
        response = await api_client.get(
            "/metrics/hourly",
            params={
                "start_date": date.today().isoformat(),
                "end_date": date.today().isoformat(),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
