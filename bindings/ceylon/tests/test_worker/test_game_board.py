import random


# Define the roles and their abilities
class Role:
    def __init__(self, name, ability):
        self.name = name
        self.ability = ability


class Player:
    def __init__(self, name, role):
        self.name = name
        self.role = role
        self.clues = []
        self.position = 'Foyer'

    def move(self, new_position):
        self.position = new_position
        print(f"{self.name} moves to the {new_position}")

    def find_clue(self, clue):

        self.clues.append(clue)
        print(f"{self.name} found a clue: {clue}")


# Define the mansion layout and clues
rooms = ['Library', 'Lab', 'Attic', 'Kitchen', 'Garden']
clues = {
    'Library': 'Ancient Book',
    'Lab': 'Strange Chemical',
    'Attic': 'Old Journal',
    'Kitchen': 'Hidden Key',
    'Garden': 'Mysterious Map'
}

# Define the players
roles = [
    Role('Detective', 'Can ask detailed questions about clues'),
    Role('Scientist', 'Can analyze clues for additional insights'),
    Role('Historian', 'Knows the mansion\'s background'),
    Role('Locksmith', 'Can open hidden rooms and safes'),
    Role('Psychic', 'Can sense hidden items and passages'),
    Role('Thief', 'Can retrieve items from locked areas')
]

players = [
    Player('Alice', roles[0]),
    Player('Bob', roles[1]),
    Player('Charlie', roles[2]),
    Player('Diana', roles[3]),
    Player('Eve', roles[4]),
    Player('Frank', roles[5])
]


# Simulate a few turns
def simulate_game_turns(turns):
    for turn in range(turns):
        print(f"\nTurn {turn + 1}")
        for player in players:
            # Randomly move the player to a new room
            new_room = random.choice(rooms)
            player.move(new_room)

            # Check if there's a clue in the room
            if new_room in clues:
                player.find_clue(clues[new_room])
                # Remove the clue from the room (assuming it's found only once)
                del clues[new_room]


# Run the simulation for 5 turns
simulate_game_turns(5)

# Print the final state
print("\nFinal State:")
for player in players:
    print(f"{player.name} ({player.role.name}) has clues: {player.clues}")
