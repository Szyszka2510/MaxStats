import io
import pandas as pd
import requests
import streamlit as st

# Konfiguracja strony
st.set_page_config(page_title="MaxStats - Twój Asystent Piłkarski", layout="wide")

# Custom CSS — dostosowanie stylów na wzór Twojego QSS z PyQt6
st.markdown("""
<style>
    .stApp { background-color: #0F172A; color: #F8FAFC; }
    div[data-testid="stMetric"] {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 15px;
    }
    div[data-testid="stMetric"]:hover {
        border: 1px solid #38BDF8;
    }
    .pos-box {
        background-color: #1E293B;
        border: 1px solid #0284C7;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

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

# ================= PANEL BOCZNY (SIDEBAR) =================
st.sidebar.header("⚽ Wybór Rozgrywek")
league_name = st.sidebar.selectbox("Wybierz Ligę", list(competitions_map.keys()))
league_code = competitions_map[league_name]
season_code = get_current_season_code()

@st.cache_data(ttl=3600)
def fetch_data(l_code, s_code):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    urls_to_try = [
        f"https://www.football-data.co.uk/mmz4281/{s_code}/{l_code}.csv",
        f"https://www.football-data.co.uk/new/{l_code}.csv"
    ]
    df = None
    for url in urls_to_try:
        try:
            res = requests.get(url, headers=headers, timeout=6)
            if res.status_code == 200 and len(res.text) > 100:
                df = pd.read_csv(io.StringIO(res.text), on_bad_lines='skip')
                col_rename = {'Home': 'HomeTeam', 'Away': 'AwayTeam', 'HG': 'FTHG', 'AG': 'FTAG', 'Res': 'FTR'}
                df = df.rename(columns=col_rename)
                if 'HomeTeam' in df.columns and 'AwayTeam' in df.columns:
                    break
        except Exception:
            continue
    if df is not None and not df.empty:
        df = df.dropna(subset=['HomeTeam', 'AwayTeam'])
    return df

df_matches = fetch_data(league_code, season_code)

def calculate_league_table(df):
    if df is None or df.empty:
        return None
    df_played = df.dropna(subset=['FTHG', 'FTAG']).copy()
    teams = sorted(list(set(df_played['HomeTeam'].astype(str).str.strip().tolist()) |
                        set(df_played['AwayTeam'].astype(str).str.strip().tolist())))
    table_data = []
    for team in teams:
        team_df = df_played[(df_played['HomeTeam'] == team) | (df_played['AwayTeam'] == team)]
        matches = len(team_df)
        pts, gf_total, ga_total = 0, 0, 0
        for _, row in team_df.iterrows():
            is_home = (row['HomeTeam'] == team)
            gf = int(row['FTHG'] if is_home else row['FTAG'])
            ga = int(row['FTAG'] if is_home else row['FTHG'])
            res = str(row.get('FTR', '')).upper()
            gf_total += gf
            ga_total += ga
            if (is_home and res == 'H') or (not is_home and res == 'A'):
                pts += 3
            elif res == 'D':
                pts += 1
        table_data.append({
            'team': team,
            'matches': matches,
            'pts': pts,
            'gd': gf_total - ga_total,
            'gf': gf_total,
            'ga': ga_total
        })
    table_df = pd.DataFrame(table_data)
    table_df = table_df.sort_values(by=['pts', 'gd', 'gf'], ascending=[False, False, False]).reset_index(drop=True)
    table_df['pos'] = table_df.index + 1
    return table_df

if df_matches is not None and not df_matches.empty:
    teams = sorted(list(set(df_matches['HomeTeam'].astype(str).str.strip().tolist()) |
                        set(df_matches['AwayTeam'].astype(str).str.strip().tolist())))
    
    selected_team = st.sidebar.selectbox("Wybierz Drużynę:", teams)
    x_matches = st.sidebar.slider("Analiza ostatnich meczów:", 1, 50, 5)

    # Obliczanie pozycji w tabeli
    table_df = calculate_league_table(df_matches)
    if table_df is not None:
        team_row = table_df[table_df['team'] == selected_team]
        if not team_row.empty:
            pos = team_row.iloc[0]['pos']
            pts = team_row.iloc[0]['pts']
            m = team_row.iloc[0]['matches']
            total_teams = len(table_df)
            pos_text = f"**{pos}. miejsce** na {total_teams} zespołów | **{pts} pkt** w {m} meczach"
        else:
            pos_text = "Brak danych w tabeli ligowej."
    else:
        pos_text = "Brak danych w tabeli ligowej."

    # SEKCJA: POZYCJA W TABELI LIGOWEJ
    st.markdown(f"""
    <div class="pos-box">
        <span style="color: #38BDF8; font-size: 12px; font-weight: bold;">🏆 AKTUALNA POZYCJA W TABELI LIGOWEJ</span><br>
        <span style="font-size: 18px; font-weight: bold; color: #FFFFFF;">{pos_text}</span>
    </div>
    """, unsafe_allow_html=True)

    # ZAKŁADKI
    tab1, tab2, tab3 = st.tabs([
        "📊 Przegląd Średnich Statystyk", 
        "🏆 Porównanie Wszystkich Drużyn Ligi", 
        "📅 Lista Ostatnich Meczów"
    ])

    current_team_matches = df_matches[(df_matches['HomeTeam'] == selected_team) | (df_matches['AwayTeam'] == selected_team)].copy()
    latest = current_team_matches.tail(x_matches)

    # ================= ZAKŁADKA 1: KAFELKI ŚREDNICH =================
    with tab1:
        if not latest.empty:
            g_scored, g_conceded = 0, 0
            yellows, reds = 0, 0
            shots, shots_target = 0, 0
            fouls, corners = 0, 0
            wins, draws, losses = 0, 0, 0
            btts_count = 0

            for _, row in latest.iterrows():
                is_home = (row['HomeTeam'] == selected_team)
                gf = int(row['FTHG'] if is_home else row['FTAG']) if pd.notnull(row.get('FTHG')) else 0
                ga = int(row['FTAG'] if is_home else row['FTHG']) if pd.notnull(row.get('FTAG')) else 0

                if gf > 0 and ga > 0:
                    btts_count += 1

                hy = int(row.get('HY', 0)) if is_home else int(row.get('AY', 0))
                hr = int(row.get('HR', 0)) if is_home else int(row.get('AR', 0))
                st_val = int(row.get('HST', 0)) if is_home else int(row.get('AST', 0))
                sh = int(row.get('HS', 0)) if is_home else int(row.get('AS', 0))
                fl = int(row.get('HF', 0)) if is_home else int(row.get('AF', 0))
                cr = int(row.get('HC', 0)) if is_home else int(row.get('AC', 0))

                g_scored += gf; g_conceded += ga
                yellows += (hy if pd.notnull(hy) else 0)
                reds += (hr if pd.notnull(hr) else 0)
                shots_target += (st_val if pd.notnull(st_val) else 0)
                shots += (sh if pd.notnull(sh) else 0)
                fouls += (fl if pd.notnull(fl) else 0)
                corners += (cr if pd.notnull(cr) else 0)

                res = str(row.get('FTR', '')).upper()
                if (is_home and res == 'H') or (not is_home and res == 'A'):
                    wins += 1
                elif res == 'D':
                    draws += 1
                else:
                    losses += 1

            n = len(latest)
            pts_period = (wins * 3) + draws
            btts_pct = (btts_count / n) * 100
            acc = (shots_target / shots * 100) if shots > 0 else 0

            r1_c1, r1_c2 = st.columns(2)
            r1_c1.metric("⚽ GOLE STRZELONE / STRACONE", f"{g_scored} / {g_conceded}", f"Średnia: {g_scored/n:.2f} strzel / {g_conceded/n:.2f} strac na mecz", delta_color="off")
            r1_c2.metric("🤝 BTTS (OBIE STRZELĄ)", f"{btts_count} / {n} meczów", f"Częstotliwość BTTS: {btts_pct:.1f}%", delta_color="off")

            r2_c1, r2_c2 = st.columns(2)
            r2_c1.metric("🎯 STRZAŁY NA MECZ", f"{shots/n:.2f}", f"Średnia celnych: {shots_target/n:.2f} na mecz (Celność: {acc:.1f}%)", delta_color="off")
            r2_c2.metric("🟨🟫 KARTKI NA MECZ", f"{(yellows+reds)/n:.2f}", f"Suma: {yellows} 🟨 żółtych | {reds} 🟥 czerwonych w okresie", delta_color="off")

            r3_c1, r3_c2 = st.columns(2)
            r3_c1.metric("⚠️ FAULE NA MECZ", f"{fouls/n:.2f}", f"Łącznie popełniono fauli: {fouls}", delta_color="off")
            r3_c2.metric("🚩 RZUTY ROŻNE NA MECZ", f"{corners/n:.2f}", f"Łącznie wykonano rzutów rożnych: {corners}", delta_color="off")

            st.metric("📊 BILANS & PUNKTACJA", f"{wins}Z - {draws}R - {losses}P", f"Zdobyte punkty w okresie: {pts_period} pkt", delta_color="off")

    # ================= ZAKŁADKA 2: PORÓWNANIE ALL TEAMS =================
    with tab2:
        if table_df is not None:
            pos_map = dict(zip(table_df['team'], table_df['pos']))
            comparison_rows = []

            for team_item in teams:
                t_df = df_matches[(df_matches['HomeTeam'] == team_item) | (df_matches['AwayTeam'] == team_item)].tail(x_matches)
                n_matches = len(t_df)
                if n_matches == 0:
                    continue

                gf_sum, ga_sum = 0, 0
                sh_sum, st_sum = 0, 0
                cards_sum, fl_sum, cr_sum = 0, 0, 0
                btts_cnt = 0

                for _, row in t_df.iterrows():
                    is_home = (row['HomeTeam'] == team_item)
                    gf = int(row['FTHG'] if is_home else row['FTAG']) if pd.notnull(row.get('FTHG')) else 0
                    ga = int(row['FTAG'] if is_home else row['FTHG']) if pd.notnull(row.get('FTAG')) else 0

                    if gf > 0 and ga > 0:
                        btts_cnt += 1

                    hy = int(row.get('HY', 0)) if is_home else int(row.get('AY', 0))
                    hr = int(row.get('HR', 0)) if is_home else int(row.get('AR', 0))
                    st_val = int(row.get('HST', 0)) if is_home else int(row.get('AST', 0))
                    sh = int(row.get('HS', 0)) if is_home else int(row.get('AS', 0))
                    fl = int(row.get('HF', 0)) if is_home else int(row.get('AF', 0))
                    cr = int(row.get('HC', 0)) if is_home else int(row.get('AC', 0))

                    gf_sum += gf; ga_sum += ga
                    sh_sum += (sh if pd.notnull(sh) else 0)
                    st_sum += (st_val if pd.notnull(st_val) else 0)
                    cards_sum += ((hy if pd.notnull(hy) else 0) + (hr if pd.notnull(hr) else 0))
                    fl_sum += (fl if pd.notnull(fl) else 0)
                    cr_sum += (cr if pd.notnull(cr) else 0)

                comparison_rows.append({
                    "Poz.": int(pos_map.get(team_item, 999)),
                    "Drużyna": team_item,
                    "Mecze": n_matches,
                    "Gole Strz. / mecz": round(gf_sum / n_matches, 2),
                    "Gole Strac. / mecz": round(ga_sum / n_matches, 2),
                    "BTTS %": round((btts_cnt / n_matches) * 100, 1),
                    "Strzały / mecz": round(sh_sum / n_matches, 2),
                    "Celne / mecz": round(st_sum / n_matches, 2),
                    "Kartki / mecz": round(cards_sum / n_matches, 2),
                    "Faule / mecz": round(fl_sum / n_matches, 2),
                    "Rożne / mecz": round(cr_sum / n_matches, 2)
                })

            comp_df = pd.DataFrame(comparison_rows).sort_values(by="Poz.")
            st.dataframe(comp_df, use_container_width=True, hide_index=True)

    # ================= ZAKŁADKA 3: LISTA MECZÓW =================
    with tab3:
        if not latest.empty:
            matches_rows = []
            for _, row in latest.iterrows():
                is_home = (row['HomeTeam'] == selected_team)
                opp = row['AwayTeam'] if is_home else row['HomeTeam']

                gf = int(row['FTHG'] if is_home else row['FTAG']) if pd.notnull(row.get('FTHG')) else 0
                ga = int(row['FTAG'] if is_home else row['FTHG']) if pd.notnull(row.get('FTAG')) else 0

                is_btts = (gf > 0 and ga > 0)
                hy = int(row.get('HY', 0)) if is_home else int(row.get('AY', 0))
                hr = int(row.get('HR', 0)) if is_home else int(row.get('AR', 0))
                st_val = int(row.get('HST', 0)) if is_home else int(row.get('AST', 0))
                sh = int(row.get('HS', 0)) if is_home else int(row.get('AS', 0))
                fl = int(row.get('HF', 0)) if is_home else int(row.get('AF', 0))

                hy = hy if pd.notnull(hy) else 0
                hr = hr if pd.notnull(hr) else 0
                st_val = st_val if pd.notnull(st_val) else 0
                sh = sh if pd.notnull(sh) else 0
                fl = fl if pd.notnull(fl) else 0

                res = str(row.get('FTR', '')).upper()
                if (is_home and res == 'H') or (not is_home and res == 'A'):
                    result_str = "Zwycięstwo"
                elif res == 'D':
                    result_str = "Remis"
                else:
                    result_str = "Porażka"

                matches_rows.append({
                    "Data": str(row.get('Date', '')),
                    "Przeciwnik": str(opp),
                    "Miejsce": "Dom" if is_home else "Wyjazd",
                    "Wynik": result_str,
                    "Gole": f"{gf} : {ga}",
                    "BTTS": "TAK" if is_btts else "NIE",
                    "Strzały (Celne)": f"{sh} ({st_val})",
                    "Faule": str(fl),
                    "Kartki (Ż/C)": f"{hy} 🟨 / {hr} 🟥"
                })

            matches_df = pd.DataFrame(matches_rows)

            # Funkcja kolorująca wyniki tak jak w PyQt6
            def color_results(val):
                if val == 'Zwycięstwo':
                    return 'background-color: #059669; color: white'
                elif val == 'Remis':
                    return 'background-color: #4B5563; color: white'
                elif val == 'Porażka':
                    return 'background-color: #DC2626; color: white'
                return ''

            def color_btts(val):
                if val == 'TAK':
                    return 'color: #34D399; font-weight: bold'
                elif val == 'NIE':
                    return 'color: #F87171; font-weight: bold'
                return ''

            styled_matches = matches_df.style.map(color_results, subset=['Wynik'])\
                                             .map(color_btts, subset=['BTTS'])

            st.dataframe(styled_matches, use_container_width=True, hide_index=True)

else:
    st.error("Wybierz ligę i pobierz dane.")
