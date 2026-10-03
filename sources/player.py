""" Text adventure game
    @insta = @lakshaytalkstocomputer
    @year  = 2018
"""
__author__ = "lakshaytalkstocomputer"

import items
import world


def _as_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class Player:
    def __init__(self):
        self.inventory = [items.Rock(),
                          items.Dagger(),
                          items.CrustyBread()]

        self.x = world.start_tile_location[0]
        self.y = world.start_tile_location[1]
        self.hp = 100
        self.gold = 5
        self.victory = False

    def is_alive(self):
        return self.hp > 0

    def print_inventory(self):
        print("Inventory:")
        for item in self.inventory:
            print("*" + str(item))
        print("*Gold : {}".format(self.gold))
        best_weapon = self.most_powerful_weapon()
        print("Your best weapon is your {}".format(best_weapon))

    def most_powerful_weapon(self):
        max_damage = 0
        best_weapon = None

        for item in self.inventory:
            try:
                if item.damage > max_damage:
                    best_weapon = item
                    max_damage = item.damage
            except AttributeError:
                pass

        return best_weapon

    def move(self, dx, dy):
        if world.tile_at(self.x + dx, self.y + dy):
            self.x += dx
            self.y += dy

    def move_north(self):
        self.move(dx=0, dy=-1)

    def move_south(self):
        self.move(dx=0, dy=1)

    def move_east(self):
        self.move(dx=1, dy=0)

    def move_west(self):
        self.move(dx=-1, dy=0)

    def attack(self):
        best_weapon = self.most_powerful_weapon()
        room = world.tile_at(self.x, self.y)
        enemy = room.enemy
        print("You can use {} against!".format(best_weapon.name, enemy.name))
        enemy.hp -= best_weapon.damage
        if not enemy.is_alive():
            print("You killed {}!".format(enemy.name))
        else:
            print("{} HP is {}.".format(enemy.name, enemy.hp))

    def heal(self):
        consumables = [item for item in self.inventory if isinstance(item, items.Consumable)]
        if not consumables:
            print("You don't have any items to heal you!")
            return

        for i, item in enumerate(consumables,1):
            print("Choose an item to use to heal: ")
            print("{}. {}".format(i, item))

        valid = False
        while not valid:
            choice = input("")
            try:
                to_eat = consumables[int(choice) - 1]
                self.hp = min(100, self.hp + to_eat.healing_value)
                self.inventory.remove(to_eat)
                print("Current HP: {}".format(self.hp))
                valid = True
            except (ValueError, IndexError):
                print("Invalid Choice, try again.")

    def trade(self):
        room = world.tile_at(self.x, self.y)
        room.check_if_trade(self)

    def to_dict(self):
        return {
            "x": self.x,
            "y": self.y,
            "hp": self.hp,
            "gold": self.gold,
            "victory": self.victory,
            "inventory": [type(item).__name__ for item in self.inventory],
        }

    @classmethod
    def from_dict(cls, data):
        # A save may miss fields or carry fields from another version.
        # Recover with the defaults a new player gets instead of crashing.
        if not isinstance(data, dict):
            data = {}
        player = cls.__new__(cls)
        start = world.start_tile_location or (0, 0)
        player.x = _as_int(data.get("x"), start[0])
        player.y = _as_int(data.get("y"), start[1])
        player.hp = _as_int(data.get("hp"), 100)
        player.gold = _as_int(data.get("gold"), 5)
        player.victory = bool(data.get("victory", False))
        if isinstance(data.get("inventory"), list):
            player.inventory = []
            for name in data["inventory"]:
                item_class = items.ITEM_TYPES.get(name) if isinstance(name, str) else None
                if item_class is not None:
                    player.inventory.append(item_class())
        else:
            player.inventory = [items.Rock(),
                                items.Dagger(),
                                items.CrustyBread()]
        if world.tile_at(player.x, player.y) is None:
            player.x, player.y = start
        return player

