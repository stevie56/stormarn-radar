"""
utils/map_utils.py — Folium-Karte
"""
import folium
from folium.plugins import MarkerCluster
from utils.scoring import STATUS_COLOR

WAS_BLUE   = "#003064"
WAS_ORANGE = "#f29400"

def make_map(standorte: list[dict], firmen: list[dict] | None = None,
             center: list = [53.685, 10.31], zoom: int = 11) -> folium.Map:

    m = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles="CartoDB positron",
        control_scale=True,
    )

    # ── Gewerbestandort-Pins ──────────────────────────────
    cluster = MarkerCluster(name="Gewerbegebiete", show=True)

    for s in standorte:
        if not s.get("lat") or not s.get("lng"):
            continue

        color  = STATUS_COLOR.get(s.get("status","rot"), "#dc2626")
        score  = s.get("score","?")
        status = s.get("status","rot")
        trend  = s.get("trend","=")
        fa     = s.get("fahrten_tag", 0)

        icon_html = f"""
        <div style="
            background:{color};
            color:#fff;
            border-radius:8px;
            padding:3px 7px;
            font-size:11px;
            font-weight:700;
            border:2px solid #fff;
            box-shadow:0 2px 6px rgba(0,0,0,.35);
            white-space:nowrap;
            font-family:'IBM Plex Sans',sans-serif;
        ">{score} {trend}</div>"""

        popup_html = f"""
        <div style="font-family:sans-serif;min-width:220px;padding:4px">
          <div style="font-weight:700;font-size:14px;color:{WAS_BLUE};margin-bottom:4px">{s.get('name','')}</div>
          <div style="font-size:11px;color:#6b7280;margin-bottom:8px">{s.get('ort','')}</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-bottom:8px">
            <div style="background:#f0f2f5;border-radius:6px;padding:5px 8px;text-align:center">
              <div style="font-size:16px;font-weight:700;color:{color}">{score}</div>
              <div style="font-size:9px;color:#6b7280">Score</div>
            </div>
            <div style="background:#f0f2f5;border-radius:6px;padding:5px 8px;text-align:center">
              <div style="font-size:16px;font-weight:700;color:{WAS_BLUE}">{fa}</div>
              <div style="font-size:9px;color:#6b7280">Fahrten/Tag</div>
            </div>
          </div>
          <div style="font-size:10px;color:#6b7280">
            <b>Beschäftigte:</b> {s.get('beschaeftigte','—')}<br>
            <b>Datenstand:</b> {s.get('daten_stand','—')}
          </div>
        </div>"""

        folium.Marker(
            location=[s["lat"], s["lng"]],
            icon=folium.DivIcon(html=icon_html, icon_size=(60, 26), icon_anchor=(30, 13)),
            popup=folium.Popup(popup_html, max_width=260),
            tooltip=s.get("name",""),
        ).add_to(cluster)

    cluster.add_to(m)

    # ── Firmen-Pins (optional, kleiner) ──────────────────
    if firmen:
        firm_layer = folium.FeatureGroup(name="Unternehmen", show=False)
        for f in firmen:
            if not f.get("lat") or not f.get("lng"):
                continue
            ma = f.get("beschaeftigte", 0) or 0
            r  = 8 if ma >= 1000 else 6 if ma >= 300 else 4
            folium.CircleMarker(
                location=[f["lat"], f["lng"]],
                radius=r,
                color="#fff",
                weight=1.5,
                fill=True,
                fill_color="#2563eb",
                fill_opacity=0.8,
                tooltip=f"{f.get('name','')} · {ma} MA",
                popup=f"<b>{f.get('name','')}</b><br>{f.get('ort','')}<br>MA: {ma}",
            ).add_to(firm_layer)
        firm_layer.add_to(m)

    folium.LayerControl().add_to(m)
    return m
