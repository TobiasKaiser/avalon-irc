import pytest
import re

from ..game import AvalonGame

class DummyBot:
    def __init__(self):
        self.pubmsg_queue=[]
        self.privmsg_queue=[]

    def send_pubmsg(self, msg):
        """Send message to all players. For use by AvalonGame class."""
        self.pubmsg_queue.append(msg)
        

    def send_privmsg(self, nick, msg):
        """Send private message to one player. For use by AvalonGame class."""
        self.privmsg_queue.append((nick, msg))
        
    def assert_messages(self, pubmsgs=[], privmsgs=[]):
        """pubmsgs must be a list of regular expressions. The first matching
        message in the pubmsg queue is removed along with the corresponding entry
        of the argument. If no message matches the specified regex or the queue is
        not empty after all pubmsgs are processes, an error is raised.
        privmsgs works the same way, but contains tuples (nick, msg_regex)."""

        for expected_pubmsg in pubmsgs:
            matched = False
            for i in range(len(self.pubmsg_queue)):
                if re.match(expected_pubmsg, self.pubmsg_queue[i]):
                    self.pubmsg_queue.pop(i)
                    matched = True
                    break
            assert(matched)

        assert(len(self.pubmsg_queue) == 0)

        for expected_nick, expected_privmsg in privmsgs:
            matched = False
            for i in range(len(self.privmsg_queue)):
                nick, msg = self.privmsg_queue[i]
                
                msg_matched = re.match(expected_privmsg, msg)
                nick_matched = nick == expected_nick

                if msg_matched and nick_matched:
                    self.privmsg_queue.pop(i)
                    matched = True
                    break
            assert(matched)

        assert(len(self.privmsg_queue) == 0)

class GameTester:
    def __init__(self):
        self.bot = DummyBot()
        self.game = AvalonGame(self.bot)
        self.players = []

    def join(self, player_name):
        self.players.append(player_name)
        self.game.handle_pubmsg(player_name, "!join")
        self.bot.assert_messages(pubmsgs=["^Players registered: {}$".format(", ".join(self.players))])

    def join_count(self, count):
        for i in range(count):
            self.join("Player{}".format(i))

    def start(self, call):
        self.game.handle_pubmsg(self.players[0], call)

def test_game():
    gt = GameTester()

    gt.join_count(10)

    gt.start("!start percival mordred oberon morgana")

    print(gt.bot.pubmsg_queue)
    for n, m in gt.bot.privmsg_queue:
        print(n, m)
    
    #g.handle_pubmsg("Player2", "!join")
    #g.handle_pubmsg("Player3", "!join")
    #g.handle_pubmsg("Player4", "!join")
    #g.handle_pubmsg("Player5", "!join")
    #g.handle_pubmsg("Player1", "!start")


if __name__=="__main__":
    test_game()