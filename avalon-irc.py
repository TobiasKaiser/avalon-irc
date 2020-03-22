#!/usr/bin/env python3

import irc.bot
#import irc.strings
import string
import random
from collections import namedtuple

Quest = namedtuple('Quest', 'team_size fails_required')


class Role:
    optional = False

    def __init__(self, nick):
        self.nick = nick

    def get_initial_knowledge(self, game):
        return "You have no knowledge about other identities."
    


class RoleMinionOfMordred(Role):
    short_name="minion"
    long_name="a Minion of Mordred"
    description="evil player with knowledge of the identities of all other Minions of Mordred"

    evil = True
    is_minion_of_mordred = True

    def get_initial_knowledge(self, game):
        fellow_minions=[]
        for player in game.players:
            if player == self.nick:
                continue
            if game.get_role(player).is_minion_of_mordred:
                fellow_minions.append(player)
        if len(fellow_minions)==1:
            return "Your fellow Minion of Mordred is {}.".format(fellow_minions[0])
        else:
            return "Your fellow Minions of Mordred are {}.".format(", ".join(fellow_minions))

class RoleLoyalServantOfArthur(Role):
    short_name="servant"
    long_name="a Loyal Servant of Arthur"
    description="good player with no knowledge about identities of other players"

    evil = False
    is_minion_of_mordred = False

