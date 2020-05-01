import json

class Highscore:
    def __init__(self, json_filename):
        self.json_filename=json_filename
        self.load()

    def load(self):
        try:
            with open(self.json_filename, "r") as f:
                self.data = json.load(f)
        except FileNotFoundError:
            self.data={}
            self.save()

    def save(self):
        with open(self.json_filename, "w") as f:
            json.dump(self.data, f, indent=4)

    def ensure_record_exists(self, player):
        if not player in self.data:
            self.data[player]={
                "won":0,
                "lost":0
            }

    def update(self, winners, losers):
        for winner in winners:
            self.ensure_record_exists(winner)
            self.data[winner]["won"]+=1
        for loser in losers:
            self.ensure_record_exists(loser)
            self.data[loser]["lost"]+=1
        self.save()

    def get_highscore_str(self):
        entries = list(self.data.items())
        entries.sort(key=lambda p: p[1]["won"], reverse=True)
        entries_str=[]
        for player, player_data in entries:
            entries_str.append("{} (won: {}, lost: {})".format(
                player, player_data["won"], player_data["lost"]
            ))
        return ", ".join(entries_str)