# EscapeFromCave
Text Adventure - Escape From Cave

You wake suddenly and find yourself in a cave.
There is darkness all over What will you do?

Text adventure game written in Python using basics of languages.
I recommend any one who is just strating or has started or is starting into 
Github should look it up and start Contributing.

This game uses Loops, Conditions, Objects, Strings and some basic python data structures
like List , Ordered Dictionary.
You will also get to read someone else's code which will help you in your future.

Also if you are a newbie and want to start contributing on Github , then I would 
strongly recommend you start this project.

So come join me in expanding this project and making it bigger and better.

And as always suggestions and questions are always welcome. 

## Save / Load

The game autosaves to `savegame.json` after every action and restores the
player (position, HP, gold, victory flag, inventory) plus already-claimed
gold tiles on the next start. The save is deleted when you die or win.

Loading a save never crashes the game; broken data is recovered like this:

* Save file missing, unreadable, or not valid JSON -> start a new game.
* Missing player fields (x, y, hp, gold, victory, inventory) -> fall back
  to the defaults a new player gets.
* Unknown item names in the inventory -> skipped; known items still load.
* Unknown extra fields -> ignored.
* Saved position that is not a real tile on the map -> back to the start tile.

Run the regression tests with:

    python3 -m unittest discover -s tests -v
