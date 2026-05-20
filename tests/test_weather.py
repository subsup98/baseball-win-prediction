import pandas as pd

from mlb_winprob.weather import augment_weather_with_open_meteo


class FakeOpenMeteoCollector:
    def hourly_weather(self, *, latitude, longitude, start_date, end_date):
        assert latitude == 39.283787
        assert longitude == -76.621689
        assert start_date == "2024-03-28"
        return pd.DataFrame(
            {
                "weather_hour": pd.to_datetime(["2024-03-28 19:00:00+00:00"], utc=True),
                "open_meteo_temperature": [55.0],
                "humidity": [62],
                "open_meteo_wind_speed": [10.0],
                "open_meteo_wind_direction_degrees": [310],
            }
        )


def test_augment_weather_with_open_meteo_fills_humidity():
    games = pd.DataFrame(
        [
            {
                "game_id": "g1",
                "game_date": "2024-03-28 19:05:00+00:00",
                "season": 2024,
                "venue_id": 2,
            }
        ]
    )
    weather = pd.DataFrame(
        [
            {
                "game_id": "g1",
                "temperature": 54,
                "wind_speed": 9,
                "wind_direction": "In From LF",
                "humidity": None,
                "is_dome": 0,
            }
        ]
    )
    venues = pd.DataFrame(
        [
            {
                "venue_id": 2,
                "latitude": 39.283787,
                "longitude": -76.621689,
            }
        ]
    )

    augmented = augment_weather_with_open_meteo(
        games=games,
        weather=weather,
        venues=venues,
        collector=FakeOpenMeteoCollector(),
    )

    row = augmented.iloc[0]
    assert row["humidity"] == 62
    assert row["humidity_source"] == "open_meteo_archive"
    assert row["open_meteo_temperature"] == 55.0
