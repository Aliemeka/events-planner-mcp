from mcp.server.fastmcp import FastMCP
import httpx
import logging

# import resend

# import os


mcp = FastMCP("events-planner-mcp")


WEATHER_URL = "https://api.open-meteo.com/v1/"

citys = {
    "Enugu": {
        "latitude": 6.4483,
        "longitude": 7.5139,
        "timezone": "Africa/Lagos",
    },
    "Lagos": {
        "latitude": 6.5244,
        "longitude": 3.3792,
        "timezone": "Africa/Lagos",
    },
    "Abuja": {
        "latitude": 9.0579,
        "longitude": 7.4951,
        "timezone": "Africa/Lagos",
    },
    "Port Harcourt": {
        "latitude": 4.8156,
        "longitude": 7.0498,
        "timezone": "Africa/Lagos",
    },
}

weather_code_map = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Drizzle light intensity",
    53: "Drizzle moderate intensity",
    55: "Drizzle dense intensity",
    56: "Freezing drizzle light intensity",
    57: "Freezing drizzle dense intensity",
    61: "Rain slight intensity",
    63: "Rain moderate intensity",
    65: "Rain heavy intensity",
    66: "Freezing rain light intensity",
    67: "Freezing rain heavy intensity",
    71: "Snow fall slight intensity",
    73: "Snow fall moderate intensity",
    75: "Snow fall heavy intensity",
    77: "Snow grains",
    80: "Rain showers slight intensity",
    81: "Rain showers moderate intensity",
    82: "Rain showers violent intensity",
    85: "Snow showers slight intensity",
    86: "Snow showers heavy intensity",
    95: "Thunderstorm slight or moderate",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


async def make_weather_request(city: str):
    """Make a weather request to the specified URL for the given city.

    Args:
        url (str): _description_
        city (str): _description_
    """

    city_data = citys.get(city)
    if not city_data:
        return {"error": "City not found"}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{WEATHER_URL}forecast",
            params={
                "latitude": city_data["latitude"],
                "longitude": city_data["longitude"],
                "timezone": city_data["timezone"],
                "daily": "weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum",
                "forcast_days": 14,
                "current_weather": "true",
                "temperature_unit": "celsius",
            },
        )
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f"Failed to fetch weather data: {response.status_code}")
            return {"error": "Failed to fetch weather data"}


@mcp.tool()
async def get_current_weather(city: str):
    """Get the current weather for a specified city."""
    weather_data = await make_weather_request(city)
    if "error" in weather_data:
        return {"error": weather_data["error"]}

    current_weather = weather_data.get("current_weather", {})
    if not current_weather:
        return {"error": "No current weather data available"}

    return {
        "temperature": current_weather.get("temperature"),
        "windspeed": current_weather.get("windspeed"),
        "winddirection": current_weather.get("winddirection"),
        "weathercode": weather_code_map.get(
            current_weather.get("weathercode"), "Unknown"
        ),
    }


@mcp.tool()
async def get_weekly_forecast(city: str):
    """Get the weekly weather forecast for a specified city."""
    weather_data = await make_weather_request(city)
    if "error" in weather_data:
        return {"error": weather_data["error"]}

    daily_forecast = weather_data.get("daily", {})
    if not daily_forecast:
        return {"error": "No daily forecast data available"}

    return {
        "dates": daily_forecast.get("time", []),
        "weathercodes": [
            weather_code_map.get(code, "Unknown")
            for code in daily_forecast.get("weathercode", [])
        ],
    }


@mcp.tool()
async def get_weather_by_date(city: str, date: str):
    """Get the weather for a specific date in a specified city."""
    weather_data = await make_weather_request(city)
    if "error" in weather_data:
        return {"error": weather_data["error"]}

    daily_forecast = weather_data.get("daily", {})
    if not daily_forecast:
        return {"error": "No daily forecast data available"}

    if date not in daily_forecast.get("time", []):
        return {"error": "Date not found in forecast"}

    index = daily_forecast["time"].index(date)
    weather_info = {
        "date": date,
        "weathercode": weather_code_map.get(
            daily_forecast["weathercode"][index], "Unknown"
        ),
        "max_temp": daily_forecast["temperature_2m_max"][index],
        "min_temp": daily_forecast["temperature_2m_min"][index],
        "precipitation": daily_forecast["precipitation_sum"][index],
    }

    return weather_info


def send_email(to: str, subject: str, body: str):
    """Send an email (placeholder function)."""
    # This function would contain the logic to send an email.
    # For now, we will just log the email details.
    import resend
    import os
    from dotenv import load_dotenv

    load_dotenv()

    resend.api_key = os.getenv("RESEND_API_KEY", "secret_key")
    api_key = resend.api_key
    logging.info(f"Using Resend API key: {api_key}")

    params = {
        "from": "Emeka from Dome Academy <emeka@domeinitiative.com>",
        "to": [f"{to}"],
        "subject": subject,
        "html": body,
        "reply_to": "info@domeinitiative.com",
    }
    logging.info(f"Sending email to {to} with subject '{subject}' and body '{body}'")
    try:
        resend.Emails.send(params)
        logging.info(f"Email sent to {to}")
    except Exception as e:
        logging.error(f"Failed to send email to {to}: {e}")
        return False
    return True


@mcp.tool()
async def invite_people(
    emails: list[str],
    event_name: str,
    html_body: str,
):
    """Invite people to an event by email."""
    if not emails:
        return {"error": "No emails provided"}

    # Here you would implement the logic to send invitations
    # For now, we will just return a success message

    for email in emails:
        send_email(
            to=email,
            subject=f"Invitation to {event_name}",
            body=html_body,
        )

    return {
        "message": f"Invitations sent for {event_name} to {len(emails)} people.",
        "emails": emails,
    }


if __name__ == "__main__":
    mcp.run("stdio")
