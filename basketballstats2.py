import tkinter as tk
from tkinter import ttk, messagebox
import requests
import matplotlib.pyplot as plt
import math

# Updated working endpoints
BASE_SITE_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball"
BASE_STATS_URL = "https://sports.core.api.espn.com/v2/sports/basketball/leagues/mens-college-basketball"

IMPORTANT_STATS = {
    "avgPoints": "Points Per Game",
    "avgRebounds": "Rebounds Per Game",
    "avgAssists": "Assists Per Game",
    "fieldGoalPct": "Field Goal %",
    "threePointFieldGoalPct": "3PT %",
}

class TeamComparerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("College Basketball Team Comparison")
        self.root.geometry("700x650")

        self.teams = self.load_teams()
        if not self.teams:
            messagebox.showerror("Fatal Error", "No teams were loaded from ESPN API.")
        self.create_widgets()

    # ---------------------------------------------------------
    # Load ALL Division I teams (FIXED ENDPOINT)
    # ---------------------------------------------------------
    def load_teams(self):
        teams = {}

        try:
            url = f"{BASE_SITE_URL}/teams?limit=500"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            sports = data.get("sports", [])
            if not sports:
                return {}

            leagues = sports[0].get("leagues", [])
            if not leagues:
                return {}

            for item in leagues[0].get("teams", []):
                team = item.get("team", {})
                name = team.get("displayName")
                team_id = team.get("id")

                if name and team_id:
                    teams[name] = team_id

            return dict(sorted(teams.items()))

        except Exception as e:
            print("TEAM LOAD ERROR:", e)
            return {}

    # ---------------------------------------------------------
    # GUI Setup
    # ---------------------------------------------------------
    def create_widgets(self):

        ttk.Label(self.root, text="Team 1:").grid(row=0, column=0, padx=5, pady=5)
        self.team1_combo = ttk.Combobox(self.root, values=list(self.teams.keys()), width=35)
        self.team1_combo.grid(row=0, column=1)

        ttk.Label(self.root, text="Team 2:").grid(row=1, column=0, padx=5, pady=5)
        self.team2_combo = ttk.Combobox(self.root, values=list(self.teams.keys()), width=35)
        self.team2_combo.grid(row=1, column=1)

        ttk.Label(self.root, text="Season Year:").grid(row=2, column=0, padx=5, pady=5)
        self.season_entry = ttk.Entry(self.root)
        self.season_entry.insert(0, "2024")
        self.season_entry.grid(row=2, column=1)

        ttk.Button(self.root, text="Compare Teams", command=self.compare)\
            .grid(row=3, column=0, columnspan=2, pady=10)

        self.output = tk.Text(self.root, height=20, width=85)
        self.output.grid(row=4, column=0, columnspan=2, padx=10, pady=10)

    # ---------------------------------------------------------
    # Fetch team stats
    # ---------------------------------------------------------
    def get_team_stats(self, team_id, season):

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
                            stats[stat["name"]] = 0.0

            return stats

        except:
            return None

    # ---------------------------------------------------------
    # Fetch team record (FIXED)
    # ---------------------------------------------------------
    def get_team_record(self, team_id, season):

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
    def calculate_win_probability(self, stats1, stats2):

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
    # Compare logic
    # ---------------------------------------------------------
    def compare(self):

        team1 = self.team1_combo.get()
        team2 = self.team2_combo.get()
        season = self.season_entry.get()

        if team1 not in self.teams or team2 not in self.teams:
            messagebox.showerror("Error", "Please select valid teams.")
            return

        if not season.isdigit():
            messagebox.showerror("Error", "Enter a valid season year.")
            return

        stats1 = self.get_team_stats(self.teams[team1], season)
        stats2 = self.get_team_stats(self.teams[team2], season)

        if not stats1 or not stats2:
            messagebox.showerror("Error", "Stats unavailable for that season.")
            return

        record1 = self.get_team_record(self.teams[team1], season)
        record2 = self.get_team_record(self.teams[team2], season)

        self.display_results(team1, team2, season, stats1, stats2, record1, record2)
        self.plot_comparison(team1, team2, stats1, stats2)

    # ---------------------------------------------------------
    # Display Results
    # ---------------------------------------------------------
    def display_results(self, team1, team2, season, stats1, stats2, record1, record2):

        self.output.delete(1.0, tk.END)

        self.output.insert(tk.END, f"{team1} vs {team2} ({season})\n\n")
        self.output.insert(tk.END, f"{team1} Record: {record1}\n")
        self.output.insert(tk.END, f"{team2} Record: {record2}\n\n")

        prob1, prob2 = self.calculate_win_probability(stats1, stats2)
        winner = team1 if prob1 > prob2 else team2

        self.output.insert(tk.END, f"Win Probability:\n")
        self.output.insert(tk.END, f"{team1}: {prob1:.1f}%\n")
        self.output.insert(tk.END, f"{team2}: {prob2:.1f}%\n")
        self.output.insert(tk.END, f"Predicted Winner: {winner}\n\n")

        for key, label in IMPORTANT_STATS.items():
            val1 = stats1.get(key, 0)
            val2 = stats2.get(key, 0)

            better = team1 if val1 > val2 else team2 if val2 > val1 else "Tie"

            self.output.insert(tk.END, f"{label}\n")
            self.output.insert(tk.END, f"{team1}: {val1}\n")
            self.output.insert(tk.END, f"{team2}: {val2}\n")
            self.output.insert(tk.END, f"Better: {better}\n\n")

    # ---------------------------------------------------------
    # Plot
    # ---------------------------------------------------------
    def plot_comparison(self, team1, team2, stats1, stats2):

        labels = list(IMPORTANT_STATS.values())
        values1 = [stats1.get(k, 0) for k in IMPORTANT_STATS]
        values2 = [stats2.get(k, 0) for k in IMPORTANT_STATS]

        x = range(len(labels))

        plt.figure(figsize=(10, 6))
        plt.bar(x, values1, width=0.4, label=team1)
        plt.bar([i + 0.4 for i in x], values2, width=0.4, label=team2)

        plt.xticks([i + 0.2 for i in x], labels, rotation=45)
        plt.title("Team Stat Comparison")
        plt.legend()
        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    root = tk.Tk()
    app = TeamComparerApp(root)
    root.mainloop()