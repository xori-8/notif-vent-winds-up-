from datetime import datetime
import requests

LATITUDE = 47.247
LONGITUDE = -2.167
VENT_MIN = 12.0
VENT_MAX = 16.0

# Ton canal ntfy
NTFY_TOPIC = "brevin-wind-alert-9821"


def is_direction_favorable(deg):
    """Vérifie si le vent est orienté entre Sud-Ouest (225°) et Nord-Ouest (315°)."""
    return 225 <= deg <= 315


def get_direction_label(deg):
    if 215 <= deg < 235:
        return "SO"
    if 235 <= deg < 255:
        return "OSO"
    if 255 <= deg < 285:
        return "O"
    if 285 <= deg < 305:
        return "ONO"
    if 305 <= deg <= 325:
        return "NO"
    return f"{int(deg)}°"


def get_forecast():
    """Récupère les prévisions AROME HD sur 3 jours (Aujourd'hui, Demain, J+2)."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": "wind_speed_10m,wind_gusts_10m,wind_direction_10m",
        "models": "meteofrance_arome_france_hd",
        "wind_speed_unit": "kn",
        "timezone": "Europe/Paris",
        "forecast_days": 3,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()["hourly"]


def find_consecutive_sessions(day_data, min_hours=3):
    """Détecte les blocs d'au moins `min_hours` heures consécutives favorables."""
    sessions = []
    current_session = []

    for point in day_data:
        speed_ok = VENT_MIN <= point["vent"] <= VENT_MAX
        dir_ok = is_direction_favorable(point["dir"])

        if speed_ok and dir_ok:
            current_session.append(point)
        else:
            if len(current_session) >= min_hours:
                sessions.append(current_session)
            current_session = []

    if len(current_session) >= min_hours:
        sessions.append(current_session)

    return sessions


def send_notification(title, sessions):
    message_lines = []
    for session in sessions:
        h_start = session[0]["heure"]
        h_end = session[-1]["heure"]
        avg_speed = sum(p["vent"] for p in session) / len(session)
        max_gust = max(p["rafales"] for p in session)
        avg_dir = sum(p["dir"] for p in session) / len(session)
        dir_label = get_direction_label(avg_dir)

        message_lines.append(
            f"🌊 Créneau {h_start} - {h_end} ({len(session)}h):\n"
            f"   • Vent moy : {avg_speed:.1f} kts\n"
            f"   • Max rafales : {max_gust:.1f} kts\n"
            f"   • Orientation : {dir_label} ({avg_dir:.0f}°)"
        )

    full_message = "\n\n".join(message_lines)

    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=full_message.encode("utf-8"),
        headers={
            "Title": title.encode("utf-8"),
            "Priority": "high",
            "Tags": "surfer,wind_blowing",
        },
        timeout=10,
    )


def check_all():
    data = get_forecast()

    # Organise les prévisions par date (YYYY-MM-DD)
    days_data = {}
    for t, vent, rafales, direct in zip(
        data["time"],
        data["wind_speed_10m"],
        data["wind_gusts_10m"],
        data["wind_direction_10m"],
    ):
        date_str, heure = t.split("T")
        if date_str not in days_data:
            days_data[date_str] = []
        days_data[date_str].append(
            {"heure": heure, "vent": vent, "rafales": rafales, "dir": direct}
        )

    dates_sorted = sorted(list(days_data.keys()))
    today_str = dates_sorted[0]
    j_plus_2_str = dates_sorted[2] if len(dates_sorted) >= 3 else None

    # 1. Vérification pour AUJOURD'HUI (Matin même)
    today_sessions = find_consecutive_sessions(days_data[today_str])
    if today_sessions:
        print(f"[OK] Session(s) trouvée(s) pour aujourd'hui ({today_str})")
        send_notification("🔥 Session AUJOURD'HUI à Saint-Brevin !", today_sessions)
    else:
        print(f"[INFO] Aucune session de 3h continue aujourd'hui ({today_str}).")

    # 2. Vérification pour DANS 2 JOURS (J+2)
    if j_plus_2_str and j_plus_2_str in days_data:
        j2_sessions = find_consecutive_sessions(days_data[j_plus_2_str])
        if j2_sessions:
            date_formatted = datetime.strptime(j_plus_2_str, "%Y-%m-%d").strftime("%d/%m")
            print(f"[OK] Session(s) trouvée(s) pour J+2 ({date_formatted})")
            send_notification(f"📅 Session prévue dans 2 jours ({date_formatted})", j2_sessions)
        else:
            print(f"[INFO] Aucune session de 3h continue pour J+2 ({j_plus_2_str}).")


if __name__ == "__main__":
    check_all()
