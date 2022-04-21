class Player:
    """
    Class for representing individual players of the game
    :param name, str - name of the Player
    :param character, str - default = HUMAN. Type of the player, for now str, but can be changed to Enum or some other alternative
                            (CHECK options) - this should expect values HUMAN or COMPUTER
                            (later differentiate computer into different kinds of agents, GREEDY, RANDOM etc.)
    """

    def __init__(self, name: str, character: str = 'HUMAN'):
        """
        Constructor method
        """
        self.name: str = name  # type checking of the input args?
        self.character: str = character  # type checking of the input args?
        self.hand: list = []
        if character != 'HUMAN':
            raise ValueError("Sofar only human players are supported, other kinds of agents will be implemented later")

    def __repr__(self):
        """
        Dunder returning the text describing the instance, which can be passed to eval to generate same instance
        :return: str
        """
        return f"Player({self.name})"

    def play_turn(self):
        """
        Instance method which performs the play of the player. Can be conditioned on self.character.
        :return:
        """
        pass  # TODO: implement me
        """
        For human players this should take as an argument the type of move they want to play. For computer players,
        the move can be decided based on their character
        """
