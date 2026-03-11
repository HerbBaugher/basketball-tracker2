import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import math

st.set_page_config(
    page_title="College Basketball Team Comparison",
    page_icon="🏀",
    layout="centered"
)

BASE_SITE_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball"
BASE_STATS_URL = "https://sports.core.api.espn.com/v2/sports/basketball/leagues/mens-college-basketball"

IMPORTANT_STATS = {
    "avgPoints": "Points Per Game",
    "avgRebounds": "Rebounds Per Game",
    "avgAssists": "Assists Per Game",
    "fieldGoalPct": "Field Goal %",
    "threePointFieldGoalPct": "3PT %",
}


# ---------------------------------------------------------
# Load Teams
# ---------------------------------------------------------
@st.cache_data
def load_teams():
    teams = {}

    try:
        url = f"{BASE_SITE_URL}/teams?limit=500"
        response = requests.get(url, timeout=10)
        data = response.json()

        sports = data.get("sports", [])
        leagues = sports[0].get("leagues", [])

        for item in leagues[0].get("teams", []):
            team = item.get("team", {})
            name = team.get("displayName")
            team_id = team.get("id")

            if name and team_id:
                teams[name] = team_id

        return dict(sorted(teams.items()))

    except:
        return {}


# ---------------------------------------------------------
# Fetch Stats
# ---------------------------------------------------------
def get_team_stats(team_id, season):

    url = f"{BASE_STATS_URL}/seasons/{season}/types/2/teams/{team_id}/statistics"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None

        data = response.json()
        stats = {}

        for category in data.get("splits", {}).get("categories", []):
            for stat in category.get("stats", []):
                if stat.get("name") in IMPORTANT_STATS:
                    value = stat.get("displayValue", "0").replace("%", "")
                    try:
                        stats[stat["name"]] = float(value)
                    except:
                        stats[stat["name"]] = 0

        return stats

    except:
        return None


# ---------------------------------------------------------
# Fetch Record
# ---------------------------------------------------------
def get_team_record(team_id, season):

    try:
        url = f"{BASE_SITE_URL}/teams/{team_id}?season={season}"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            return "N/A"

        data = response.json()
        record_items = data.get("team", {}).get("record", {}).get("items", [])

        if record_items:
            return record_items[0].get("summary", "N/A")

        return "N/A"

    except:
        return "N/A"


# ---------------------------------------------------------
# Win Probability Model
# ---------------------------------------------------------
def calculate_win_probability(stats1, stats2):

    weights = {
        "avgPoints": 1.2,
        "avgRebounds": 0.8,
        "avgAssists": 0.7,
        "fieldGoalPct": 1.0,
        "threePointFieldGoalPct": 1.0,
    }

    score1 = sum(stats1.get(stat, 0) * w for stat, w in weights.items())
    score2 = sum(stats2.get(stat, 0) * w for stat, w in weights.items())

    diff = score1 - score2
    prob1 = 1 / (1 + math.exp(-diff / 10))
    prob2 = 1 - prob1

    return prob1 * 100, prob2 * 100


# ---------------------------------------------------------
# Page Title
# ---------------------------------------------------------
st.title("🏀 College Basketball Team Comparison")
st.write("Compare Division I college basketball teams using ESPN statistics.")

teams = load_teams()

if not teams:
    st.error("Unable to load teams from ESPN API.")
    st.stop()

team_list = list(teams.keys())

# ---------------------------------------------------------
# Mobile Friendly Inputs
# ---------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    team1 = st.selectbox("Team 1", team_list)

with col2:
    team2 = st.selectbox("Team 2", team_list)

season = st.number_input("Season Year", min_value=2000, max_value=2100, value=2024)

# ---------------------------------------------------------
# Compare Button
# ---------------------------------------------------------
if st.button("Compare Teams"):

    with st.spinner("Fetching team stats..."):

        stats1 = get_team_stats(teams[team1], season)
        stats2 = get_team_stats(teams[team2], season)

        if not stats1 or not stats2:
            st.error("Stats unavailable for that season.")
            st.stop()

        record1 = get_team_record(teams[team1], season)
        record2 = get_team_record(teams[team2], season)

    # -----------------------------------------------------
    # Win Probability
    # -----------------------------------------------------
    prob1, prob2 = calculate_win_probability(stats1, stats2)
    winner = team1 if prob1 > prob2 else team2

    st.subheader("Team Records")

    rec_col1, rec_col2 = st.columns(2)

    with rec_col1:
        st.metric(team1, record1)

    with rec_col2:
        st.metric(team2, record2)

    st.subheader("Win Probability")

    prob_col1, prob_col2 = st.columns(2)

    with prob_col1:
        st.metric(team1, f"{prob1:.1f}%")

    with prob_col2:
        st.metric(team2, f"{prob2:.1f}%")

    st.success(f"Predicted Winner: {winner}")

    # -----------------------------------------------------
    # Stat Table
    # -----------------------------------------------------
    rows = []

    for key, label in IMPORTANT_STATS.items():

        val1 = stats1.get(key, 0)
        val2 = stats2.get(key, 0)

        better = team1 if val1 > val2 else team2 if val2 > val1 else "Tie"

        rows.append({
            "Stat": label,
            team1: val1,
            team2: val2,
            "Better": better
        })

    df = pd.DataFrame(rows)

    st.subheader("Stat Comparison")
    st.dataframe(df, use_container_width=True)

    # -----------------------------------------------------
    # Chart
    # -----------------------------------------------------
    labels = list(IMPORTANT_STATS.values())
    values1 = [stats1.get(k, 0) for k in IMPORTANT_STATS]
    values2 = [stats2.get(k, 0) for k in IMPORTANT_STATS]

    x = range(len(labels))

    fig, ax = plt.subplots()

    ax.bar(x, values1, width=0.4, label=team1)
    ax.bar([i + 0.4 for i in x], values2, width=0.4, label=team2)

    ax.set_xticks([i + 0.2 for i in x])
    ax.set_xticklabels(labels, rotation=45)

    ax.set_title("Team Stat Comparison")
    ax.legend()

    st.pyplot(fig)
