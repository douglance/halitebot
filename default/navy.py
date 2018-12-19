#!/usr/bin/env python3
# Python 3.6

import hlt
from hlt import constants
from hlt.entity import Ship
from hlt.positionals import Direction, Position
from hlt.game_map import MapCell
import random
import logging
import math
from .map import Location, Map
from .constants import LOG_LEVEL, DROP_BARRIER

import logging

logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)

class Admiral():
    def __init__(self, player, map, game):
        self.player = player
        self.map = map
        self.game = game

    def get_ships(self):
        return self.player.get_ships()

class Navy():
    captains: dict

    def __init__(self, admiral):
        self.captains = {}
        self.admiral = admiral

    @property
    def game_map(self):
        return self.admiral.map.game_map

    @property
    def dropoffs(self):
        player = self.admiral.player
        dropoffs = player.get_dropoffs()
        dropoffs.append(player.shipyard)
        return dropoffs

    def update_captains(self):
        for ship in self.admiral.get_ships():
            location = Location(position=ship.position,
                                cell=self.game_map[ship.position],
                                map=self.admiral.map)
            captain = Captain(last_location=location, 
                              current_location=location, 
                              ship_id=ship.id,
                              navy=self)
            if not ship.id in self.captains:
                self.captains[ship.id] = captain

    @property
    def closest_to_drop_target(self):
        try:
            objs = []
            self.update_captains()
            for key, captain in self.captains.items():
                tpl = (captain, self.game_map.calculate_distance(captain.current_location.position, self.admiral.map.best_location.position))
                objs.append(tpl)
            closest = min(objs, key=lambda x: x[1])[0]
            return closest
        except Exception:
            logger.exception('Error in closest to drop target')
            return random.choice(list(self.captains.items()))



