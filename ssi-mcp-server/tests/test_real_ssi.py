import asyncio
from datetime import date

from app.services.api_client import SSIApiClient


async def main():
    client = SSIApiClient()

    try:
        print("Testing real SSi API...")
        print("URL: https://dailygraphs.finsoftai.com")
        print("Ticker: RELIANCE")
        print("Date: 2026-08-11")
        print()

        result = await client.get_daily_graphs(
            "RELIANCE",
            date(2026, 8, 11),
        )

        print("SUCCESS")
        print("Response received:")
        print(result)

    except Exception as e:
        print("FAILED")
        print(type(e).__name__)
        print(str(e))

    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())