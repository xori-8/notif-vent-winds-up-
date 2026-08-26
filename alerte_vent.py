import requests

LATITUDE = 47.247
LONGITUDE = -2.167
VENT_MIN = 12.0
VENT_MAX = 16.0
NTFY_TOPIC = "brevin-wind-alert-9821"  # Ton canal ntfy configuré à l'étape 1


def get_arome_hd_wind():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": "wind_speed_10m,wind_gusts_10m,wind_direction_10m",
        "models": "meteofrance_arome_france_hd",
        "wind_speed_unit": "kn",
        "timezone": "Europe/Paris",
        "forecast_days": 1,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()["hourly"]


def send_notification(creneaux):
    lignes = [
        f"• {c['heure']} : {c['vent']:.1f} noeuds (rafales {c['rafales']:.1f} noeuds, dir {c['dir']}°)"
        for c in creneaux
    ]
    message = (
        "Conditions favorables détectées à Saint-Brevin :\n"
        + "\n".join(lignes)
    )

    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={
            "Title": "Alerte Vent Saint-Brevin (12-16 kts)".encode("utf-8"),
            "Priority": "high",
            "Tags": "wind_blowing,surfer",
        },
        timeout=10,
    )


def check_conditions():
    data = get_arome_hd_wind()
    creneaux = []

    for t, vent, rafales, direct in zip(
        data["time"],
        data["wind_speed_10m"],
        data["wind_gusts_10m"],
        data["wind_direction_10m"],
    ):
        if VENT_MIN <= vent <= VENT_MAX:
            heure = t.split("T")[1]
            creneaux.append(
                {"heure": heure, "vent": vent, "rafales": rafales, "dir": direct}
            )

    if creneaux:
        send_notification(creneaux)
        print(f"[OK] {len(creneaux)} créneau(x) trouvé(s), notification envoyée.")
    else:
        print("[INFO] Aucun créneau entre 12 et 16 nœuds aujourd'hui.")


if __name__ == "__main__":
    check_conditions()
