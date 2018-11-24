#!/usr/bin/env python3
# Python 3.7

import hlt
from hlt import constants
from hlt.entity import Ship
from hlt.positionals import Direction, Position
from hlt.game_map import MapCell
import random
import logging
import math
# import numpy as np
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)
logger.setLevel('INFO')

def log(name, var):
    logger.info(f'{name}: {var}')
# CONSTANTS

game = hlt.Game()
drop_barrier = (constants.MAX_HALITE * .8) 
game_ending = game.turn_number >= constants.MAX_TURNS/1.05
drop_time = game.turn_number >= constants.MAX_TURNS/2


def timefunc(f):
    def f_timer(*args, **kwargs):
        start = time.time()
        result = f(*args, **kwargs)
        end = time.time()
        logger.info(f.__name__ + ' took ' + str(end - start))
        return result
    return f_timer

@dataclass
class Navy():
    captains: list

    @property
    def closest_to_drop_target(self):
        objs = []
        for captain in self.captains:
            tpl = (captain, game_map.calculate_distance(captain.ship.position, map.best_location.position))
            logger.warning(tpl)
            objs.append(tpl)
        try:
            closest = min(objs, key=lambda x: x[1])[0]
            # logger.warning(f'Closest Drop: {closest}')
            return closest
        except Exception as err:
            logger.warning('Error in closest to drop target')
            logger.warning(err)
            return self.captains[0]


@dataclass
class Location():
    position: Position
    cell: MapCell
    safe: bool = True

    @property
    def neighborhood_value(self):
        cell_set = []
        cell_set.append(self.cell)
        neighbors = self.position.get_surrounding_cardinals()
        for neighbor in neighbors:
            if game_map[neighbor] not in cell_set:
                cell_set.append(game_map[neighbor])
                neighbor_neighbors = game_map[neighbor].position.get_surrounding_cardinals(
                )
                for neighbor_neighbor in neighbor_neighbors:
                    if game_map[neighbor_neighbor] not in cell_set:
                        cell_set.append(game_map[neighbor_neighbor])
        total_halite = 0
        for cell in cell_set:
            total_halite += cell.halite_amount
        return total_halite

    @property
    def value(self):
        return self.cell.halite_amount

    def get_random_neighbor_position(self):
        neighbors = self.position.get_surrounding_cardinals()        
        nearby_cells = []
        for neighbor in neighbors:
            if not game_map[neighbor].is_occupied:
                nearby_cells.append(game_map[neighbor])
        if not nearby_cells:
            return self.position
        else:
            return random.choice(nearby_cells).position

    def good_for_looting(self, ship):
        expected_harvest = (.25*self.cell.halite_amount)
        available_inventory = (constants.MAX_HALITE-ship.halite_amount)
        # half_of_the_best_return = .125*map.best_location.cell.halite_amount
        if expected_harvest >= constants.MAX_HALITE*.1 and expected_harvest < available_inventory and not self.cell.has_structure:
        # if expected_harvest < available_inventory 
            return True
        else:
            return False


@dataclass
class Map():
    locations: list
    best_location: Location
    safe_locations: list
        
    def __init__(self, locations=list, safe_locations=list):
        best_value = 0
        self.locations = []
        self.safe_locations = []
        for x in range(game_map.width):
            for y in range(game_map.height):
                position = Position(x, y)
                cell=game_map[position]
                location = Location(position=position, cell=cell)
                if location.neighborhood_value > best_value:
                    self.best_location = location
                    best_value = location.neighborhood_value
                self.locations.append(location)
    
    def reset(self):
        self.safe_locations = self.locations
    

