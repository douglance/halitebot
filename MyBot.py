#!/usr/bin/env python3
# Python 3.6

import random
import logging
import math
import time
import logging
import hlt
from hlt import constants
from default.navy import Navy, Admiral, Captain
from default.map import Map
from default.constants import LOG_LEVEL


logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)

game = hlt.Game()
game.ready("MiPyBot")
logger.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

# Customize these classes and replace the appropriate properties and methods to build your own bot


class MyMap(Map):
    pass


class MyNavy(Navy):
    pass


class MyAdmiral(Admiral):
    pass


class MyCaptain(Captain):
    pass


map = MyMap(game=game)
admiral = MyAdmiral(player=game.me, map=map, game=game)
navy = MyNavy(admiral=admiral, captain_class=MyCaptain)

###############
## MAIN LOOP ##
###############

# This is the main game loop where the magic happens
# It expects a command_queue that is a list of Halite commands

while True:
    try:
        # Updates Halite game state
        game.update_frame()

        # Updates our game state
        map.reset()
        navy.update_captains()

        ships = game.me.get_ships()
        logger.info(f'Total Ships: {len(ships)}')
        command_queue = []

        # Loop through ships and append orders
        try:
            for ship in ships:
                command_queue.append(navy.captains[ship.id].orders)
        except Exception:
            logger.exception('Error in main loop')

        # Build new ship
        try:
            if admiral.good_to_build_new_ship():
                command_queue.append(game.me.shipyard.spawn())
        except Exception:
            logger.exception('Error building ship')

        game.end_turn(command_queue)

    except Exception:
        logger.exception("Error in Main Loop")
