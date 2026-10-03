""" Text adventure game
    @insta = @lakshaytalkstocomputer
    @year  = 2018
"""
__author__ = "lakshaytalkstocomputer"


import json
import os

import world
from player import Player
from collections import OrderedDict


SAVE_FILE = "savegame.json"


def save_game(player, path=SAVE_FILE):
    data = {
        "player": player.to_dict(),
        "claimed_gold": [list(coord) for coord in world.claimed_gold_tiles()],
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_game(path=SAVE_FILE):
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def play():
    print()
    print()
    print("Escape from Cave Terror!")
    world.parse_world_dsl()
    save_data = load_game()
    if save_data:
        player = Player.from_dict(save_data.get("player"))
        world.restore_claimed_gold(save_data.get("claimed_gold"))
    else:
        player = Player()
    while player.is_alive() and not player.victory:
        room = world.tile_at(player.x, player.y)
        print(room.intro_text())
        room.modify_player(player)
        if player.is_alive() and not player.victory:
            try:
                choose_action(room, player)
            except (EOFError, KeyboardInterrupt):
                # The player quit the game: keep the progress so it can
                # be restored on the next run instead of dropping it.
                save_game(player)
                return
            save_game(player)
        elif not player.is_alive():
            print("Your journey has come to an early end! ")
    if os.path.exists(SAVE_FILE):
        os.remove(SAVE_FILE)


def get_available_actions(room, player):
    actions = OrderedDict()
    print("Choose an action: ")
    if player.inventory:
        action_adder(actions, 'i', player.print_inventory, "Print inventory")
    if isinstance(room, world.TraderTile):
        action_adder(actions, 't', player.trade, "Trade")
    if isinstance(room, world.EnemyTile) and room.enemy.is_alive():
        action_adder(actions, 'a', player.attack, "Attack")
    else:
        if world.tile_at(room.x, room.y - 1):
            action_adder(actions, 'n', player.move_north, "Go North")
        if world.tile_at(room.x, room.y + 1):
            action_adder(actions, 's', player.move_south, "Go South")
        if world.tile_at(room.x + 1, room.y):
            action_adder(actions, 'e', player.move_east, "Go East")
        if world.tile_at(room.x - 1, room.y):
            action_adder(actions, 'w', player.move_west, "Go West")
        if player.hp < 100:
            action_adder(actions, 'h', player.heal, "Heal")

    return actions


def action_adder(action_dict, hotkey, action, name):
    action_dict[hotkey.lower()] = action
    action_dict[hotkey.upper()] = action
    print("{} : {}".format(hotkey, name))


def choose_action(room, player):
    action = None
    while not action:
        available_actions = get_available_actions(room, player)
        action_input = input("Action: ")
        action = available_actions.get(action_input)
        if action:
            action()
        else:
            print("Invalid action!")

if __name__ == "__main__":
    play()
