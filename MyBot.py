#!/usr/bin/env python3
# Python 3.7

import hlt
from hlt import constants
from hlt.positionals import Direction, Position
import random
import logging
# import numpy as np
import time


# def timefunc(f):
#     def f_timer(*args, **kwargs):
#         start = time.time()
#         result = f(*args, **kwargs)
#         end = time.time()
#         logging.info(f.__name__ + ' took ' + str(end - start))
#         return result
#     return f_timer


game = hlt.Game()

game.ready("MyPythonBot")
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

hlt.game_map.MapCell.value = 0
# hlt.game_map.MapCell.fitness = 0
total_halite = 0

while True:
    game.update_frame()
    me = game.me
    game_map = game.game_map
    command_queue = []
    dropoffs = me.get_dropoffs()
    dropoffs.append(me.shipyard)

    bank = me.halite_amount
    # logging.info('bank: ' + str(me.halite_amount))

    total_halite += bank
    # logging.info('total_halite: ' + str(total_halite))

    all_cells = []
    for x in range(game_map.width):
        for y in range(game_map.height):
            position = Position(x, y)
            game_map[position].value = game_map[position].halite_amount
            all_cells.append(game_map[position])

    def make_drop(bank):
        logging.info('making dropoff')
        bank -= constants.DROPOFF_COST
        return ship.make_dropoff()

    def get_closest_drop():
        distances = []
        for dropoff in dropoffs:
            distances.append((
                dropoff, game_map.calculate_distance(ship.position, dropoff.position)))
        return min(distances, key=lambda x: x[1])[0]

    def get_random():
        nearby_positions = [
            ship_position.position.directional_offset(Direction.North), ship_position.position.directional_offset(Direction.South), ship_position.position.directional_offset(Direction.East), ship_position.position.directional_offset(Direction.West)]
        nearby_cells = []
        for position in nearby_positions:
            if not game_map[position].is_occupied:
                nearby_cells.append(game_map[position])
        return random.choice(nearby_cells).position

    def go_random():
        logging.info('going to random cell')
        target = get_random()
        return ship.move(
            game_map.naive_navigate(ship, target))

    def go_drop_final():
        try:
            logging.info('going to final drop')
            dropoffs = me.get_dropoffs()
            dropoffs.append(me.shipyard)
            if len(dropoffs) > 1:
                logging.info('dropoffs:' + str(dropoffs))
                distances = []
                for dropoff in dropoffs:
                    distances.append((
                        dropoff, game_map.calculate_distance(ship.position, dropoff.position)))
                closest_drop = min(distances, key=lambda x: x[1])[0]
                logging.info('closest_drop: ' + str(closest_drop))
                target = closest_drop.position
            else:
                target = dropoffs[0].position
            direction = game_map.get_unsafe_moves(ship.position, target)[0]
            target_position = ship_position.position.directional_offset(
                direction)
            if game_map[target_position].has_structure:
                logging.info('mad dash')
                return ship.move(direction)
            else:
                logging.info('final drop target: ' + str(target))
                return ship.move(game_map.naive_navigate(
                    ship, target))

        except Exception as err:
            logging.warning('error in final drop')
            logging.warning(err)
            return ship.move(game_map.naive_navigate(
                ship, me.shipyard.position))

    def go_drop():
        try:
            logging.info('going to drop')
            if len(dropoffs) > 1:
                target = get_closest_drop().position
            else:
                target = dropoffs[0].position
        except Exception as err:
            logging.warning(err)
            target = me.shipyard.position
        return ship.move(game_map.naive_navigate(
            ship, target))

    def go_get_halite():
        logging.info('going to get halite')
        best_cell = get_best_cell()
        try:
            move = game_map.naive_navigate(ship, best_cell.position)
            logging.info(move)
            target_position = ship_position.position.directional_offset(
                move)
            logging.info(game_map[target_position].has_structure)
            if not game_map[target_position].has_structure:
                target = best_cell.position
                all_cells.remove(best_cell)
                return ship.move(move)
            else:
                return ship.move(
                    game_map.naive_navigate(ship, get_random()))
        except Exception as err:
            logging.warning(err)
            target = max(all_cells, key=lambda x: x.value).position
            return ship.move(
                game_map.naive_navigate(ship, target))

    def get_best_cell():
        best_fitness = 0
        for cell in all_cells:
            distance = (game_map.calculate_distance(
                ship.position, cell.position))
            if distance is 0:
                distance = 0.1
            fitness = (cell.value^2) / distance
            if fitness > best_fitness:
                best_fitness = fitness
                best_cell = cell
        logging.info('best_cell: ' + str(best_cell))
        return best_cell

    def get_dropability():
        # TODO: Find the best location for drop zone and build it there instead.
        nearby_ships = get_number_of_nearby_ships()
        distance = game_map.calculate_distance(
            ship.position, get_closest_drop().position)
        if nearby_ships is 4 and distance > 5:
            return True
        else:
            return False

    def get_number_of_nearby_ships():
        nearby_positions = [
            ship_position.position.directional_offset(Direction.North),
            ship_position.position.directional_offset(Direction.South),
            ship_position.position.directional_offset(Direction.East),
            ship_position.position.directional_offset(Direction.West)]
        nearby_ships = 0
        for position in nearby_positions:
            if game_map[position].is_occupied:
                nearby_ships += 1
        return nearby_ships

    for index, ship in enumerate(me.get_ships()):
        try:
            ship_position = game_map[ship.position]
            cost_to_move = .1 * ship_position.halite_amount

            nearby_ships = get_number_of_nearby_ships()

            if game.turn_number >= constants.MAX_TURNS/1.075 and not ship_position.has_structure:
                command = go_drop_final()
            elif get_dropability() and bank > constants.DROPOFF_COST and not ship_position.has_structure:
                command = make_drop(bank)
            elif nearby_ships < 3 and ship.halite_amount >= 750 - cost_to_move and not ship_position.has_structure:
                command = go_drop()
            elif nearby_ships < 3 and cost_to_move <= ship.halite_amount and not ship_position.has_structure:
                command = go_get_halite()
            elif cost_to_move <= ship.halite_amount:
                command = go_random()
            else:
                command = ship.stay_still()
            command_queue.append(command)
        except Exception as err:
            logging.warning(err)
            command_queue.append(ship.stay_still())

        # logging.info(data)
    if game.turn_number <= constants.MAX_TURNS/1.5 and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied:
        command_queue.append(me.shipyard.spawn())
        bank -= constants.SHIP_COST

    # if me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied:
    #     command_queue.append(me.shipyard.spawn())

    game.end_turn(command_queue)
