import httpx


async def estimate_walk_minutes(
    lat1: float, lng1: float, lat2: float, lng2: float
) -> int | None:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "http://router.project-osrm.org/route/v1/foot/"
                f"{lng1},{lat1};{lng2},{lat2}",
                params={"overview": "false"},
            )
            resp.raise_for_status()
            routes = resp.json().get("routes", [])
            if routes:
                return max(1, int(routes[0]["duration"] / 60))
    except Exception:
        pass
    return None
