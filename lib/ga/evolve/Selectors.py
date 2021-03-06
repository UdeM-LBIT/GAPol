"""

:mod:`Selectors` -- selection methods module
==============================================================

This module have the *selection methods*, like roulette wheel, tournament, ranking, etc.

"""

import random
import Consts

def GRankSelector(population, **args):
    """ The Rank Selector - This selector will pick the best individual of
    the population every time.
    """
    count = 0

    if args["popID"] != GRankSelector.cachePopID:
        best_fitness = population.bestFitness().fitness
        for index in xrange(1, len(population.internalPop)):
            if population[index].fitness == best_fitness:
                count += 1

        GRankSelector.cachePopID = args["popID"]
        GRankSelector.cacheCount = count

    else:
        count = GRankSelector.cacheCount

    return population[random.randint(0, count)]

GRankSelector.cachePopID = None
GRankSelector.cacheCount = None

def GUniformSelector(population, **args):
    """ The Uniform Selector """
    return population[random.randint(0, len(population) - 1)]

def GTournamentSelector(population, **args):
    """ The Tournament Selector

    It accepts the *tournamentPool* population parameter.

    .. note::
        the Tournament Selector uses the Roulette Wheel to
        pick individuals for the pool

    """
    choosen = None
    poolSize = population.getParam("tournamentPool", Consts.CDefTournamentPoolSize)
    tournament_pool = [GRouletteWheel(population, **args) for i in xrange(poolSize)]
    choosen = min(tournament_pool, key=lambda ind: ind.fitness)
    
    return choosen

def GTournamentSelectorAlternative(population, **args):
    """ The alternative Tournament Selector

    This Tournament Selector don't uses the Roulette Wheel

    It accepts the *tournamentPool* population parameter.
    """
    pool_size = population.getParam("tournamentPool", Consts.CDefTournamentPoolSize)
    len_pop = len(population)
    tournament_pool = [population[random.randint(0, len_pop - 1)] for i in xrange(pool_size)]
    choosen = min(tournament_pool, key=lambda ind: ind.fitness)
    
    return choosen

def GRouletteWheel(population, **args):
    """ The Roulette Wheel selector """
    psum = None
    if args["popID"] != GRouletteWheel.cachePopID:
        GRouletteWheel.cachePopID = args["popID"]
        psum = GRouletteWheel_PrepareWheel(population)
        GRouletteWheel.cacheWheel = psum
    else:
        psum = GRouletteWheel.cacheWheel

    cutoff = random.random()
    lower = 0
    upper = len(population) - 1
    while(upper >= lower):
        i = lower + ((upper - lower) / 2)
        if psum[i] > cutoff:
            upper = i - 1
        else:
            lower = i + 1

    lower = min(len(population) - 1, lower)
    lower = max(0, lower)

    return population.bestFitness(lower)

GRouletteWheel.cachePopID = None
GRouletteWheel.cacheWheel = None

def GRouletteWheel_PrepareWheel(population):
    """ A preparation for Roulette Wheel selection """

    len_pop = len(population)

    psum = [i for i in xrange(len_pop)]

    population.statistics()

    pop_fitMax = population.stats["fitMax"]
    pop_fitMin = population.stats["fitMin"]

    if pop_fitMax == pop_fitMin:
        for index in xrange(len_pop):
            psum[index] = (index + 1) / float(len_pop)
    elif (pop_fitMax > 0 and pop_fitMin >= 0) or (pop_fitMax <= 0 and pop_fitMin < 0):
        population.sort()
        psum[0] = -population[0].fitness + pop_fitMax + pop_fitMin
        for i in xrange(1, len_pop):
            psum[i] = -population[i].fitness + pop_fitMax + pop_fitMin + psum[i - 1]
        for i in xrange(len_pop):
            psum[i] /= float(psum[len_pop - 1])

    return psum