@dataclass
class Captain():
    last_location: Location
    current_location: Location
    ship_id: int

    def __eq__(self, other):
        return self.ship_id == other.ship_id

    def __str__(self):
        return f"""
        Captain of Ship: {str(self.ship_id)}
         - Status: {str(self.status)}
         - Halite: {str(self.ship.halite_amount)}
         - Current Location: ({str(self.current_location.position.x)}, {str(self.current_location.position.y)})
         - Last Location: ({str(self.last_location.position.x)}, {str(self.last_location.position.y)})
         - Priority: {str(self.priority)}
        """

    @property
    def priority(self):
        if self.status is 'banking final':
            return 1
        elif self.status is 'building':
            return 2
        elif self.status is 'hunting':
            return 3
        elif self.status is 'banking':
            return 4
        elif self.status is 'looting':
            return 5
        elif self.status is 'random':
            return 6
        else:
            return 7

    @property
    def cost_to_move(self):
        return (.1 * self.current_location.cell.halite_amount)
    
    @property
    def can_afford_to_move(self):
        return self.cost_to_move <= self.ship.halite_amount

    @property
    def number_of_nearby_ships(self):
        total = 0
        neighbors = self.current_position.get_surrounding_cardinals()
        for neighbor in neighbors:
            if game_map[neighbor].is_occupied:
                total += 1
        return total

    @property
    def ship(self):
        try:
            return game.me.get_ship(self.ship_id)
        except Exception as err:
            logger.warning(err)
            navy.captains.remove(self)

    @property
    def status(self):
        if game_ending:
            return 'banking final'
        elif bank > 5000 and self is navy.closest_to_drop_target:
            return 'building'
        elif self.ship.halite_amount > drop_barrier:
            return 'banking'
        elif self.current_location.good_for_looting(self.ship):
            return 'looting'
        elif self.ship.halite_amount < drop_barrier and self.can_afford_to_move:
            return 'hunting'
        elif self.can_afford_to_move:
            return 'random'
        else:
            return 'still'


    @property
    def orders(self):
        position = self.ship.position
        self.last_location = self.current_location
        self.current_location = Location(cell=game_map[position], position=position)
        if self.status is 'banking final':
            return self.bank_unsafe()
        elif self.status is 'banking':
            return self.bank()
        elif self.status is 'building':
            return self.build()
        elif self.status is 'hunting':
            return self.hunt()
        elif self.status is 'looting':
            return self.loot()
        elif self.status is 'random':
            return self.go_random()
        else:
            return self.stay_still()


    # def move(self, target_location):
    #     """ Handles moving the ship """
    #     move = self.ship.move(self.ship.position, target_location.position)

    @property
    def closest_drop(self):
        distances = []
        dropoffs = game.me.get_dropoffs()
        dropoffs.append(game.me.shipyard)
        for dropoff in dropoffs:
            distances.append((
                dropoff, game_map.calculate_distance(self.ship.position, dropoff.position)))
        return min(distances, key=lambda x: x[1])[0]

    @property
    def best_target_location(self):
        best_fitness = 0
        for location in map.safe_locations:
            distance = game_map.calculate_distance(
                self.ship.position, location.position)
            distance *= 2
            if distance is 0:
                distance = 1
            fitness = round(location.value / distance)
            if fitness > best_fitness:
                best_fitness = fitness
                best_location = location
        return best_location

    def hunt(self):
        logger.debug(str(self.ship_id) + ' is hunting')
        try:
            move = game_map.naive_navigate(self.ship, self.best_target_location.position)
            target_position = self.ship.position.directional_offset(move)
            if not self.best_target_location.cell.has_structure and \
                    self.can_afford_to_move:
                if move is Direction.Still and \
                    self.current_location.cell.halite_amount < 50:
                    return self.go_random()
                map.safe_locations.remove(self.best_target_location)
                return self.ship.move(move)
            elif self.can_afford_to_move:
                return self.go_random()
            else:
                return self.stay_still()
        except Exception as err:
            logger.warning('error hunting')
            logger.warning(err)
            return self.go_random()

    def bank(self):
        logger.debug(str(self.ship_id) + ' is banking')
        try:
            target = self.closest_drop.position
            move = game_map.naive_navigate(self.ship, target)
            closest_drop_distance = game_map.calculate_distance(self.ship.position, self.closest_drop.position)
            if move is Direction.Still and closest_drop_distance <3:
                return self.go_random()
            return self.ship.move(move)
        except Exception as err:
            logger.warning("error banking")
            logger.warning(err)
            target = me.shipyard.position
            move = game_map.naive_navigate(self.ship, target)
            return self.ship.move(move)

    def bank_unsafe(self):
        try:
            logger.debug(str(self.ship_id) + ' going to bank unsafe')
            target = self.closest_drop.position
            direction = game_map.get_unsafe_moves(self.ship.position, target)[0]
            target_position = self.ship.position.directional_offset(
                direction)
            if game_map[target_position].has_structure:
                return self.ship.move(direction)
            else:
                return self.ship.move(game_map.naive_navigate(
                    self.ship.position, target))

        except Exception as err:
            logger.warning('error in bank unsafe')
            logger.warning(err)
            return self.ship.move(game_map.naive_navigate(
                self.ship, self.closest_drop.position))

    def build(self):
        # TODO: Test this feature
        try:
            target = map.best_location.position
            move = game_map.naive_navigate(self.ship, target)
            if move is Direction.Still and self.current_location is map.best_location:
                return self.ship.make_dropoff()
            else:
                return self.ship.move(move)
        except Exception as err:
            logger.warning('error building')
            logger.warning(err)
            return self.ship.stay_still()

    def loot(self):
        logger.debug(str(self.ship_id) + ' looting')
        return self.ship.stay_still()

    def go_random(self):
        logger.debug(str(self.ship_id) + ' going random')
        try:
            if self.can_afford_to_move:
                target = self.current_location.get_random_neighbor_position()
                return self.ship.move(
                    game_map.naive_navigate(self.ship, target))
            else:
                return self.stay_still()
        except Exception as err:
            logger.warning('error in go_random')
            logger.warning(err)
            return self.ship.stay_still()

    def stay_still(self):
        return self.ship.stay_still()

