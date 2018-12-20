#!/usr/bin/env python3
# Python 3.6

import hlt
from hlt import constants
from hlt.entity import Ship
from hlt.positionals import Direction, Position
from hlt.game_map import MapCell
import random
import math
from .map import Location
from .constants import LOG_LEVEL, DROP_BARRIER

import logging

logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)


class Admiral():
    '''Represents the player in the bot

    Holds the map and knows when to build new ships'''

    def __init__(self, player, map, game):
        self.player = player
        self.map = map
        self.game = game

    def get_ships(self):
        return self.player.get_ships()

    def good_to_build_new_ship(self):
        return self.game.turn_number <= constants.MAX_TURNS/1.5 and \
            self.player.halite_amount >= constants.SHIP_COST and \
            not self.game.game_map[self.player.shipyard].is_occupied or \
            self.player.halite_amount >= 20000


class Navy():
    '''Manages ship captains

    '''
    captains: dict

    def __init__(self, admiral, captain_class):
        self.captains = {}
        self.captain_class = captain_class
        self.admiral = admiral

    @property
    def game_map(self):
        '''Convenience property for accessing the game map'''
        return self.admiral.map.game_map

    @property
    def dropoffs(self):
        '''List of all dropoffs owned by player'''
        player = self.admiral.player
        dropoffs = player.get_dropoffs()
        dropoffs.append(player.shipyard)
        return dropoffs

    def update_captains(self):
        '''Adds new captains to the Navy'''
        for ship in self.admiral.get_ships():
            location = Location(position=ship.position,
                                cell=self.game_map[ship.position],
                                map=self.admiral.map)
            captain = self.captain_class(last_location=location,
                                         current_location=location,
                                         ship_id=ship.id,
                                         navy=self)
            if not ship.id in self.captains:
                self.captains[ship.id] = captain

    @property
    def closest_to_best_drop_target(self):
        '''Returns Captain that is closest to the best drop target'''
        try:
            objs = []
            self.update_captains()
            for key, captain in self.captains.items():
                tpl = (captain, self.game_map.calculate_distance(
                    captain.current_location.position, self.admiral.map.best_location.position))
                objs.append(tpl)
            closest = min(objs, key=lambda x: x[1])[0]
            return closest
        except Exception:
            logger.exception('Error in closest to drop target')
            return random.choice(list(self.captains.items()))


