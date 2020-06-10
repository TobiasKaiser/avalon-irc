
import irc.bot
import string
from .game import AvalonGame
from .highscore import Highscore
import textwrap


class AvalonBot(irc.bot.SingleServerIRCBot):
    def __init__(self, channel, nickname, server, port=6667, highscore_filename="highscore.json"):
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
        self.channel = channel
        self.game = AvalonGame(self)
        self.debug_game = False
        self.highscore = Highscore(highscore_filename)

    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        c.join(self.channel)

    def check_finish(self):
        if self.game.phase == AvalonGame.Finished:
            # Start new game:
            self.game = AvalonGame(self)
            

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
                self.game.handle_privmsg(msg[2:2+first_excl], msg[2+first_excl+1:])
        else:
            self.game.handle_pubmsg(nick, msg)
        self.check_finish()
    
    def send_pubmsg(self, msg):
        """Send message to all players. For use by AvalonGame class."""
        for line in textwrap.wrap(msg, 200):
            self.connection.privmsg(self.channel, line)

    def send_privmsg(self, nick, msg):
        """Send private message to one player. For use by AvalonGame class."""
        self.connection.privmsg(nick, msg)
        #self.connection.notice(nick, msg)
        if self.debug_game:
            print("privmsg to {}: {}".format(nick, msg))
            #self.send_pubmsg("((privmsg to {}: {}))".format(nick, msg))
        
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