# @dataclass
# class Admiral():
#     id = int
    # TODO Create an admiral that controls a group of captains.

game.ready("MyPythonBot")
logger.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

###############
## Game Loop ##
###############

navy = Navy(captains=[])

while True:
    game.update_frame()
    me = game.me
    game_map = game.game_map
    map = Map()
    command_queue = []
    dropoffs = me.get_dropoffs()
    dropoffs.append(me.shipyard)
    ships = me.get_ships()
   
    logger.info(f'Total Ships: {len(ships)}')
    bank = me.halite_amount
    logger.info(f'Bank: {bank}')
    # player_can_afford_dropoff = bank > constants.DROPOFF_COST

    # Update Navy
    for ship in ships:
        try:
            location = Location(position=ship.position,
                                cell=game_map[ship.position])
            new_captain = Captain(last_location=location, 
                                  current_location=location, 
                                  ship_id=ship.id)
            if new_captain not in navy.captains:
                navy.captains.append(new_captain)
        except Exception as err:
            logger.warning('Error updating navy')
            logger.warning(err)

    new_navy=[]
    for captain in navy.captains:
        if me.has_ship(captain.ship_id):
            try:
                new_navy.append(captain)
            except Exception as err:
                logger.warning('Not in list')
                logger.warning(err)
    navy.captains = new_navy

    ###############
    ## Main Loop ##
    ############### 
    logger.info('Start Main Loop')
    try:
        map.reset()
        try:
            # logger.warning('Attempting sort')
            navy.captains.sort(key=lambda x: x.priority)
        except Exception as err:
            logger.warning('error in sort')
            logger.warning(err)

        for captain in navy.captains:
            # logger.info(f'Priority: {captain.priority}')
            try:
                command_queue.append(captain.orders)
            except Exception as err:
                logger.warning('Error in Captain Loop')
                logger.warning(err)
    except Exception as err:
        logger.warning('Error Main Loop')
        logger.warning(err)

    # Build Ship
    try:
        if game.turn_number <= constants.MAX_TURNS/1.5 and \
                me.halite_amount >= constants.SHIP_COST and \
                not game_map[me.shipyard].is_occupied:
            command_queue.append(me.shipyard.spawn())
            bank -= constants.SHIP_COST
    except Exception as err:
        logger.warning('Error building ship')
        logger.warning(err)

    logger.info("End Main Loop")
    game.end_turn(command_queue)
