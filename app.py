import io
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="MaxStats PRO", layout="wide")

st.title("⚽ MaxStats - Twój Asystent Piłkarski")

competitions_map = {
    "Premier League (Anglia)": "E0",
    "La Liga (Hiszpania)": "SP1",
    "Bundesliga (Niemcy)": "D1",
    "Serie A (Włochy)": "I1",
    "Ligue 1 (Francja)": "F1",
    "Eredivisie (Holandia)": "N1",
    "Pro League (Belgia)": "B1",
    "Liga Portugal (Portugalia)": "P1",
    "Süper Lig (Turcja)": "T1",
    "Championship (Anglia)": "E1",
    "2. Bundesliga (Niemcy)": "D2",
}


def get_current_season_code():
    now = pd.Timestamp.now()
    year = now.year
    if now.month < 7:
        start_year = year - 1
        end_year = year
    else:
        start_year = year
        end_year = year + 1
    return f"{str(start_year)[-2:]}{str(end_year)[-2:]}"


# Sidebar
league_label = st.sidebar.selectbox("Wybierz Ligę", list(competitions_map.keys()))
league_code = competitions_map[league_label]
season_code = get_current_season_code()


@st.cache_data(ttl=3600)
def load_data(l_code, s_code):
    headers = {"User-Agent": "Mozilla/5.0"}
    urls = [
        f"https://www.football-data.co.uk/mmz4281/{s_code}/{l_code}.csv",
        f"https://www.football-data.co.uk/new/{l_code}.csv",
        "https://www.football-data.co.uk/fixtures.csv",
    ]
    df = None
    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=6)
            if res.status_code == 200 and len(res.text) > 100:
                df_temp = pd.read_csv(io.StringIO(res.text), on_bad_lines="skip")
                col_rename = {
                    "Home": "HomeTeam",
                    "Away": "AwayTeam",
                    "HG": "FTHG",
                    "AG": "FTAG",
                    "Res": "FTR",
                    "Div": "League",
                }
                df_temp = df_temp.rename(columns=col_rename)

                if url.endswith("fixtures.csv"):
                    div_col = "League" if "League" in df_temp.columns else ("Div" if "Div" in df_temp.columns else None)
                    if div_col:
                        df_temp = df_temp[df_temp[div_col] == l_code]

                if "HomeTeam" in df_temp.columns and "AwayTeam" in df_temp.columns and not df_temp.empty:
                    if df is None:
                        df = df_temp
                    else:
                        df = pd.concat([df, df_temp], ignore_index=True)
        except Exception:
            continue
    if df is not None:
        df = df.dropna(subset=["HomeTeam", "AwayTeam"])
    return df


df_matches = load_data(league_code, season_code)

if df_matches is not None and not df_matches.empty:
    teams = sorted(
        list(
            set(df_matches["HomeTeam"].astype(str).str.strip().tolist())
            | set(df_matches["AwayTeam"].astype(str).str.strip().tolist())
        )
    )
    selected_team = st.sidebar.selectbox("Wybierz Drużynę", teams)
    x_matches = st.sidebar.slider("Analiza ostatnich meczów", 1, 50, 5)

    # Obliczanie pozycji w tabeli
    df_played = df_matches.dropna(subset=["FTHG", "FTAG"]).copy()
    table_data = []
    for t in teams:
        t_df = df_played[(df_played["HomeTeam"] == t) | (df_played["AwayTeam"] == t)]
        pts, gf_tot, ga_tot = 0, 0, 0
        for _, row in t_df.iterrows():
            is_h = row["HomeTeam"] == t
            gf = int(row["FTHG"] if is_h else row["FTAG"])
            ga = int(row["FTAG"] if is_h else row["FTHG"])
            res = str(row.get("FTR", "")).upper()
            gf_tot += gf
            ga_tot += ga
            if (is_h and res == "H") or (not is_h and res == "A"):
                pts += 3
            elif res == "D":
                pts += 1
        table_data.append({"team": t, "pts": pts, "gd": gf_tot - ga_tot, "gf": gf_tot, "m": len(t_df)})

    tbl_df = pd.DataFrame(table_data).sort_values(by=["pts", "gd", "gf"], ascending=False).reset_index(drop=True)
    tbl_df["pos"] = tbl_df.index + 1

    team_row = tbl_df[tbl_df["team"] == selected_team]
    if not team_row.empty:
        pos = team_row.iloc[0]["pos"]
        pts = team_row.iloc[0]["pts"]
        m = team_row.iloc[0]["m"]
        st.info(f"🏆 **Aktualna pozycja w tabeli:** {pos}. miejsce ({pts} pkt w {m} meczach)")

    # Najbliższy mecz
    team_all = df_matches[(df_matches["HomeTeam"] == selected_team) | (df_matches["AwayTeam"] == selected_team)]
    unplayed = team_all[team_all["FTHG"].isna() | (team_all["FTHG"].astype(str).str.strip() == "")]
    if not unplayed.empty:
        nm = unplayed.iloc[0]
        is_h = nm["HomeTeam"] == selected_team
        opp = nm["AwayTeam"] if is_h else nm["HomeTeam"]
        v = "Dom" if is_h else "Wyjazd"
        dt = f"{nm.get('Date', '')} {nm.get('Time', '')}".strip()
        st.success(f"⏳ **Najbliższy mecz:** vs {opp} | Data: {dt} | Miejsce: {v}")

    # Statystyki drużyny
    latest = team_all.dropna(subset=["FTHG"]).tail(x_matches)
    if not latest.empty:
        n = len(latest)
        gf_s, ga_s, sh_s, st_s, cr_s, fl_s, cards_s, btts_c = 0, 0, 0, 0, 0, 0, 0, 0
        for _, row in latest.iterrows():
            is_h = row["HomeTeam"] == selected_team
            gf = int(row["FTHG"] if is_h else row["FTAG"])
            ga = int(row["FTAG"] if is_h else row["FTHG"])
            if gf > 0 and ga > 0:
                btts_c += 1
            sh = int(row.get("HS" if is_h else "AS", 0) or 0)
            st_val = int(row.get("HST" if is_h else "AST", 0) or 0)
            cr = int(row.get("HC" if is_h else "AC", 0) or 0)
            fl = int(row.get("HF" if is_h else "AF", 0) or 0)
            y = int(row.get("HY" if is_h else "AY", 0) or 0)
            r = int(row.get("HR" if is_h else "AR", 0) or 0)

            gf_s += gf
            ga_s += ga
            sh_s += sh
            st_s += st_val
            cr_s += cr
            fl_s += fl
            cards_s += y + r

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Gole (Strzelone / Stracone)", f"{gf_s / n:.2f} / {ga_s / n:.2f}")
        col2.metric("BTTS %", f"{(btts_c / n) * 100:.1f}%")
        col3.metric("Strzały / Celne na mecz", f"{sh_s / n:.2f} / {st_s / n:.2f}")
        col4.metric("Kartki / Faule na mecz", f"{cards_s / n:.2f} / {fl_s / n:.2f}")

    # Tabela ligowa
    st.subheader("🏆 Tabela Ligowa")
    st.dataframe(
        tbl_df[["pos", "team", "m", "pts", "gd", "gf"]].rename(
            columns={"pos": "Poz.", "team": "Drużyna", "m": "Mecze", "pts": "Pkt", "gd": "RB", "gf": "Gole"}
        ),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.error("Błąd pobierania danych z serwera.")
