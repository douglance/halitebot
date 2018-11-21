
    # for index, ship in enumerate(ships):
    #     try:
    #         ship_position = game_map[ship.position]
    #         cost_to_move = (.1 * ship_position.halite_amount)
    #         ship_can_afford_to_move = cost_to_move <= ship.halite_amount
    #         player_can_afford_dropoff = bank > constants.DROPOFF_COST
    #         ship_ready_to_drop = ship.halite_amount > (
    #             constants.MAX_HALITE * .8) - cost_to_move
    #         game_ending = game.turn_number >= constants.MAX_TURNS/1.05
    #         drop_time = game.turn_number >= constants.MAX_TURNS/2
    #         ship_id = 'Ship-' + str(ship.id)
    #         drop_building = True

    #         nearby_ships = get_number_of_nearby_ships(ship_position.position)

    #         if game_ending:
    #             command = go_drop_final()
    #         # elif location_is_good_for_drop() and player_can_afford_dropoff:
    #         elif ship_position is best_drop_location:
    #             command = make_drop(bank)
    #         elif ship_ready_to_drop and \
    #                 not ship_position.has_structure and \
    #                 player_can_afford_dropoff and \
    #                 drop_time:
    #             command = go_to_best_drop()
    #         elif ship_ready_to_drop and \
    #                 not ship_position.has_structure:
    #             command = go_drop()
    #         elif location_good_for_looting() and \
    #                 not ship_position.has_structure:
    #             command = go_loot()
    #         elif nearby_ships is 4 and \
    #                 ship_can_afford_to_move and \
    #                 not ship_position.has_structure:
    #             command = go_toward_best()
    #         elif ship_can_afford_to_move:
    #             command = go_get_halite()
    #         else:
    #             logger.info(ship_id + ' staying still')
    #             command = ship.stay_still()
    #         command_queue.append(command)
    #     except Exception as err:
    #         logger.warning(err)
    #         command_queue.append(ship.stay_still())

    
    # @timefunc
    def get_best_cell_by_neighborhood_halite_amount():
        logger.info('get_best_cell_by_neighborhood_halite_amount')
        best_value = 0
        try:
            for cell in all_cells:
                cell_set = []
                cell_set.append(cell)
                neighbors = cell.position.get_surrounding_cardinals()
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
                if total_halite > best_value:
                    best_value = total_halite
                    best_cell = cell
            logger.info('best_cell: ' + str(best_cell))
            return best_cell
        except Exception as err:
            logger.warning(
                'error in get_best_cell_by_neighborhood_halite_amount')
            logger.warning(err)
            return get_best_cell()

    # best_drop_location = get_best_cell_by_neighborhood_halite_amount()

    def get_neighborhood_value(cell):
        neighbors = cell.position.get_surrounding_cardinals()
        total_halite = 0
        total_halite += game_map[cell].halite_amount
        for neighbor in neighbors:
            total_halite += game_map[neighbor].halite_amount
        return total_halite

    def make_drop(bank):
        logger.info(ship_id + ' is making a dropoff')
        try:
            if location_is_good_for_drop(game_map[ship_position]):
                bank -= constants.DROPOFF_COST
                return ship.make_dropoff()
            else:
                return ship.stay_still()
        except Exception as err:
            logger.warning('error making drop')
            logger.warning(err)
            return ship.stay_still()

    def go_to_best_drop():
        logger.info('going to best drop location')
        try:
            target = best_drop_location
            return ship.move(
                game_map.naive_navigate(ship, target.position))
        except Exception as err:
            logger.warning('error making drop')
            logger.warning(err)
            return go_random()

    def get_closest_drop():
        distances = []
        for dropoff in dropoffs:
            distances.append((
                dropoff, game_map.calculate_distance(ship.position, dropoff.position)))
        return min(distances, key=lambda x: x[1])[0]

    # def get_cost_to_drop():
        closest_drop = get_closest_drop()
        total_cost = 0
        position = ship
        # closest_drop_distance = game_map.calculate_distance(
        #     ship.position, closest_drop.position)

        next_step = game_map.naive_navigate(ship, closest_drop.position)
        target_position = ship_position.position.directional_offset(
            next_step)
        logger.info(target_position)
        while game_map[target_position] is not closest_drop:
            total_cost += game_map[next_step].halite_amount * .1
            next_step = ship_position.position.directional_offset(
                next_step)
            logger.info(total_cost)

    def go_random():
        logger.info('going to random cell')
        try:
            target = get_random()
            return ship.move(
                game_map.naive_navigate(ship, target))
        except:
            return ship.stay_still()

    def go_drop_final():
        try:
            logger.info(ship_id + ' going to final drop')
            target = get_closest_drop().position
            direction = game_map.get_unsafe_moves(ship.position, target)[0]
            target_position = ship_position.position.directional_offset(
                direction)
            if game_map[target_position].has_structure:
                return ship.move(direction)
            else:
                return ship.move(game_map.naive_navigate(
                    ship, target))

        except Exception as err:
            logger.warning('error in final drop')
            logger.warning(err)
            return ship.move(game_map.naive_navigate(
                ship, get_closest_drop().position))

    def go_drop():
        logger.info(ship_id + ' is going to drop')
        try:
            target = get_closest_drop().position
        except Exception as err:
            logger.warning(err)
            target = me.shipyard.position
        move = game_map.naive_navigate(
            ship, target)
        return ship.move(move)

    def go_toward_best():
        logger.info('going toward best')
        try:
            target = max(all_cells, key=lambda x: x.value).position
            return ship.move(
                game_map.naive_navigate(ship, target))
        except Exception as err:
            logger.warning('error going toward best')
            logger.warning(err)
            return go_random()

    def go_get_halite():
        logger.info(ship_id + ' is going to get halite')
        try:
            best_cell = get_best_cell()
            move = game_map.naive_navigate(ship, best_cell.position)
            target_position = ship_position.position.directional_offset(
                move)
            if not game_map[target_position].has_structure and \
                    move is not Direction.Still:
                all_cells.remove(best_cell)
                return ship.move(move)
            else:
                return go_random()
        except Exception as err:
            logger.warning(err)
            return go_toward_best()

    def get_best_cell():
        best_fitness = 0
        for cell in all_cells:
            distance = game_map.calculate_distance(
                ship.position, cell.position)
            if distance is 0:
                distance = 0.1
            fitness = round(cell.value / distance)
            if fitness > best_fitness:
                best_fitness = fitness
                best_cell = cell
        return best_cell

    def get_best_cell_by_neighborhood():
        best_fitness = 0
        for cell in all_cells:
            cell_value = get_neighborhood_value(cell)
            distance = (game_map.calculate_distance(
                ship.position, cell.position))
            if distance is 0:
                distance = 0.1
            fitness = round((cell_value) / (distance/2))
            if fitness > best_fitness:
                best_fitness = fitness
                best_cell = cell
        return best_cell

    def location_is_good_for_drop(cell):
        distance = game_map.calculate_distance(
            cell.position, get_closest_drop().position)
        if not cell.has_structure:
            return True
        else:
            return False

    def get_number_of_nearby_ships(position):
        nearby_positions = [
            position.directional_offset(Direction.North),
            position.directional_offset(Direction.South),
            position.directional_offset(Direction.East),
            position.directional_offset(Direction.West)]
        nearby_ships = 0
        for position in nearby_positions:
            if game_map[position].is_occupied:
                nearby_ships += 1
        return nearby_ships

    def location_good_for_looting():
        expected_harvest = (.25*ship_position.halite_amount)
        available_inventory = (constants.MAX_HALITE-ship.halite_amount)
        half_of_the_best_return = .125*get_best_cell().halite_amount
        if expected_harvest >= half_of_the_best_return and expected_harvest < available_inventory:
            return True
        else:
            return False

    def go_loot():
        logger.info(ship_id + ' is looting')
        return ship.stay_still()

    def contains(list, filter):
        for x in list:
            if filter(x):
                return True
        return False



    def get_all_cells():
        all_cells = []
        for x in range(game_map.width):
            for y in range(game_map.height):
                position = Position(x, y)
                game_map[position].value = game_map[position].halite_amount
                all_cells.append(game_map[position])
        return all_cells

    all_cells = get_all_cells()