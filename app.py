import io
import sys
from threading import Thread
import pandas as pd
import requests

from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QSlider, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QTabWidget, QMessageBox, QGridLayout
)


class NumericTableWidgetItem(QTableWidgetItem):
    """Specjalna komórka do poprawnego sortowania wartości liczbowych."""
    def __init__(self, value, display_text=None):
        super().__init__(display_text if display_text is not None else str(value))
        self.sort_value = value

    def __lt__(self, other):
        if isinstance(other, NumericTableWidgetItem):
            return self.sort_value < other.sort_value
        return super().__lt__(other)


class WorkerSignals(QObject):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)


class FootballAppPRO(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MaxStats - Twój Asystent Piłkarski")
        self.resize(1350, 900)

        self.df_matches = None
        self.current_team_matches = None

        # Lista lig krajowych (bez Ekstraklasy)
        self.competitions_map = {
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

        self.init_ui()
        self.apply_custom_styles()

    def get_current_season_code(self):
        now = pd.Timestamp.now()
        year = now.year
        if now.month < 7:
            start_year = year - 1
            end_year = year
        else:
            start_year = year
            end_year = year + 1
        return f"{str(start_year)[-2:]}{str(end_year)[-2:]}"

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # ================= PANEL BOCZNY =================
        sidebar = QFrame()
        sidebar.setFixedWidth(290)
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(15, 20, 15, 20)

        sidebar_layout.addWidget(QLabel("⚽ Wybór Rozgrywek", font=QFont("Arial", 14, QFont.Weight.Bold)))

        self.combo_league = QComboBox()
        self.combo_league.addItems(list(self.competitions_map.keys()))
        sidebar_layout.addWidget(self.combo_league)

        self.btn_load = QPushButton("🔄 Pobierz Aktualne Dane")
        self.btn_load.clicked.connect(self.start_loading)
        sidebar_layout.addWidget(self.btn_load)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        sidebar_layout.addWidget(line)

        sidebar_layout.addWidget(QLabel("Wybierz Drużynę:"))
        self.combo_team = QComboBox()
        self.combo_team.addItem("Najpierw pobierz dane")
        self.combo_team.currentTextChanged.connect(self.on_team_selected)
        sidebar_layout.addWidget(self.combo_team)

        sidebar_layout.addSpacing(15)
        self.lbl_slider = QLabel("Analiza ostatnich meczów: 5")
        self.lbl_slider.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        sidebar_layout.addWidget(self.lbl_slider)

        self.slider_matches = QSlider(Qt.Orientation.Horizontal)
        self.slider_matches.setMinimum(1)
        self.slider_matches.setMaximum(50)
        self.slider_matches.setValue(5)

        self.slider_matches.valueChanged.connect(self.on_slider_move)
        self.slider_matches.sliderReleased.connect(self.on_slider_release)

        sidebar_layout.addWidget(self.slider_matches)

        sidebar_layout.addStretch()

        self.lbl_status = QLabel("Wybierz ligę i pobierz dane.")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("color: #00E676; font-size: 11px;")
        sidebar_layout.addWidget(self.lbl_status)

        main_layout.addWidget(sidebar)

        # ================= PANEL GŁÓWNY =================
        content_panel = QVBoxLayout()

        # SEKCJA: POZYCJA W TABELI LIGOWEJ
        self.card_league_pos = QFrame()
        self.card_league_pos.setObjectName("pos_card")
        pos_layout = QVBoxLayout(self.card_league_pos)
        pos_layout.setContentsMargins(15, 10, 15, 10)

        self.lbl_pos_title = QLabel("🏆 AKTUALNA POZYCJA W TABELI LIGOWEJ")
        self.lbl_pos_title.setStyleSheet("color: #38BDF8; font-size: 11px; font-weight: bold;")

        self.lbl_pos_info = QLabel("Pobierz dane, aby sprawdzić pozycję drużyny w tabeli.")
        self.lbl_pos_info.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFFFF;")

        pos_layout.addWidget(self.lbl_pos_title)
        pos_layout.addWidget(self.lbl_pos_info)

        content_panel.addWidget(self.card_league_pos)

        self.tabs = QTabWidget()

        # ZAKŁADKA 1: KAFELKI ŚREDNICH
        self.tab_dashboard = QWidget()
        dash_layout = QVBoxLayout(self.tab_dashboard)

        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(15)

        self.card_goals = self.create_big_card("⚽ GOLE STRZELONE / STRACONE", "0 / 0",
                                               "Średnia strzelonych: 0.00 / mecz")
        self.card_btts = self.create_big_card("🤝 BTTS (OBIE STRZELĄ)", "0 / 0 meczów", "Procent meczów z BTTS: 0%")
        self.card_shots = self.create_big_card("🎯 STRZAŁY NA MECZ", "0.00", "Średnia celnych: 0.00 (Celność: 0%)")
        self.card_cards = self.create_big_card("🟨🟫 KARTKI NA MECZ", "0.00", "Suma kartek: 0 żółtych | 0 czerwonych")
        self.card_fouls = self.create_big_card("⚠️ FAULE NA MECZ", "0.00", "Łącznie fauli w okresie: 0")
        self.card_corners = self.create_big_card("🚩 RZUTY ROŻNE NA MECZ", "0.00", "Suma rożnych w okresie: 0")
        self.card_form = self.create_big_card("📊 BILANS & PUNKTACJA", "0Z - 0R - 0P", "Zdobyte punkty: 0")

        self.grid_layout.addWidget(self.card_goals, 0, 0)
        self.grid_layout.addWidget(self.card_btts, 0, 1)
        self.grid_layout.addWidget(self.card_shots, 1, 0)
        self.grid_layout.addWidget(self.card_cards, 1, 1)
        self.grid_layout.addWidget(self.card_fouls, 2, 0)
        self.grid_layout.addWidget(self.card_corners, 2, 1)
        self.grid_layout.addWidget(self.card_form, 3, 0, 1, 2)

        dash_layout.addLayout(self.grid_layout)
        self.tabs.addTab(self.tab_dashboard, "📊 Przegląd Średnich Statystyk")

        # ZAKŁADKA 2: PORÓWNANIE I TABELA LIGOWA
        self.tab_all_teams = QWidget()
        tab_all_layout = QVBoxLayout(self.tab_all_teams)
        self.table_all_teams = QTableWidget()
        self.setup_table_comparison(self.table_all_teams, [
            "Poz.", "Drużyna", "Mecze", "Gole Strz.\n/ mecz", "Gole Strac.\n/ mecz", "BTTS %", "Strzały\n/ mecz",
            "Celne\n/ mecz", "Kartki\n/ mecz", "Faule\n/ mecz", "Rożne\n/ mecz"
        ])
        tab_all_layout.addWidget(self.table_all_teams)
        self.tabs.addTab(self.tab_all_teams, "🏆 Porównanie Wszystkich Drużyn Ligi")

        # ZAKŁADKA 3: TABELA MECZÓW
        self.tab_matches = QWidget()
        tab3_layout = QVBoxLayout(self.tab_matches)
        self.table_matches = QTableWidget()
        self.setup_table_matches(self.table_matches, [
            "Data", "Przeciwnik", "Miejsce", "Wynik", "Gole", "BTTS", "Strzały (Celne)", "Faule", "Kartki (Ż/C)"
        ])
        tab3_layout.addWidget(self.table_matches)
        self.tabs.addTab(self.tab_matches, "📅 Lista Ostatnich Meczów")

        content_panel.addWidget(self.tabs)
        main_layout.addLayout(content_panel)

    def create_big_card(self, title, main_val, sub_val):
        card = QFrame()
        card.setObjectName("big_card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 12, 15, 12)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("color: #80D8FF; font-size: 11px; font-weight: bold;")
        lbl_m = QLabel(main_val)
        lbl_m.setStyleSheet("font-size: 22px; font-weight: bold; color: #FFFFFF; margin: 3px 0;")
        lbl_s = QLabel(sub_val)
        lbl_s.setStyleSheet("color: #B0BEC5; font-size: 12px;")

        layout.addWidget(lbl_t)
        layout.addWidget(lbl_m)
        layout.addWidget(lbl_s)

        card.lbl_main = lbl_m
        card.lbl_sub = lbl_s
        return card

    def setup_table_comparison(self, table, headers):
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)

        table.setWordWrap(True)
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setFixedHeight(45)

        table.setAlternatingRowColors(True)
        table.setSortingEnabled(True)

    def setup_table_matches(self, table, headers):
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setAlternatingRowColors(True)

    def start_loading(self):
        self.lbl_status.setText("Pobieranie danych...")
        self.btn_load.setEnabled(False)

        self.signals = WorkerSignals()
        self.signals.finished.connect(self.on_data_loaded)
        self.signals.error.connect(self.on_data_error)

        Thread(target=self.fetch_data_thread, daemon=True).start()

    def fetch_data_thread(self):
        try:
            league_name = self.combo_league.currentText()
            league_code = self.competitions_map[league_name]
            season_code = self.get_current_season_code()

            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

            urls_to_try = [
                f"https://www.football-data.co.uk/mmz4281/{season_code}/{league_code}.csv",
                f"https://www.football-data.co.uk/new/{league_code}.csv"
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

            if df is None or df.empty:
                raise Exception("Brak danych z serwera.")

            df = df.dropna(subset=['HomeTeam', 'AwayTeam'])

            self.signals.finished.emit(df)
        except Exception as e:
            self.signals.error.emit(str(e))

    def calculate_league_table(self):
        if self.df_matches is None or self.df_matches.empty:
            return None

        df_played = self.df_matches.dropna(subset=['FTHG', 'FTAG']).copy()
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

            gd = gf_total - ga_total
            table_data.append({
                'team': team,
                'matches': matches,
                'pts': pts,
                'gd': gd,
                'gf': gf_total,
                'ga': ga_total
            })

        table_df = pd.DataFrame(table_data)
        table_df = table_df.sort_values(by=['pts', 'gd', 'gf'], ascending=[False, False, False]).reset_index(drop=True)
        table_df['pos'] = table_df.index + 1
        return table_df

    def on_data_loaded(self, df):
        self.btn_load.setEnabled(True)
        self.df_matches = df

        teams = sorted(list(set(df['HomeTeam'].astype(str).str.strip().tolist()) |
                            set(df['AwayTeam'].astype(str).str.strip().tolist())))

        self.combo_team.blockSignals(True)
        self.combo_team.clear()
        self.combo_team.addItems(teams)
        self.combo_team.blockSignals(False)

        self.lbl_status.setText(f"Wczytano {len(df)} meczów!")
        self.update_all_teams_comparison()
        self.on_team_selected(teams[0])

    def on_data_error(self, err):
        self.btn_load.setEnabled(True)
        self.lbl_status.setText("Błąd pobierania danych.")
        QMessageBox.warning(self, "Uwaga", f"Szczegóły: {err}")

    def on_team_selected(self, team_name):
        if self.df_matches is None or not team_name:
            return

        df = self.df_matches
        self.current_team_matches = df[(df['HomeTeam'] == team_name) | (df['AwayTeam'] == team_name)].copy()

        table_df = self.calculate_league_table()
        if table_df is not None:
            team_row = table_df[table_df['team'] == team_name]
            if not team_row.empty:
                pos = team_row.iloc[0]['pos']
                pts = team_row.iloc[0]['pts']
                m = team_row.iloc[0]['matches']
                total_teams = len(table_df)
                self.lbl_pos_info.setText(f"{pos}. miejsce na {total_teams} zespołów  |  {pts} pkt w {m} meczach")
            else:
                self.lbl_pos_info.setText("Brak danych w tabeli ligowej.")

        self.update_analysis()

    def on_slider_move(self, val):
        self.lbl_slider.setText(f"Analiza ostatnich meczów: {val}")
        self.update_analysis()

    def on_slider_release(self):
        if self.df_matches is not None:
            self.update_all_teams_comparison()

    def update_all_teams_comparison(self):
        if self.df_matches is None or self.df_matches.empty:
            return

        df = self.df_matches
        x_matches = self.slider_matches.value()
        table_df = self.calculate_league_table()

        if table_df is None:
            return

        pos_map = dict(zip(table_df['team'], table_df['pos']))
        teams = sorted(list(set(df['HomeTeam'].astype(str).str.strip().tolist()) |
                            set(df['AwayTeam'].astype(str).str.strip().tolist())))

        self.table_all_teams.setSortingEnabled(False)
        self.table_all_teams.setRowCount(0)

        for row_idx, team in enumerate(teams):
            team_df = df[(df['HomeTeam'] == team) | (df['AwayTeam'] == team)].tail(x_matches)
            n = len(team_df)
            if n == 0:
                continue

            gf_sum, ga_sum = 0, 0
            sh_sum, st_sum = 0, 0
            cards_sum, fl_sum, cr_sum = 0, 0, 0
            btts_cnt = 0

            for _, row in team_df.iterrows():
                is_home = (row['HomeTeam'] == team)
                gf = int(row['FTHG'] if is_home else row['FTAG']) if pd.notnull(row.get('FTHG')) else 0
                ga = int(row['FTAG'] if is_home else row['FTHG']) if pd.notnull(row.get('FTAG')) else 0

                if gf > 0 and ga > 0:
                    btts_cnt += 1

                hy = int(row.get('HY', 0)) if is_home else int(row.get('AY', 0))
                hr = int(row.get('HR', 0)) if is_home else int(row.get('AR', 0))
                st = int(row.get('HST', 0)) if is_home else int(row.get('AST', 0))
                sh = int(row.get('HS', 0)) if is_home else int(row.get('AS', 0))
                fl = int(row.get('HF', 0)) if is_home else int(row.get('AF', 0))
                cr = int(row.get('HC', 0)) if is_home else int(row.get('AC', 0))

                gf_sum += gf
                ga_sum += ga
                sh_sum += (sh if pd.notnull(sh) else 0)
                st_sum += (st if pd.notnull(st) else 0)
                cards_sum += ((hy if pd.notnull(hy) else 0) + (hr if pd.notnull(hr) else 0))
                fl_sum += (fl if pd.notnull(fl) else 0)
                cr_sum += (cr if pd.notnull(cr) else 0)

            self.table_all_teams.insertRow(row_idx)

            pos_val = int(pos_map.get(team, 999))
            btts_pct = (btts_cnt / n) * 100

            # Używamy NumericTableWidgetItem do poprawnego sortowania cyfrowego
            items = [
                NumericTableWidgetItem(pos_val, str(pos_val)),
                QTableWidgetItem(team),
                NumericTableWidgetItem(n, str(n)),
                NumericTableWidgetItem(gf_sum / n, f"{gf_sum / n:.2f}"),
                NumericTableWidgetItem(ga_sum / n, f"{ga_sum / n:.2f}"),
                NumericTableWidgetItem(btts_pct, f"{btts_pct:.1f}%"),
                NumericTableWidgetItem(sh_sum / n, f"{sh_sum / n:.2f}"),
                NumericTableWidgetItem(st_sum / n, f"{st_sum / n:.2f}"),
                NumericTableWidgetItem(cards_sum / n, f"{cards_sum / n:.2f}"),
                NumericTableWidgetItem(fl_sum / n, f"{fl_sum / n:.2f}"),
                NumericTableWidgetItem(cr_sum / n, f"{cr_sum / n:.2f}"),
            ]

            for c_idx, item in enumerate(items):
                if c_idx != 1:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_all_teams.setItem(row_idx, c_idx, item)

        self.table_all_teams.setSortingEnabled(True)

    def update_analysis(self):
        if self.current_team_matches is None or self.current_team_matches.empty:
            return

        team = self.combo_team.currentText()
        x_matches = self.slider_matches.value()
        latest = self.current_team_matches.tail(x_matches)

        g_scored, g_conceded = 0, 0
        yellows, reds = 0, 0
        shots, shots_target = 0, 0
        fouls, corners = 0, 0
        wins, draws, losses = 0, 0, 0
        btts_count = 0

        self.table_matches.setRowCount(0)

        for i, (_, row) in enumerate(latest.iterrows()):
            is_home = (row['HomeTeam'] == team)
            opp = row['AwayTeam'] if is_home else row['HomeTeam']

            gf = int(row['FTHG'] if is_home else row['FTAG']) if pd.notnull(row.get('FTHG')) else 0
            ga = int(row['FTAG'] if is_home else row['FTHG']) if pd.notnull(row.get('FTAG')) else 0

            is_btts = (gf > 0 and ga > 0)
            if is_btts:
                btts_count += 1

            hy = int(row.get('HY', 0)) if is_home else int(row.get('AY', 0))
            hr = int(row.get('HR', 0)) if is_home else int(row.get('AR', 0))
            st = int(row.get('HST', 0)) if is_home else int(row.get('AST', 0))
            sh = int(row.get('HS', 0)) if is_home else int(row.get('AS', 0))
            fl = int(row.get('HF', 0)) if is_home else int(row.get('AF', 0))
            cr = int(row.get('HC', 0)) if is_home else int(row.get('AC', 0))

            hy = hy if pd.notnull(hy) else 0
            hr = hr if pd.notnull(hr) else 0
            st = st if pd.notnull(st) else 0
            sh = sh if pd.notnull(sh) else 0
            fl = fl if pd.notnull(fl) else 0
            cr = cr if pd.notnull(cr) else 0

            g_scored += gf
            g_conceded += ga
            yellows += hy
            reds += hr
            shots_target += st
            shots += sh
            fouls += fl
            corners += cr

            res = str(row.get('FTR', '')).upper()
            if (is_home and res == 'H') or (not is_home and res == 'A'):
                wins += 1
                result_str = "Zwycięstwo"
                res_bg_color = QColor("#059669")
            elif res == 'D':
                draws += 1
                result_str = "Remis"
                res_bg_color = QColor("#4B5563")
            else:
                losses += 1
                result_str = "Porażka"
                res_bg_color = QColor("#DC2626")

            self.table_matches.insertRow(i)

            item_date = QTableWidgetItem(str(row.get('Date', '')))
            item_opp = QTableWidgetItem(str(opp))
            item_venue = QTableWidgetItem("Dom" if is_home else "Wyjazd")

            item_res = QTableWidgetItem(result_str)
            item_res.setBackground(res_bg_color)
            item_res.setForeground(QColor("#FFFFFF"))

            item_goals = QTableWidgetItem(f"{gf} : {ga}")
            item_btts = QTableWidgetItem("TAK" if is_btts else "NIE")
            item_btts.setForeground(QColor("#34D399") if is_btts else QColor("#F87171"))

            item_shots = QTableWidgetItem(f"{sh} ({st})")
            item_fouls = QTableWidgetItem(str(fl))
            item_cards = QTableWidgetItem(f"{hy} 🟨 / {hr} 🟥")

            for col_idx, item in enumerate(
                    [item_date, item_opp, item_venue, item_res, item_goals, item_btts, item_shots, item_fouls,
                     item_cards]):
                if col_idx != 1:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_matches.setItem(i, col_idx, item)

        n = len(latest)
        if n == 0:
            return

        pts = (wins * 3) + draws

        self.card_goals.lbl_main.setText(f"{g_scored} : {g_conceded}")
        self.card_goals.lbl_sub.setText(f"Średnia: {g_scored / n:.2f} strzel / {g_conceded / n:.2f} strac na mecz")

        btts_pct = (btts_count / n) * 100
        self.card_btts.lbl_main.setText(f"{btts_count} / {n} meczów")
        self.card_btts.lbl_sub.setText(f"Częstotliwość BTTS: {btts_pct:.1f}%")

        acc = (shots_target / shots * 100) if shots > 0 else 0
        self.card_shots.lbl_main.setText(f"{shots / n:.2f} / mecz")
        self.card_shots.lbl_sub.setText(f"Średnia celnych: {shots_target / n:.2f} na mecz (Celność: {acc:.1f}%)")

        self.card_cards.lbl_main.setText(f"{(yellows + reds) / n:.2f} / mecz")
        self.card_cards.lbl_sub.setText(f"Suma: {yellows} 🟨 żółtych | {reds} 🟥 czerwonych w okresie")

        self.card_fouls.lbl_main.setText(f"{fouls / n:.2f} fauli / mecz")
        self.card_fouls.lbl_sub.setText(f"Łącznie popełniono fauli: {fouls}")

        self.card_corners.lbl_main.setText(f"{corners / n:.2f} rożnych / mecz")
        self.card_corners.lbl_sub.setText(f"Łącznie wykonano rzutów rożnych: {corners}")

        self.card_form.lbl_main.setText(f"{wins}Z - {draws}R - {losses}P")
        self.card_form.lbl_sub.setText(f"Zdobyte punkty w okresie: {pts} pkt")

    def apply_custom_styles(self):
        qss = """
        QMainWindow { background-color: #0F172A; }
        QWidget { color: #F8FAFC; font-family: 'Segoe UI', Arial; }
        QFrame#sidebar { background-color: #1E293B; border-radius: 12px; }
        QFrame#pos_card { background-color: #1E293B; border-radius: 12px; border: 1px solid #0284C7; }
        QFrame#big_card { background-color: #1E293B; border-radius: 12px; border: 1px solid #334155; }
        QFrame#big_card:hover { border: 1px solid #38BDF8; }
        QComboBox, QPushButton {
            background-color: #334155; border: 1px solid #475569;
            border-radius: 6px; padding: 8px; color: #FFF; font-weight: bold;
        }
        QPushButton { background-color: #0284C7; }
        QPushButton:hover { background-color: #0369A1; }
        QTableWidget {
            background-color: #1E293B; gridline-color: #334155;
            border-radius: 10px; selection-background-color: #0369A1;
        }
        QHeaderView::section {
            background-color: #0F172A; color: #38BDF8;
            padding: 4px; border: none; font-weight: bold;
        }
        QTabBar::tab {
            background: #1E293B; padding: 10px 20px;
            border-top-left-radius: 8px; border-top-right-radius: 8px;
            margin-right: 4px; color: #94A3B8;
        }
        QTabBar::tab:selected { background: #0284C7; color: #FFF; font-weight: bold; }
        """
        self.setStyleSheet(qss)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FootballAppPRO()
    window.show()
    sys.exit(app.exec())