class AvalonGame:

    # Map player count to lists of five quests
    game_plans = {
        5:  [Quest(2, 1), Quest(3, 1), Quest(2, 1), Quest(3, 1), Quest(3, 1)],
        6:  [Quest(2, 1), Quest(3, 1), Quest(4, 1), Quest(3, 1), Quest(4, 1)],
        7:  [Quest(2, 1), Quest(3, 1), Quest(3, 1), Quest(4, 2), Quest(4, 1)],
        8:  [Quest(3, 1), Quest(4, 1), Quest(4, 1), Quest(5, 2), Quest(5, 1)],
        9:  [Quest(3, 1), Quest(4, 1), Quest(4, 1), Quest(5, 2), Quest(5, 1)],
        10: [Quest(3, 1), Quest(4, 1), Quest(4, 1), Quest(5, 2), Quest(5, 1)]
    }

    game_plans_evil_count = {
        5: 2,
        6: 2,
        7: 3,
        8: 3,
        9: 3,
        10: 4
    }

    Assemble, TeamSel, TeamVote, MissionVote, Finished = range(5)
    Good, Evil = range(2)

    def get_role(self, nick):
        player_idx = self.players.index(nick)
        return self.roles[player_idx]

    @property
    def game_plan(self):
        return self.game_plans[len(self.players)]
    
    @property
    def current_quest(self):
        return len(self.quest_results)

    def __init__(self, bot):
        self.phase = AvalonGame.Assemble

        #self.players = []
        self.players=["a", "b", "c",  "d", "Morn"]
        self.players.sort()
        self.roles=[]
        self.bot = bot
        self.teamsel_player_idx = None
        self.failed_votes = 0
        self.quest_results = []
        self.team = []
        self.players_voted = [] # used for both team vote and quest itself

    def handle_privmsg(self, nick, msg):
        print("privmsg from {}: {}".format(nick, msg))
        msg=msg.lower()
        if msg=="accept":
            self.handle_accept_reject(nick, accept=True)
        elif msg=="reject":
            self.handle_accept_reject(nick, accept=False)
        elif msg=="success":
            self.handle_success_fail(nick, fail=False)
        elif msg=="fail":
            self.handle_success_fail(nick, fail=True)
        elif msg=="identify":
            self.handle_identify(nick)
        else:
            self.bot.send_privmsg(nick, "Unsupported command. Supported commands via private message are accept, reject, success, fail, identify.")

    def handle_pubmsg(self, nick, msg):
        print("pubmsg from {}: {}".format(nick, msg))

        if msg.startswith("!"):
            cmd=msg[1:].split(" ")[0].lower()
            if msg.find(" ")>=0:
                arg = msg.split(" ", 1)[1].strip()
            else:
                arg = ""
            if cmd=="info":
                self.handle_info()
            elif cmd=="join":
                self.handle_join(nick)
            elif cmd=="leave":
                self.handle_leave(nick)
            elif cmd=="start":
                self.handle_start(nick)
            elif cmd=="team":
                self.handle_team(nick, arg)

    def handle_join(self, nick):
        if not (self.phase == AvalonGame.Assemble):
            self.bot.send_pubmsg("{}: Command not available.".format(nick))
            return

        if nick in self.players:
            self.bot.send_pubmsg("{}: You are already registered.".format(nick))
        else:
            self.players.append(nick)
            self.players.sort() # This way the same player names will always play in the same order.
            self.bot.send_pubmsg("Players registered: {}".format(self.players_str()))

    def handle_leave(self, nick):
        if not (self.phase == AvalonGame.Assemble):
            self.bot.send_pubmsg("{}: Command not available.".format(nick))
            return

        if nick in self.players:
            self.players.remove(nick)
            self.bot.send_pubmsg("Players registered: {}".format(self.players_str()))
        else:
            self.bot.send_pubmsg("{}: You are not registered.".format(nick))


    def assign_roles(self):
        """Assigns roles to players by assigning self.roles list.
        If role assignment is successful, return True, else return False.
        """
        
        evil_player_count = self.game_plans_evil_count[len(self.players)]
        good_player_count = len(self.players) - evil_player_count

        evil_roles = []

        good_roles = []

        # TODO: Append optional roles to evil_roles and good_roles dictionary.

        if len(evil_roles) > evil_player_count:
            # Game cannot be started because too many optional evil roles are enabled
            return False
        if len(good_roles) > good_player_count:
            # Game cannot be started because too many optional good roles are enabled
            return False

        # Fill up remaining slots with RoleMinionOfMordred, RoleLoyalServantOfArthur:
        while len(evil_roles) < evil_player_count:
            evil_roles.append(RoleMinionOfMordred)
        while len(good_roles) < good_player_count:
            good_roles.append(RoleLoyalServantOfArthur)

        # Assign and shuffle self.roles list
        role_classes = good_roles + evil_roles
        random.shuffle(role_classes)
        self.roles=[]
        for player_idx, role_class in enumerate(role_classes):
            self.roles.append(role_class(self.players[player_idx]))

        # Send info to all players
        for player in self.players:
            role = self.get_role(player)
            msg = "You are {} ({}). {}".format(role.long_name, role.description, role.get_initial_knowledge(self))
            self.bot.send_privmsg(player, msg)

        return True


    def handle_start(self, nick):
        if not (self.phase == AvalonGame.Assemble):
            self.bot.send_pubmsg("{}: Command not available.".format(nick))
            return

        if not (nick in self.players):
            self.bot.send_pubmsg("{}: You are not registerd for the game.".format(nick))
            return

        if len(self.players)<5:
            self.bot.send_pubmsg("{}: At least five players are required to start.".format(nick))
            return

        if len(self.players)>10:
            self.bot.send_pubmsg("{}: At most ten players are required to start.".format(nick))
            return

        if not self.assign_roles():
            self.bot.send_pubmsg("Game could not be started due to error in assigning roles. Please check your options for consistency.")
            return

        self.bot.send_pubmsg("The game has started! Players are {}.".format(self.players_str()))

        self.enter_teamsel()

    def enter_teamsel(self, after_failed_vote=False):
        # Increment failed votes:
        if after_failed_vote:
            self.failed_votes+= 1
            if self.failed_votes >= 5:
                self.bot.send_pubmsg("Five failed votes: Evil wins.")
                self.phase = Finished
                self.winner = AvalonGame.Evil
            elif self.failed_votes == 4:
                self.bot.send_pubmsg("Failed votes in this round: {}. When five failed votes are reached, Evil wins!".format(self.failed_votes))
            else:
                self.bot.send_pubmsg("Failed votes in this round: {}".format(self.failed_votes))
        else:
            self.failed_votes = 0

        # Increment player or choose random first player:
        if self.teamsel_player_idx == None:
            self.teamsel_player_idx = random.choice(range(len(self.players)))
        else:
            self.teamsel_player_idx = (self.teamsel_player_idx + 1) % len(self.players)

        self.phase = AvalonGame.TeamSel


        self.bot.send_pubmsg("{} (Type \"!team Player1 Player2 ...\")".format(self.teamsel_str()))

    def handle_team(self, nick, arg):
        if not (self.phase == AvalonGame.TeamSel):
            self.bot.send_pubmsg("{}: Command not available.".format(nick))
            return

        fails_required = self.game_plan[self.current_quest].fails_required
        team_size = self.game_plan[self.current_quest].team_size
        teamsel_player = self.players[self.teamsel_player_idx]

        if not (nick == teamsel_player):
            self.bot.send_pubmsg("{}: It is not your turn.".format(nick))
            return

        team = arg.split(" ")
        if len(team) != team_size:
            self.bot.send_pubmsg("{}: Team must consist of {} players.".format(nick, team_size))
            return

        player_names_valid=True
        for player in team:
            if not (player in self.players):
                player_names_valid=False

        if not player_names_valid:
            self.bot.send_pubmsg("{}: Team must consist of valid players.".format(nick))
            return

        self.team = team
        self.phase = AvalonGame.TeamVote

        self.bot.send_pubmsg("{} Please vote for or against this team with \"/m Avalon accept\" or h \"/m Avalon reject\".".format(self.team_str()))


    def team_str(self):
        return "{} has chosen the following team: {}.".format(
            self.players[self.teamsel_player_idx],
            ", ".join(self.team)
        )

    def handle_accept_reject(self, nick, accept):
        pass

    def handle_success_fail(self, nick, fail):
        pass

    def handle_identify(self):
        pass

    def players_str(self):
        return ", ".join(self.players) if len(self.players) >= 1 else "none"

    def teamsel_str(self):
        fails_required = self.game_plan[self.current_quest].fails_required
        team_size = self.game_plan[self.current_quest].team_size
        teamsel_player = self.players[self.teamsel_player_idx]

        return "For quest {}/5, {} now selects a team of {} players.{}".format(
            self.current_quest+1,
            teamsel_player,
            team_size,
            " Two fails are required to fail this quest." if fails_required == 2 else ""
        )

    def handle_info(self):
        if self.phase == AvalonGame.Assemble:
            self.bot.send_pubmsg("Info: Game is not running. Players registered: {}".format(self.players_str()))
        elif self.phase == AvalonGame.TeamSel:
            self.bot.send_pubmsg("Info: {}".format(self.teamsel_str()))
        elif self.phase == AvalonGame.TeamVote:
            pass




