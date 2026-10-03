"""Regression tests for EscapeFromCave.

Covers the four fixed defect areas:
  * directed graph traversal  -> map adjacency + illegal moves
  * item uniqueness           -> gold tiles can only be picked up once
  * player state persistence  -> inventory serialization / save recovery
  * victory determination     -> key items are required to win
"""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sources"))

import items
import world
import game
from player import Player


def fresh_world():
    world.parse_world_dsl()


def quiet(callable_, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return callable_(*args, **kwargs)


class MapAdjacencyTests(unittest.TestCase):
    def setUp(self):
        fresh_world()

    def test_parse_is_idempotent(self):
        world.parse_world_dsl()
        world.parse_world_dsl()
        self.assertEqual(len(world.world_map), 5)
        self.assertTrue(all(len(row) == 5 for row in world.world_map))
        self.assertEqual(world.start_tile_location, (2, 3))

    def test_known_tiles(self):
        self.assertIsInstance(world.tile_at(2, 3), world.StartTile)
        self.assertIsInstance(world.tile_at(2, 0), world.VictoryTile)
        gold_tiles = [(x, y) for y in range(5) for x in range(5)
                      if isinstance(world.tile_at(x, y), world.FindGoldTile)]
        self.assertEqual(sorted(gold_tiles), [(0, 4), (3, 3), (4, 4)])

    def test_empty_cells_and_out_of_bounds_are_none(self):
        self.assertIsNone(world.tile_at(1, 3))
        self.assertIsNone(world.tile_at(-1, 0))
        self.assertIsNone(world.tile_at(0, -1))
        self.assertIsNone(world.tile_at(99, 99))

    def test_available_actions_match_adjacency(self):
        player = Player()
        room = world.tile_at(player.x, player.y)
        actions = quiet(game.get_available_actions, room, player)
        for hotkey in ("n", "s", "e"):
            self.assertIn(hotkey, actions)
        self.assertNotIn("w", actions)
        self.assertNotIn("W", actions)

    def test_illegal_move_is_ignored(self):
        player = Player()
        player.move_west()  # (1, 3) is an empty cell
        self.assertEqual((player.x, player.y), (2, 3))
        player.move_north()  # (2, 2) is a real tile
        self.assertEqual((player.x, player.y), (2, 2))
        for _ in range(10):
            player.move_north()  # walk into the cave wall repeatedly
        self.assertIsNotNone(world.tile_at(player.x, player.y))


class ItemUniquenessTests(unittest.TestCase):
    def setUp(self):
        fresh_world()
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    def test_gold_tile_claimed_once_on_revisit(self):
        player = Player()
        tile = world.tile_at(3, 3)
        self.assertIsInstance(tile, world.FindGoldTile)
        quiet(tile.modify_player, player)
        gold_after_first_visit = player.gold
        quiet(tile.modify_player, player)  # backtrack onto the same tile
        self.assertEqual(player.gold, gold_after_first_visit)
        self.assertTrue(tile.gold_claimed)

    def test_claimed_gold_survives_save_and_reload(self):
        player = Player()
        quiet(world.tile_at(3, 3).modify_player, player)
        path = os.path.join(self.tmpdir.name, "save.json")
        game.save_game(player, path)

        fresh_world()  # simulate restarting the game
        data = game.load_game(path)
        restored = Player.from_dict(data["player"])
        world.restore_claimed_gold(data["claimed_gold"])

        reloaded_tile = world.tile_at(3, 3)
        self.assertTrue(reloaded_tile.gold_claimed)
        quiet(reloaded_tile.modify_player, restored)
        self.assertEqual(restored.gold, player.gold)


class InventorySerializationTests(unittest.TestCase):
    def setUp(self):
        fresh_world()
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    def test_roundtrip_preserves_state_and_order(self):
        player = Player()
        player.inventory.append(items.HealingPotion())
        player.hp = 42
        player.gold = 77
        player.x, player.y = 2, 2
        restored = Player.from_dict(player.to_dict())
        self.assertEqual([type(i).__name__ for i in restored.inventory],
                         ["Rock", "Dagger", "CrustyBread", "HealingPotion"])
        self.assertEqual(restored.hp, 42)
        self.assertEqual(restored.gold, 77)
        self.assertEqual((restored.x, restored.y), (2, 2))
        self.assertFalse(restored.victory)

    def test_save_file_roundtrip(self):
        player = Player()
        player.gold = 33
        path = os.path.join(self.tmpdir.name, "save.json")
        game.save_game(player, path)
        with open(path) as f:
            self.assertEqual(json.load(f)["player"]["gold"], 33)
        restored = Player.from_dict(game.load_game(path)["player"])
        self.assertEqual(restored.gold, 33)
        self.assertEqual([i.name for i in restored.inventory],
                         [i.name for i in player.inventory])

    def test_unknown_item_names_are_skipped(self):
        data = {"x": 2, "y": 3, "hp": 80, "gold": 10,
                "inventory": ["Rock", "Excalibur", "Dagger", 42]}
        restored = Player.from_dict(data)
        self.assertEqual([type(i).__name__ for i in restored.inventory],
                         ["Rock", "Dagger"])

    def test_missing_fields_fall_back_to_defaults(self):
        restored = Player.from_dict({})
        self.assertEqual((restored.x, restored.y), world.start_tile_location)
        self.assertEqual(restored.hp, 100)
        self.assertEqual(restored.gold, 5)
        self.assertFalse(restored.victory)
        self.assertEqual([type(i).__name__ for i in restored.inventory],
                         ["Rock", "Dagger", "CrustyBread"])

    def test_unknown_fields_are_ignored(self):
        data = {"x": 2, "y": 3, "hp": 90, "gold": 8, "victory": False,
                "inventory": ["Rock"], "mana": 999, "pets": ["dog"]}
        restored = Player.from_dict(data)
        self.assertEqual(restored.hp, 90)
        self.assertFalse(hasattr(restored, "mana"))

    def test_invalid_saved_position_returns_to_start(self):
        restored = Player.from_dict({"x": 1, "y": 3, "inventory": []})
        self.assertEqual((restored.x, restored.y), world.start_tile_location)

    def test_corrupted_or_missing_save_returns_none(self):
        bad = os.path.join(self.tmpdir.name, "bad.json")
        with open(bad, "w") as f:
            f.write("{ not json !")
        self.assertIsNone(game.load_game(bad))
        self.assertIsNone(game.load_game(os.path.join(self.tmpdir.name, "none.json")))

    def test_restore_claimed_gold_tolerates_junk(self):
        quiet(world.restore_claimed_gold, None)
        quiet(world.restore_claimed_gold, ["junk", [1], ["a", "b"], [99, 99]])
        self.assertFalse(world.tile_at(3, 3).gold_claimed)


class VictoryPreconditionTests(unittest.TestCase):
    def setUp(self):
        fresh_world()

    def test_victory_requires_all_key_items(self):
        player = Player()
        tile = world.VictoryTile(2, 0)
        player.inventory = [i for i in player.inventory if i.name != "Dagger"]
        quiet(tile.modify_player, player)
        self.assertFalse(player.victory)
        player.inventory.append(items.Dagger())
        quiet(tile.modify_player, player)
        self.assertTrue(player.victory)

    def test_full_starting_inventory_wins(self):
        player = Player()
        quiet(world.tile_at(2, 0).modify_player, player)
        self.assertTrue(player.victory)


if __name__ == "__main__":
    unittest.main()
