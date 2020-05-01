
class Role:
    is_assassin = False
    is_merlin = False
    is_percival = False
    unknown_to_merlin = False
    looks_like_merlin_to_percival = False

    def __init__(self, nick):
        self.nick = nick

    def get_initial_knowledge(self, game):
        return "You have no knowledge of other identities."
    def validate_roles(self, roles):
        """Return True if roles contain all roles that are required for this role to participate properly in the game."""
        return True

class RoleMinionOfMordred(Role):
    short_name="minion"
    long_name="Minion of Mordred"
    long_name_article="a Minion of Mordred"
    description="evil player with knowledge of the identities of the other Minions of Mordred"

    evil = True
    is_minion_of_mordred = True

    def get_initial_knowledge(self, game):
        fellow_minions=[]
        for player in game.players:
            if player == self.nick:
                continue
            if game.get_role(player).is_minion_of_mordred:
                fellow_minions.append(player)
        if len(fellow_minions)==0:
            return "There is no fellow Minion of Mordred."
        if len(fellow_minions)==1:
            return "Your fellow Minion of Mordred is {}.".format(fellow_minions[0])
        else:
            return "Your fellow Minions of Mordred are {}.".format(", ".join(fellow_minions))

class RoleAssassin(RoleMinionOfMordred):
    short_name="assassin"
    long_name="Assassin"
    long_name_article="the Assassin"
    description="evil player with knowledge of the identities of the other Minions of Mordred and the option to win the game by identifying Merlin"

    is_assassin = True

class RoleLoyalServantOfArthur(Role):
    short_name="servant"
    long_name="Loyal Servant of Arthur"
    long_name_article="a Loyal Servant of Arthur"
    description="good player with no knowledge about identities of other players"

    evil = False
    is_minion_of_mordred = False

class RoleMerlin(RoleLoyalServantOfArthur):
    short_name="merlin"
    long_name="Merlin"
    long_name_article="Merlin"
    description="good player with knowledge of the identities of the Minions of Mordred"
    is_merlin = True
    looks_like_merlin_to_percival = True

    def get_initial_knowledge(self, game):
        minions=[]
        for player in game.players:
            role = game.get_role(player)
            if role.unknown_to_merlin:
                continue
            if role.is_minion_of_mordred:
                minions.append(player)
        if len(minions)==1:
            return "The Minion of Mordred is {}.".format(minions[0])
        else:
            return "The Minions of Mordred are {}.".format(", ".join(minions))    

# Optional roles
# --------------

class RolePercival(RoleLoyalServantOfArthur):
    short_name="percival"
    long_name="Percival"
    long_name_article="Percival"
    description="good player with knowledge of the identity of Merlin"
    is_percival = True

    def get_initial_knowledge(self, game):
        merlins=[]
        for player in game.players:
            role = game.get_role(player)
            if role.looks_like_merlin_to_percival:
                merlins.append(player)
        return "{} {} Merlin.".format(
            " and ".join(merlins),
            "is" if len(merlins) == 1 else "are"
        )

class RoleMordred(RoleMinionOfMordred):
    short_name="mordred"
    long_name="Mordred"
    long_name_article="Mordred"
    description="evil player with knowledge of the identities of the other Minions of Mordred, unknown to Merlin"

    unknown_to_merlin=True

class RoleOberon(RoleMinionOfMordred):
    short_name="oberon"
    long_name="Oberon"
    long_name_article="Oberon"
    description="evil player who does not know and is unknown to the Minions of Mordred"

    is_minion_of_mordred = False

    def get_initial_knowledge(self, game):
        return "You have no knowledge of other identities."

class RoleMorgana(RoleMinionOfMordred):
    short_name="morgana"
    long_name="Morgana"
    long_name_article="Morgana"
    description="evil player with knowledge of the identities of the other Minions of Mordred, to Percival appears as Merlin"

    looks_like_merlin_to_percival = True

    def validate_roles(self, all_roles):
        # Percival needs to present for Morgana to participate.
        percival_present=False
        for role in all_roles:
            if role.is_percival:
                percival_present = True
        return percival_present