class AvalonBot(irc.bot.SingleServerIRCBot):
    def __init__(self, channel, nickname, server, port=6667):
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
        self.channel = channel
        self.game = AvalonGame(self)
        self.debug_game = True

    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        c.join(self.channel)

    def check_finish(self):
        # TODO
        if self.game.phase == AvalonGame.Finished:
            print("game finished....")

    def on_privmsg(self, c, e):
        nick = e.source.split("!")[0]
        msg = e.arguments[0]
        self.game.handle_privmsg(nick, msg)
        self.check_finish()
        
    def on_pubmsg(self, c, e):
        nick = e.source.split("!")[0]
        msg = e.arguments[0]
        if self.debug_game and msg.startswith("!!"):
            first_excl = msg[2:].find("!")
            if first_excl>=0:
                print("Debug pubmsg received.")
                self.game.handle_pubmsg(msg[2:2+first_excl], msg[2+first_excl:])
        if self.debug_game and msg.startswith("@@"):
            first_excl = msg[2:].find(" ")
            if first_excl>=0:
                print("Debug privmsg received.")
                self.game.handle_privmsg(msg[2:2+first_excl], msg[2+first_excl:])
        else:
            self.game.handle_pubmsg(nick, msg)
        self.check_finish()
    
    def send_pubmsg(self, msg):
        """Send message to all players. For use by AvalonGame class."""
        self.connection.privmsg(self.channel, msg)

    def send_privmsg(self, nick, msg):
        """Send private message to one player. For use by AvalonGame class."""
        self.connection.privmsg(nick, msg)
        #self.connection.notice(nick, msg)
        if self.debug_game:
            self.send_pubmsg("((privmsg to {}: {}))".format(nick, msg))
        

def main():
    import sys

    if len(sys.argv) != 4:
        print("Usage: avalon-irc <server[:port]> <channel> <nickname>")
        sys.exit(1)

    s = sys.argv[1].split(":", 1)
    server = s[0]
    if len(s) == 2:
        try:
            port = int(s[1])
        except ValueError:
            print("Error: Erroneous port.")
            sys.exit(1)
    else:
        port = 6667
    channel = sys.argv[2]
    nickname = sys.argv[3]

    bot = AvalonBot(channel, nickname, server, port)
    bot.start()


if __name__ == "__main__":
    main()