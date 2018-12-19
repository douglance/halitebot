#!/usr/bin/env python3
# Python 3.6

import hlt
from hlt import constants
from default.navy import Navy, Admiral
from default.map import Map
from default.constants import LOG_LEVEL
import random
import logging
import math
import time
import logging

logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)


def log(name, var):
    logger.info(f'{name}: {var}')
# CONSTANTS


game = hlt.Game()


game.ready("MiPyBot")
logger.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

map = Map(game=game)
admiral = Admiral(player=game.me, map=map, game=game)
navy = Navy(admiral=admiral)

###############
## MAIN LOOP ##
###############


while True:
    try:
        game.update_frame()
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