class Captain():
    '''This is the class that manages each ship'''
    last_location: Location
    current_location: Location
    navy: Navy
    ship_id: int

    def __init__(self, last_location, current_location, ship_id, navy):
        self.last_location = last_location
        self.current_location = current_location
        self.ship_id = ship_id
        self.navy = navy

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
    def game_map(self):
        '''Convenience property for accessing the game map'''
        return self.navy.admiral.map.game_map

    @property
    def priority(self):
        '''Used in pathfinding (not actually in the bot yet)'''
        if self.status is 'FINAL':
            return 1
        elif self.status is 'BUILD':
            return 2
        elif self.status is 'HUNT':
            return 3
        elif self.status is 'BANK':
            return 4
        elif self.status is 'LOOT':
            return 5
        elif self.status is 'RAND':
            return 6
        else:
            return 7

    @property
    def game_ending(self):
        '''Returns True if the game is ending, so the ship should go crash into the nearest dropoff'''
        return self.navy.admiral.game.turn_number >= constants.MAX_TURNS/1.05

    @property
    def should_build(self):
        '''Returns True if ship should go find the best drop location and build a dropoff there'''
        return self.navy.admiral.player.halite_amount > 5000 and self is self.navy.closest_to_drop_target and \
            round(len(self.navy.captains)/len(self.navy.dropoffs)) > 10

    @property
    def should_bank(self):
        '''Returns True if ship should go bank its halite'''
        return self.ship.halite_amount > DROP_BARRIER

    @property
    def should_loot(self):
        '''Returns True if ship should loot'''
        return self.current_location.good_for_looting(self.ship)

    @property
    def cost_to_move(self):
        '''Costs 10% of the ships location halite to move'''
        return self.current_location.cell.halite_amount * .1

    @property
    def should_hunt(self):
        '''Returns True if ship should go hunting'''
        return self.ship.halite_amount < DROP_BARRIER and self.can_afford_to_move

    @property
    def distance_to_closest_drop(self):
        '''returns an int that is the distance to the closest drop off'''
        return self.game_map.calculate_distance(self.ship.position, self.closest_drop.position)

    @property
    def can_afford_to_move(self):
        '''returns True if the ship has enough halite onboard to move'''
        return self.cost_to_move <= self.ship.halite_amount

    @property
    def number_of_nearby_ships(self):
        '''Returns int of number of ships immediately next to the ship'''
        total = 0
        neighbors = self.current_location.position.get_surrounding_cardinals()
        for neighbor in neighbors:
            if self.game_map[neighbor].is_occupied:
                total += 1
        return total

    @property
    def ship(self):
        '''Returns the Halite ship to which this is the captain'''
        try:
            return self.navy.admiral.player.get_ship(self.ship_id)
        except Exception:
            logger.exception('Ship does not exist.')
            # navy.captains.remove(self)

    @property
    def status(self):
        '''Tells the captain which orders to give'''
        if self.game_ending:
            return 'FINAL'
        if self.should_build:
            return 'BUILD'
        if self.should_bank:
            return 'BANK'
        if self.should_loot:
            return 'LOOT'
        if self.should_hunt:
            return 'HUNT'
        if self.can_afford_to_move:
            return 'RAND'
        return 'MISC'

    @property
    def orders(self):
        '''Refreshes position, then gives orders'''
        position = self.ship.position
        self.last_location = self.current_location
        self.current_location = self.navy.admiral.map.get_location_from_position(
            position)
        if self.status == 'FINAL':
            return self.bank_unsafe()
        if self.status == 'BANK':
            return self.bank()
        if self.status == 'BUILD':
            return self.build()
        if self.status == 'HUNT':
            return self.hunt()
        if self.status == 'LOOT':
            return self.loot()
        if self.status == 'RAND':
            return self.go_random_safe()
        return self.stay_still()

    @property
    def closest_drop(self):
        '''Returns the closest drop off'''
        try:
            return min(self.navy.dropoffs,
                       key=lambda x: self.game_map.calculate_distance(self.ship.position, x.position))
        except Exception:
            logger.exception('error in closest_drop')

    @property
    def best_target_location(self):
        '''Returns the best target location based on get_fitness()'''
        try:
            locations = self.navy.admiral.map.safe_locations
            return max(locations, key=lambda x: x.get_fitness(ship=self.ship))
        except Exception:
            logger.exception('error in best_target_location')

    def hunt(self):
        '''Tells the ship where to go when hunting for halite

        Returns:
            ship.move -- Returns a ship command as expected by the command queue
        '''
        logger.debug(f'{self.ship_id} is hunting')
        try:
            if self.current_location.cell.has_structure:
                return self.go_random_safe()

            best_location = self.best_target_location
            move = self.game_map.naive_navigate(
                self.ship, best_location.position)
            target_position = self.ship.position.directional_offset(move)

            if self.game_map[target_position].has_structure or \
               self.distance_to_closest_drop <= 1 and \
               move is Direction.Still:
                return self.go_random_safe()
            if target_position == self.last_location.position:
                return self.ship.stay_still()
            if self.can_afford_to_move:
                if move is Direction.Still and self.current_location.cell.halite_amount < 100:
                    return self.go_random_for_equal_distance(target_location=best_location)
                self.navy.admiral.map.safe_locations.remove(best_location)
                return self.ship.move(move)
            return self.stay_still()
        except Exception:
            logger.exception('error hunting')
            return self.stay_still()

    def bank(self):
        '''Tells the ship where to go when going to bank halite at a drop off

        Returns:
            ship.move -- Returns a ship command as expected by the command queue
        '''
        logger.debug(f'{self.ship_id} is banking')
        try:
            target = self.closest_drop.position
            move = self.game_map.naive_navigate(self.ship, target)
            if move is Direction.Still:
                return self.go_random_for_equal_distance(target_location=self.closest_drop)
            return self.ship.move(move)
        except Exception:
            logger.exception("error banking")
            return self.stay_still()

    def bank_unsafe(self):
        '''Tells the ship where to go when going to bank halite at a drop off.
           Will crash into other ships if moving onto a shipyard
           to drop halite more quickly at the end of the game.

        Returns:
            ship.move -- Returns a ship command as expected by the command queue
        '''
        logger.debug('%s going to bank unsafe', str(self.ship_id))
        try:
            target = self.closest_drop.position
            unsafe_moves = self.game_map.get_unsafe_moves(
                self.ship.position, target)
            if unsafe_moves:
                direction = unsafe_moves[0]
            else:
                return self.ship.move(self.game_map.naive_navigate(self.ship, target))

            target_position = self.ship.position.directional_offset(direction)
            if self.game_map[target_position].has_structure:
                return self.ship.move(direction)
            return self.ship.move(self.game_map.naive_navigate(self.ship, target))

        except Exception:
            logger.exception('error in bank unsafe')
            return self.stay_still()

    def build(self):
        '''Tells the ship to navigate to the best location for a dropoff
          and if it is on that location, it will attempt to build the dropoff

        Returns:
            ship.move -- Returns a ship command as expected by the command queue
        '''
        logger.debug(f'{self.ship_id} is building.')
        try:
            target = self.navy.admiral.map.best_location.position
            move = self.game_map.naive_navigate(self.ship, target)
            if self.current_location.position == self.navy.admiral.map.best_location.position:
                logger.debug(f'{self.ship_id} built a dropoff.')
                return self.ship.make_dropoff()
            if self.can_afford_to_move:
                return self.ship.move(move)
            return self.ship.stay_still()
        except Exception:
            logger.exception('error building')
            return self.stay_still()

    def loot(self):
        '''Tells the ship to stay and loot the cell

        Returns:
            ship.move -- Returns a ship command as expected by the command queue
        '''
        logger.debug(f'{self.ship_id} looting')
        return self.stay_still()

    def go_random_safe(self):
        '''Tells the ship to go randomly and trys again once if it can't find a spot to move

        Returns:
            ship.move -- Returns a ship command as expected by the command queue
        '''
        logger.debug(f'{self.ship_id} going random safe')
        try:
            if self.can_afford_to_move:
                target = self.current_location.get_random_neighbor_position_without_structure()
                if target is self.last_location.position:
                    self.go_random_unsafe()
                return self.ship.move(
                    self.game_map.naive_navigate(self.ship, target))
            return self.stay_still()
        except Exception:
            logger.exception('error in go_random_safe')
            return self.stay_still()

    def go_random_unsafe(self):
        '''Tells the ship to go randomly or else it stays still

        Returns:
            ship.move -- Returns a ship command as expected by the command queue
        '''
        logger.debug(f'{self.ship_id} going random unsafe')
        try:
            if self.can_afford_to_move:
                target = self.current_location.get_random_neighbor_position_without_structure()
                return self.ship.move(
                    self.game_map.naive_navigate(self.ship, target))
            return self.stay_still()
        except Exception:
            logger.exception('error in go_random_unsafe')
            return self.stay_still()

    def go_random_for_equal_distance(self, target_location):
        '''Tells the ship to go randomly for an equal amount of distance that it would 
            be traveling for the target_location parameter or else stay still 

        Returns:
            ship.move -- Returns a ship command as expected by the command queue
        '''
        try:
            logger.debug(f'{self.ship_id} going random')
            target_distance = self.game_map.calculate_distance(
                self.ship.position, target_location.position)
            neighbors = self.ship.position.get_surrounding_cardinals()
            nearby_cells = []
            for neighbor in neighbors:
                if not self.game_map[neighbor].is_occupied and \
                        self.game_map[neighbor].position != self.last_location.position:
                    nearby_cells.append(self.game_map[neighbor])
            if not nearby_cells:
                return self.ship.stay_still()
            choices = []
            for cell in nearby_cells:
                distance = self.game_map.calculate_distance(
                    cell.position, target_location.position)
                if distance <= target_distance:
                    choices.append(cell)
            if not choices:
                return self.ship.stay_still()
        except Exception:
            logger.exception('error in initializing go_random')
            return self.ship.stay_still()

        try:
            if self.can_afford_to_move:
                target = random.choice(choices).position
                return self.ship.move(
                    self.game_map.naive_navigate(self.ship, target))
            return self.stay_still()
        except Exception:
            logger.exception('error in go_random')
            return self.stay_still()

    def stay_still(self):
        '''Tells the ship to stay still

        Returns:
            ship.move -- Returns a ship command as expected by the command queue
        '''
        return self.ship.stay_still()
