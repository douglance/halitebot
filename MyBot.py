#!/usr/bin/env python3
# Python 3.6

import hlt
from hlt import constants
from hlt.entity import Ship
from hlt.positionals import Direction, Position
from hlt.game_map import MapCell
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
drop_barrier = (constants.MAX_HALITE * .8) 
game_ending = game.turn_number >= constants.MAX_TURNS/100
drop_time = game.turn_number >= constants.MAX_TURNS/2


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
        me = game.me
        game_map = game.game_map
        ships = game.me.get_ships()
        logger.info(f'Total Ships: {len(ships)}')
        command_queue = []

        # Loop through navy and append orders
        try:
            for ship in ships:
                command_queue.append(navy.captains[ship.id].orders)
        except Exception:
            logger.exception('Error in main loop')

        # Build new ship
        try:
            if game.turn_number <= constants.MAX_TURNS/1.5 and \
                    me.halite_amount >= constants.SHIP_COST and \
                    not game_map[me.shipyard].is_occupied or \
                    me.halite_amount >= 20000:
                command_queue.append(me.shipyard.spawn())
        except Exception:
            logger.exception('Error building ship')

        logger.info("End Main Loop")
        game.end_turn(command_queue)
    except Exception:
        logger.exception("Error in Main Loop")
