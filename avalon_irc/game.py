
import collections
import copy
import random

from .roles import *
Quest = collections.namedtuple('Quest', 'team_size fails_required')


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
    
    valid_game_args = ["percival", "mordred", "oberon", "morgana"]

    Assemble, TeamSel, TeamVote, QuestVote, Assassination, Finished = range(6)
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

        #self.quest_results=[True, True, False, False]
        self.quest_results=[]
        self.players = []
        #self.players=["a", "b", "c",  "d", "Morn"]
        self.players.sort()
        self.roles=[]
        self.bot = bot
        self.teamsel_player_idx = None
        self.team = []
        self.failed_votes = 0 # used for quest only
        self.players_voted = [] # used for both team vote and quest itself
        self.players_voted_accept = [] # used for team vote only
        self.players_voted_reject = [] # used for team vote only
        self.game_args = []

    def handle_privmsg(self, nick, msg):
        #print("privmsg from {}: {}".format(nick, msg))
        msg=msg.lower()
        if msg=="accept" or msg=="a":
            self.handle_accept_reject(nick, accept=True)
        elif msg=="reject" or msg=="r":
            self.handle_accept_reject(nick, accept=False)
        elif msg=="success" or msg=="s":
            self.handle_success_fail(nick, fail=False)
        elif msg=="fail" or msg=="f":
            self.handle_success_fail(nick, fail=True)
        elif msg=="identify":
            self.handle_identify(nick)
        else:
            self.bot.send_privmsg(nick, "Unsupported command. Supported commands via private message are accept, reject, success, fail, identify.")

    def handle_pubmsg(self, nick, msg):
        #print("pubmsg from {}: {}".format(nick, msg))

        if msg.startswith("!"):
            cmd=msg[1:].split(" ")[0].lower()
            if msg.find(" ")>=0:
                arg = msg.split(" ", 1)[1].strip()
            else:
                arg = ""
            if cmd=="info":
                self.handle_info()
            elif cmd=="highscore":
                self.handle_highscore()
            elif cmd=="join":
                self.handle_join(nick)
            elif cmd=="leave":
                self.handle_leave(nick)
            elif cmd=="start":
                self.handle_start(nick, arg)
            elif cmd=="team":
                self.handle_team(nick, arg)
            elif cmd=="kill":
                self.handle_kill(nick, arg)

    def handle_kill(self, nick, arg):
        if not (self.phase == AvalonGame.Assassination):
            self.bot.send_pubmsg("{}: Command not available.".format(nick))
            return

        if not (nick == self.get_assassin()):
            self.bot.send_pubmsg("{}: You are not the Assassin.".format(nick))
            return

        if not (arg in self.players):
            self.bot.send_pubmsg("{}: Invalid player.".format(nick))
            return

        if arg == self.get_merlin():
            self.bot.send_pubmsg("The Assassin has killed Merlin!")
            self.end_game(winner=AvalonGame.Evil)
        else:
            self.bot.send_pubmsg("The Assassin was unsuccessful.")
            self.end_game(winner=AvalonGame.Good)


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


    def assign_roles(self, optional_good_roles=[], optional_evil_roles=[]):
        """Assigns roles to players by assigning self.roles list.
        If role assignment is successful, return True, else return False.
        """
        
        evil_player_count = self.game_plans_evil_count[len(self.players)]
        good_player_count = len(self.players) - evil_player_count

        evil_roles = [RoleAssassin] + optional_evil_roles
        if "mordred" in self.game_args:
            evil_roles.append(RoleMordred)
        if "oberon" in self.game_args:
            evil_roles.append(RoleOberon)
        if "morgana" in self.game_args:
            evil_roles.append(RoleMorgana)

        good_roles = [RoleMerlin] + optional_good_roles
        if "percival" in self.game_args:
            good_roles.append(RolePercival)

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
        roles=[]
        for player_idx, role_class in enumerate(role_classes):
            roles.append(role_class(self.players[player_idx]))

        # Validate roles: Some roles require other roles to be present.
        roles_valid=True
        for r in roles:
            if not r.validate_roles(roles):
                roles_valid=False
        if not roles_valid:
            return False

        self.roles = roles

        # Send info to all players
        for player in self.players:
            self.send_rolemsg(player)

        return True

    def send_rolemsg(self, player):
        role = self.get_role(player)
        msg = "You are {} ({}). {}".format(role.long_name_article, role.description, role.get_initial_knowledge(self))
        self.bot.send_privmsg(player, msg)

    def handle_start(self, nick, arg):

        #optional_good_roles = []
        #optional_evil_roles = []
        #for opt in arg.strip().split():
        #    if opt == "-percival":
        #        optional_good_roles.append(RolePercival)
        #    elif opt == "-mordred":
        #        optional_evil_roles.append(RoleMordred)
        #    elif opt == "-oberon":
        #        optional_evil_roles.append(RoleOberon)
        #    elif opt == "-morgana":
        #        optional_evil_roles.append(RoleMorgana)
        #    elif opt == "-help":
        #        self.bot.send_pubmsg("{}: Available options are -percival, -mordred, -oberon, -morgana.".format(nick))
        #        return
        #    else:
        #        self.bot.send_pubmsg("{}: Unknown option. Type !start -help to get help.".format(nick))
        #        return
        #
        #if not (self.phase == AvalonGame.Assemble):
        #    self.bot.send_pubmsg("{}: Command not available.".format(nick))
        #    return
        #
        #if not (nick in self.players):
        #    self.bot.send_pubmsg("{}: You are not registerd for the game.".format(nick))
        #    return

        # Evaluate args:
        game_args=arg.lower().strip().split()
        
        for arg in game_args:
            if not (arg in self.valid_game_args):
                self.bot.send_pubmsg("{}: Invalid game argument. Valid game arguments are {}".format(nick, ", ".join(self.valid_game_args)))
                return

        self.game_args = game_args

        if len(self.players)<5:
            self.bot.send_pubmsg("{}: At least five players are required to start.".format(nick))
            return

        if len(self.players)>10:
            self.bot.send_pubmsg("{}: At most ten players are required to start.".format(nick))
            return



        if not self.assign_roles():
            self.bot.send_pubmsg("Game could not be started due to error in assigning roles. Please check your options for consistency.")
            return

        self.bot.send_pubmsg("The game has started! Players are {}. {}".format(
            self.players_str(),
            self.roles_str()
        ))

        self.enter_teamsel()

    def winner_str(self):
        assert self.phase == AvalonGame.Finished

        evil_players=[]
        good_players=[]
        
        for idx in range(len(self.players)):
            player = self.players[idx]
            role = self.roles[idx]
            (evil_players if role.evil else good_players).append("{} as {}".format(
                player, role.long_name
            ))

        return "{} wins! Evil players were: {}. Good players were: {}.".format(
            "Evil" if self.winner == AvalonGame.Evil else "Good",
            ", ".join(evil_players),
            ", ".join(good_players)
        )



    def enter_teamsel(self, after_failed_vote=False):
        # Increment failed votes:
        if after_failed_vote:
            self.failed_votes+= 1
            if self.failed_votes >= 5:
                self.bot.send_pubmsg("Five failed votes: Evil wins.")
                self.end_game(winner=AvalonGame.Evil)
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

        self.bot.send_pubmsg("{}".format(self.quest_overview_str()))
        self.bot.send_pubmsg("{} (Type \"!team Player1 Player2 ...\")".format(self.teamsel_str()))

    def roles_str(self):
        count_evil={}
        count_good={}
        for role in self.roles:
            cur_count=(count_evil if role.evil else count_good)
            if role.long_name in cur_count:
                cur_count[role.long_name]+=1
            else:
                cur_count[role.long_name]=1

        evil_roles=[]
        for role, count in count_evil.items():
            if count==1:
                evil_roles.append(role)
            else:
                evil_roles.append("{}x {}".format(count, role))
        good_roles=[]
        for role, count in count_good.items():
            if count==1:
                good_roles.append(role)
            else:
                good_roles.append("{}x {}".format(count, role))

        #print(count_evil, count_good)
        return "Good role cards in play: {}. Evil role cards in play: {}.".format(
            ", ".join(good_roles),
            ", ".join(evil_roles)
        )

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

        self.players_voted = []
        self.players_voted_accept = []
        self.players_voted_reject = []

        self.bot.send_pubmsg("{} Please vote for or against this team with \"/msg Avalon accept\" or h \"/msg Avalon reject\".".format(self.team_str()))

    def team_str(self):
        return "{} has chosen the following team: {}.".format(
            self.players[self.teamsel_player_idx],
            ", ".join(self.team)
        )

    def handle_accept_reject(self, nick, accept):
        if not (self.phase == AvalonGame.TeamVote):
            self.bot.send_privmsg(nick, "Command not available.")
            return

        if not (nick in self.players):
            self.bot.send_privmsg(nick, "Not eligible for vote.")
            return

        if nick in self.players_voted:
            self.bot.send_privmsg(nick, "Double vote ignored.")
            return

        self.players_voted.append(nick)
        if accept:
            self.players_voted_accept.append(nick)
        else:
            self.players_voted_reject.append(nick)

        missing_players=copy.copy(self.players)
        for player_voted in self.players_voted:
            missing_players.remove(player_voted)

        self.bot.send_privmsg(nick, "Vote cast.")
        if len(missing_players) > 0:
            self.bot.send_pubmsg("{} has voted. Missing votes from {}.".format(nick, ", ".join(missing_players)))
        else:
            # Vote completed
            accepted = len(self.players_voted_accept) > len(self.players_voted_reject)
            
            if accepted:
                self.enter_questvote()
            else:
                self.bot.send_pubmsg("The proposed team {} has been rejected. {}".format(
                    ", ".join(self.team),
                    self.team_vote_result_str()
                ))   
                self.enter_teamsel(after_failed_vote=True)

    def team_vote_result_str(self):
        return "{} voted to accept the team. {} voted to reject the team.".format(
            ", ".join(self.players_voted_accept) if len(self.players_voted_accept) > 0 else "Nobody",
            ", ".join(self.players_voted_reject) if len(self.players_voted_reject) > 0 else "Nobody"
        )

    def enter_questvote(self):
        self.bot.send_pubmsg("Team {}: you have been accepted for the quest. {} Please play success or fail for the quest with \"/msg Avalon success\" or h \"/msg Avalon fail\".{}".format(
            ", ".join(self.team),
            self.team_vote_result_str(),
            self.get_special_win_condition_or_empty_str()
        ))
        self.players_voted=[]
        self.failed_votes=0
        self.phase = AvalonGame.QuestVote

    def quest_overview_str(self):
        overview_str=""
        for idx in range(5):
            if idx>0:
                overview_str+=" | "
            quest_result="undecided"
            if self.current_quest > idx:
                if self.quest_results[idx]:
                    quest_result="succeeded"
                else:
                    quest_result="failed"
            fails_required = self.game_plan[idx].fails_required
            team_size = self.game_plan[idx].team_size
            overview_str+="Quest {} (team of {}{}): {}".format(
                idx+1,
                team_size,
                ", two fail votes required to fail" if fails_required == 2 else "",
                quest_result
            )
        return overview_str

    def get_special_win_condition_or_empty_str(self):
        return " Two fail votes are required to fail this quest." if self.get_fails_required() == 2 else ""
        return overview_str


    def handle_success_fail(self, nick, fail):
        if not (self.phase == AvalonGame.QuestVote):
            self.bot.send_privmsg(nick, "Command not available.")
            return

        if not (nick in self.team):
            self.bot.send_privmsg(nick, "Not eligible for vote.")
            return

        if nick in self.players_voted:
            self.bot.send_privmsg(nick, "Double vote ignored.")
            return

        if (not self.get_role(nick).evil) and fail:
            self.bot.send_privmsg(nick, "You are not allowed to vote fail.")
            return

        self.players_voted.append(nick)
        if fail:
            self.failed_votes += 1

        missing_players=copy.copy(self.team)
        for player_voted in self.players_voted:
            missing_players.remove(player_voted)

        self.bot.send_privmsg(nick, "Vote cast.")
        if len(missing_players) > 0:
            self.bot.send_pubmsg("{} has voted. Missing votes from {}.".format(nick, ", ".join(missing_players)))
        else:
            # Vote completed
            success = self.failed_votes < self.get_fails_required()

            self.quest_results.append(success)

            self.bot.send_pubmsg("Quest {}. Number of success votes was {}, number of fail votes was {}.".format(
                "succeeded" if success else "failed",
                len(self.team) - self.failed_votes,
                self.failed_votes
            ))

            self.enter_next_quest_or_finish()

    def end_game(self, winner):
        self.phase = AvalonGame.Finished
        self.winner = winner

        self.bot.send_pubmsg("{}".format(self.quest_overview_str()))
        self.bot.send_pubmsg("{}".format(self.winner_str()))

        winners, losers = self.get_winners_losers()
        self.bot.highscore.update(winners, losers)

        self.bot.send_pubmsg("Highscore: {}".format(self.bot.highscore.get_highscore_str()))

    def handle_highscore(self):
        self.bot.send_pubmsg("Highscore: {}".format(self.bot.highscore.get_highscore_str()))

    def get_assassin(self):
        for idx in range(len(self.players)):
            player = self.players[idx]
            role = self.roles[idx]
            if role.is_assassin:
                return player
        return None

    def get_merlin(self):
        for idx in range(len(self.players)):
            player = self.players[idx]
            role = self.roles[idx]
            if role.is_merlin:
                return player
        return None        

    def enter_assassination_phase_or_end_game(self):
        assassin = self.get_assassin()
        if assassin:
            self.phase = AvalonGame.Assassination
            self.bot.send_pubmsg("Good has almost won, but the Assassin can turn still turn the game around by identifying and assassinating Merlin by typing \"!kill Player1\".")
            # Name of Assassin must not be releaved at this stage.

        else:
            self.end_game(winner=AvalonGame.Good)

    def enter_next_quest_or_finish(self):
        total_fails     = len(list(filter(lambda x: not x, self.quest_results)))
        total_successes = len(list(filter(lambda x:     x, self.quest_results)))


        if total_fails >= 3:
            self.end_game(winner=AvalonGame.Evil)
            return

        if total_successes >= 3:
            self.enter_assassination_phase_or_end_game()
            return

        self.enter_teamsel()

    def handle_identify(self, nick):
        if nick in self.players:
            self.send_rolemsg(nick)

    def players_str(self):
        return ", ".join(self.players) if len(self.players) >= 1 else "none"

    def get_team_size(self):
        return self.game_plan[self.current_quest].team_size

    def get_fails_required(self):
        return self.game_plan[self.current_quest].fails_required

    def get_special_win_condition_or_empty_str(self):
        return " Two fails are required to fail this quest." if self.get_fails_required() == 2 else ""

    def get_teamsel_player(self):
        return self.players[self.teamsel_player_idx]

    def teamsel_str(self):
        return "For quest {}/5, {} now selects a team of {} players.{}".format(
            self.current_quest+1,
            self.get_teamsel_player(),
            self.get_team_size(),
            self.get_special_win_condition_or_empty_str()
        )

    def handle_info(self):
        if self.phase == AvalonGame.Assemble:
            self.bot.send_pubmsg("Info: Game is not running. Players registered: {}".format(self.players_str()))
        elif self.phase == AvalonGame.TeamSel:
            self.bot.send_pubmsg("Info: {}".format(self.teamsel_str()))
        elif self.phase == AvalonGame.TeamVote:
            pass

    def get_winners_losers(self):
        winners=[]
        losers=[]
        for idx in range(len(self.players)):
            role = self.roles[idx]
            player = self.players[idx]
            if self.winner == AvalonGame.Good:
                if role.evil:
                    losers.append(player)
                else:
                    winners.append(player)
            else: # self.winner == AvalonGame.Evil
                if role.evil:
                    winners.append(player)
                else:
                    losers.append(player)
        return winners, losers
