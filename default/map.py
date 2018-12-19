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
import logging
from .constants import LOG_LEVEL

logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)

class Location():
    position: Position
    cell: MapCell
    safe: bool = True
    # map: Map

    def __init__(self, position, cell, map):
        self.position = position
        self.cell = cell
        self.safe = True
        self.map = map

    def __eq__(self, other):
        if self.position.x is other.position.y and self.position.y is other.position.y:
            return True
        else:
            return False

    @property
    def neighborhood_value(self):
        cell_set = []
        cell_set.append(self.cell)
        neighbors = self.position.get_surrounding_cardinals()
        for neighbor in neighbors:
            if self.map.game_map[neighbor] not in cell_set:
                cell_set.append(self.map.game_map[neighbor])
                neighbor_neighbors = self.map.game_map[neighbor].position.get_surrounding_cardinals(
                )
                for neighbor_neighbor in neighbor_neighbors:
                    if self.map.game_map[neighbor_neighbor] not in cell_set:
                        cell_set.append(self.map.game_map[neighbor_neighbor])
        total_halite = 0
        for cell in cell_set:
            total_halite += cell.halite_amount
        return total_halite

    @property
    def value(self):
        return self.cell.halite_amount

    @property
    def distance_to_closest_drop(self):
        return self.map.game_map.calculate_distance(self.position, self.closest_drop.position)
    
    @property
    def closest_drop(self):
        try:
            distances = []
            dropoffs = self.map.game.me.get_dropoffs()
            dropoffs.append(self.map.game.me.shipyard)
            for dropoff in dropoffs:
                distances.append((
                    dropoff, self.map.game_map.calculate_distance(self.position, dropoff.position)))
            return min(distances, key=lambda x: x[1])[0]
        except Exception:
            logger.exception('error in closest_drop')

    def get_random_neighbor_position_without_structure(self):
        neighbors = self.position.get_surrounding_cardinals()        
        nearby_cells = []
        for neighbor in neighbors:
            if not self.map.game_map[neighbor].is_occupied and \
               not self.map.game_map[neighbor].has_structure:
                nearby_cells.append(self.map.game_map[neighbor])
        if not nearby_cells:
            return self.position
        else:
            return random.choice(nearby_cells).position

    def good_for_looting(self, ship):
        expected_harvest = (.25*self.cell.halite_amount)
        available_inventory = (constants.MAX_HALITE-ship.halite_amount)
        if expected_harvest >= constants.MAX_HALITE*.1 and expected_harvest < available_inventory and not self.cell.has_structure:
        # if expected_harvest < available_inventory 
            return True
        else:
            return False

    def get_fitness(self, ship):
        distance = self.map.game_map.calculate_distance(self.position, ship.position)
        distance *= 2
        if distance is 0:
            distance = 1
        return round(self.value / distance)

class Map():
    locations: list
    safe_locations: list
        
    def __init__(self, game, locations=list, safe_locations=list):
        self.locations = []
        self.safe_locations = []
        self.game_map = game.game_map
        self.game = game
        for x in range(self.game_map.width):
            for y in range(self.game_map.height):
                position = Position(x, y)
                cell=self.game_map[position]
                location = Location(position=position, cell=cell, map=self)
                self.locations.append(location)

    def get_location_from_position(self, position):
        return [location for location in self.locations if location.position.x == position.x and location.position.y == position.y][0]
    
    def reset(self):
        logger.debug('Resetting Map')
        self.safe_locations = [location for location in self.locations if not location.cell.has_structure]
        
    @property
    def best_location(self):
        return max(self.safe_locations, key=lambda x: x.value)