class Captain():
    last_location: Location
    current_location: Location
    navy: Navy
    ship_id: int

    def __init__(self,last_location, current_location, ship_id, navy):
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
        return self.navy.admiral.map.game_map

    @property
    def priority(self):
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
    def cost_to_move(self):
        return (.1 * self.current_location.cell.halite_amount)

    @property
    def distance_to_closest_drop(self):
        return self.game_map.calculate_distance(self.ship.position, self.closest_drop.position)
        
    
    @property
    def can_afford_to_move(self):
        return self.cost_to_move <= self.ship.halite_amount

    @property
    def number_of_nearby_ships(self):
        total = 0
        neighbors = self.current_location.position.get_surrounding_cardinals()
        for neighbor in neighbors:
            if self.game_map[neighbor].is_occupied:
                total += 1
        return total

    @property
    def ship(self):
        try:
            return self.navy.admiral.player.get_ship(self.ship_id)
        except Exception:
            logger.exception('Ship does not exist.')
            # navy.captains.remove(self)

    @property
    def status(self):
        if self.navy.admiral.game.turn_number >= constants.MAX_TURNS/1.05:
            return 'FINAL'
        elif self.navy.admiral.player.halite_amount > 5000 and self is self.navy.closest_to_drop_target and \
            round(len(self.navy.captains)/len(self.navy.dropoffs)) > 10:
            return 'BUILD'
        elif self.ship.halite_amount > DROP_BARRIER:
            return 'BANK'
        elif self.current_location.good_for_looting(self.ship):
            return 'LOOT'
        elif self.ship.halite_amount < DROP_BARRIER and self.can_afford_to_move:
            return 'HUNT'
        elif self.can_afford_to_move:
            return 'RAND'
        else:
            return 'MISC'

    @property
    def orders(self):
        position = self.ship.position
        self.last_location = self.current_location
        self.current_location = self.navy.admiral.map.get_location_from_position(position)
        if self.status is 'FINAL':
            return self.bank_unsafe()
        elif self.status is 'BANK':
            return self.bank()
        elif self.status is 'BUILD':
            return self.build()
        elif self.status is 'HUNT':
            return self.hunt()
        elif self.status is 'LOOT':
            return self.loot()
        elif self.status is 'RAND':
            return self.go_random_safe()
        else:
            return self.stay_still()


    # def move(self, target_location):
    #     """ Handles moving the ship """
    #     move = self.ship.move(self.ship.position, target_location.position)

    @property
    def closest_drop(self):
        try:
            return min(self.navy.dropoffs, key=lambda x: self.game_map.calculate_distance(self.ship.position, x.position))
        except Exception:
            logger.exception('error in closest_drop')

    @property
    def best_target_location(self):
        try:
            locations = self.navy.admiral.map.safe_locations
            return max(locations, key= lambda x:x.get_fitness(ship=self.ship))
        except Exception:
            logger.exception('error in best_target_location')

    def hunt(self):
        logger.debug(str(self.ship_id) + ' is hunting')
        try:
            if self.current_location.cell.has_structure:
                return self.go_random_safe()

            best_location = self.best_target_location
            move = self.game_map.naive_navigate(self.ship, best_location.position)
            target_position = self.ship.position.directional_offset(move)
            
            if self.game_map[target_position].has_structure:
                return self.go_random_safe()
            elif self.distance_to_closest_drop <= 1 and move is Direction.Still:
                return self.go_random_safe() 
            elif target_position == self.last_location.position:
                return self.ship.stay_still()
            elif self.can_afford_to_move:
                if move is Direction.Still and self.current_location.cell.halite_amount < 100:
                    return self.go_random_for_equal_distance(target_location=best_location) 
                self.navy.admiral.map.safe_locations.remove(best_location)
                return self.ship.move(move)

            else:
                return self.stay_still()
        except Exception:
            logger.exception('error hunting')
            return self.go_random_for_equal_distance(target_location=self.best_target_location)

    def bank(self):
        logger.debug(str(self.ship_id) + ' is banking')
        try:
            target = self.closest_drop.position
            move = self.game_map.naive_navigate(self.ship, target)
            if move is Direction.Still:
                return self.go_random_for_equal_distance(target_location=self.closest_drop)
            return self.ship.move(move)
        except Exception:
            logger.exception("error banking")
            target = self.closest_drop.position
            move = self.game_map.naive_navigate(self.ship, target)
            return self.ship.move(move)

    def bank_unsafe(self):
        logger.debug(str(self.ship_id) + ' going to bank unsafe')
        try:
            target = self.closest_drop.position
            unsafe_moves = self.game_map.get_unsafe_moves(self.ship.position, target)
            if unsafe_moves:
                direction = unsafe_moves[0]
            else:
                return self.ship.move(self.game_map.naive_navigate(self.ship, target))
            target_position = self.ship.position.directional_offset(direction)
            if self.game_map[target_position].has_structure:
                return self.ship.move(direction)
            else:
                return self.ship.move(self.game_map.naive_navigate(self.ship, target))

        except Exception:
            logger.exception('error in bank unsafe')
            return self.ship.move(self.game_map.naive_navigate(
                self.ship, self.closest_drop.position))

    def build(self):
        logger.info(f'{self.ship_id} is building.')
        try:
            target = self.navy.admiral.map.best_location.position
            move = self.game_map.naive_navigate(self.ship, target)
            if self.current_location.position == self.navy.admiral.map.best_location.position:
                logger.info(f'{self.ship_id} built.')
                return self.ship.make_dropoff()
            else:
                if self.can_afford_to_move:
                    logger.info(f'{self.ship_id} going to build location.')
                    return self.ship.move(move)
                else:
                    return self.ship.stay_still()
        except Exception:
            logger.exception('error building')
            return self.ship.stay_still()

    def loot(self):
        logger.debug(str(self.ship_id) + ' looting')
        return self.ship.stay_still()

    def go_random_safe(self):
        logger.debug(str(self.ship_id) + ' going random safe')
        try:
            if self.can_afford_to_move:
                target = self.current_location.get_random_neighbor_position_without_structure()
                if target is self.last_location.position:
                    self.go_random_unsafe()
                return self.ship.move(
                    self.game_map.naive_navigate(self.ship, target))
            else:
                return self.stay_still()
        except Exception:
            logger.exception('error in go_random_safe')
            return self.ship.stay_still()

    def go_random_unsafe(self):
        logger.debug(str(self.ship_id) + ' going random unsafe')
        try:
            if self.can_afford_to_move:
                target = self.current_location.get_random_neighbor_position_without_structure()
                return self.ship.move(
                    self.game_map.naive_navigate(self.ship, target))
            else:
                return self.stay_still()
        except Exception:
            logger.exception('error in go_random_unsafe')
            return self.ship.stay_still()
    
    def go_random_for_equal_distance(self, target_location):
        try:
            logger.debug(str(self.ship_id) + ' going random')
            target_distance = self.game_map.calculate_distance(self.ship.position, target_location.position)
            neighbors = self.ship.position.get_surrounding_cardinals()        
            nearby_cells = []
            for neighbor in neighbors:
                if not self.game_map[neighbor].is_occupied and self.game_map[neighbor].position != self.last_location.position:
                    nearby_cells.append(self.game_map[neighbor])
            if not nearby_cells:
                return self.ship.stay_still()
            choices = []
            for cell in nearby_cells:
                distance = self.game_map.calculate_distance(cell.position, target_location.position)
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
            else:
                return self.stay_still()
        except Exception:
            logger.exception('error in go_random')
            return self.ship.stay_still()

    def stay_still(self):
        return self.ship.stay_still()

