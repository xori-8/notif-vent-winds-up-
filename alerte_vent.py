from datetime import datetime
import requests

LATITUDE = 47.247
LONGITUDE = -2.167
VENT_MIN = 12.0
VENT_MAX = 16.0

# Ton canal ntfy
NTFY_TOPIC = "brevin-wind-alert-9821"


def is_direction_favorable(deg):
    """Vérifie si le vent est entre Sud-Ouest (225°) et Nord-Ouest (315°)."""
    if deg is None:
        return False
    return 225 <= deg <= 315


def get_direction_label(deg):
    if deg is None:
        return "?"
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
    """Récupère les prévisions. On utilise AROME en priorité avec fallback sur les modèles Météo-France."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {}
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": "wind_speed_10m,wind_gusts_10m,wind_direction_10m",
        "models": ["meteofrance_arome_france_hd", "meteofrance_seamless"],
        "wind_speed_unit": "kn",
        "timezone": "Europe/Paris",
        "forecast_days": 3,
    
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    # Si seamless/arome retourne les données
    hourly = data.get("hourly", {})
    return hourly


def find_consecutive_sessions(day_data, min_hours=3):
    """Détecte les blocs d'au moins `min_hours` heures consécutives favorables."""
    sessions = []
    current_session = []

    for point in day_data:
        vent = point.get("vent")
        direction = point.get("dir")

        # Protection contre les valeurs nulles (NoneType)
        if vent is None or direction is None:
            if len(current_session) >= min_hours:
                sessions.append(current_session)
            current_session = []
            continue

        speed_ok = VENT_MIN <= vent <= VENT_MAX
        dir_ok = is_direction_favorable(direction)

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
        valid_gusts = [p["rafales"] for p in session if p["rafales"] is not None]
        max_gust = max(valid_gusts) if valid_gusts else avg_speed
        avg_dir = sum(p["dir"] for p in session) / len(session)
        dir_label = get_direction_label(avg_dir)

        message_lines.append()
            f"🌊 {h_start} à {h_end} ({len(session)}h):\n"
            f"   • Vent : {avg_speed:.1f} kts (rafales {max_gust:.1f} kts)\n"
            f"   • Dir : {dir_label} ({avg_dir:.0f}°)"
        

    full_message = "\n\n".join(message_lines)

    requests.post()
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=full_message.encode("utf-8"),
        headers={},
            "Title": title.encode("utf-8"),
            "Priority": "high",
            "Tags": "surfer,wind_blowing",
        timeout=10,
    


def check_all():
    data = get_forecast()
    # Récupération sécurisée des listes de clés
    times = data.get("time", [])
   
    # L'API peut nommer la clé avec le nom du modèle ou en standard
    wind_keys = [k for k in data.keys() if k.startswith("wind_speed_10m")]
    gust_keys = [k for k in data.keys() if k.startswith("wind_gusts_10m")]
    dir_keys = [k for k in data.keys() if k.startswith("wind_direction_10m")]

    wind_speeds = data[wind_keys[0]] if wind_keys else []
    gusts = data[gust_keys[0]] if gust_keys else [None] * len(times)
    directions = data[dir_keys[0]] if dir_keys else [None] * len(times)

    days_data = {}
    for t, vent, rafales, direct in zip(times, wind_speeds, gusts, directions):
        date_str, heure = t.split("T")
        if date_str not in days_data:
            days_data[date_str] = []
        days_data[date_str].append()
            {"heure": heure, "vent": vent, "rafales": rafales, "dir": direct}
        

    dates_sorted = sorted(list(days_data.keys()))
    if not dates_sorted:
        print("[INFO] Aucune donnée météo retournée.")
        return

    today_str = dates_sorted[0]
    j_plus_2_str = dates_sorted[2] if len(dates_sorted) >= 3 else None
    j_plus_1_str = dates_sorted[1] if len(dates_sorted) >= 3 else None

    from datetime import datetime, time
    heure_actuelle = datetime.now() .time()
    heure_de_debut = time (9, 0)
    heure_de_fin = time (19, 30)
    
    if heure_de_debut <= heure_actuelle <= heure_de_fin:
        # 1. Vérification pour AUJOURD'HUI
        today_sessions = find_consecutive_sessions(days_data[today_str])
        if today_sessions:
            print(f"[OK] Session trouvée pour aujourd'hui ({today_str})")
            send_notification("🔥 Session AUJOURD'HUI à Saint-Brevin !", today_sessions)
        else:
            print(f"[INFO] Aucune session de 3h continue aujourd'hui ({today_str}).")
            
        # 2. Vérification pour DANS 1 JOURS (J+2)
        if j_plus_1_str and j_plus_1_str in days_data and ti:
            j1_sessions = find_consecutive_sessions(days_data[j_plus_1_str])
            if j1_sessions:
                date_formatted = datetime.strptime(j_plus_1_str, "%Y-%m-%d").strftime("%d/%m")
                print(f"[OK] Session trouvée pour J+1 ({date_formatted})")
                send_notification(f"📅 Session prévue dans 1 jours ({date_formatted})", j1_sessions
            else:
                print(f"[INFO] Aucune session de 3h continue pour J+1 ({j_plus_2_str}).")
                
        # 3. Vérification pour DANS 2 JOURS (J+2)
        if j_plus_2_str and j_plus_2_str in days_data:
            j2_sessions = find_consecutive_sessions(days_data[j_plus_2_str])
            if j2_sessions:
                date_formatted = datetime.strptime(j_plus_2_str, "%Y-%m-%d").strftime("%d/%m")
                print(f"[OK] Session trouvée pour J+2 ({date_formatted})")
                send_notification(f"📅 Session prévue dans 2 jours ({date_formatted})", j2_sessions)
            else:
                print(f"[INFO] Aucune session de 3h continue pour J+2 ({j_plus_2_str}).")


if __name__ == "__main__":
    check_all()
