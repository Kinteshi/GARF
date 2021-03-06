import random
import numpy as np
from deap import creator, base, tools, algorithms
from .misc import _chromosome_to_key
import time



class GeneticAlgorithmRandomForest():

    def __init__(self, n_trees, evaluator, seed=2567, cx_pb=0.9, ch_mut_pb=0.2, g_mut_pb=0.2, pop_size=75, n_gen=50, tour_size=2, dict_persist=None):

        random.seed(seed)
        np.random.seed(seed)
        self.__seed = seed
        self.__n_trees = n_trees
        self.__cx_pb = cx_pb
        self.__ch_mut_pb = ch_mut_pb
        self.__g_mut_pb = g_mut_pb
        self.__pop_size = pop_size
        self.__n_gen = n_gen
        self.__tour_size = tour_size
        self.__dict_persist = dict_persist
        self.__evaluator = evaluator

        self.__archive_bank = {}
        self.__population_bank = {}
        self.__pareto_front_bank = {}
        self.__last_gen = 0

        self.__model = None
        self.__collection = None
        self.__archive = None
        self.__population = None
        self.__elapsed_time = None

        self.__ga_setup()

    def __ga_setup(self):

        self.__creator = creator
        self.__creator.create('myFitness', base.Fitness,
                              weights=self.__evaluator.weights)
        self.__creator.create('individual', list,
                              fitness=self.__creator.myFitness)

        self.__toolbox = base.Toolbox()
        self.__toolbox.register("attrBool", random.randint, 0, 1)
        self.__toolbox.register("individual", tools.initRepeat,
                                self.__creator.individual, self.__toolbox.attrBool, n=self.__n_trees)
        self.__toolbox.register(
            "population", tools.initRepeat, list, self.__toolbox.individual)

        # Evaluation function
        self.__toolbox.register("evaluate", self.__evaluator.evaluate)
        self.__toolbox.register("mate", tools.cxTwoPoint)
        self.__toolbox.register("mutate", tools.mutFlipBit,
                                indpb=self.__g_mut_pb)
        self.__toolbox.register("selectTournament", tools.selTournament,
                                tournsize=self.__tour_size)

        self.__pareto_front = tools.ParetoFront()

        self.__toolbox.register("select", tools.selSPEA2)

        self.__population = self.__toolbox.population(n=self.__pop_size)

        self.__archive = []
        self.__last_gen = 0

    def evolve_model(self, n_gen=0, warm_start=False):

        if not warm_start and self.__last_gen != 0:
            self.__population_bank = {}
            self.__archive_bank = {}
            self.__last_gen = 0
            self.__population = self.__toolbox.population(n=self.__pop_size)
            self.__archive = []
            self.__pareto_front.clear()

        start = time.time()

        for gen in range(self.__last_gen, self.__last_gen + n_gen):

            loop_time = time.time()

            self.__last_gen = gen

            fits_population = self.__toolbox.evaluate(
                self.__population, bank=self.__population_bank)
            fits_archive = self.__toolbox.evaluate(
                self.__archive, bank=self.__population_bank)

            for fit, ind in zip(fits_population, self.__population):
                ind.fitness.values = fit
            for fit, ind in zip(fits_archive, self.__archive):
                ind.fitness.values = fit

            self.__bank__chromosomes()

            self.__archive = self.__toolbox.select(
                self.__population + self.__archive, k=self.__pop_size)

            self.__bank_archive()

            mating_pool = self.__toolbox.selectTournament(
                self.__archive, k=self.__pop_size)

            offspring_pool = map(self.__toolbox.clone, mating_pool)

            offspring_pool = algorithms.varAnd(
                offspring_pool, self.__toolbox, cxpb=self.__cx_pb, mutpb=self.__ch_mut_pb)

            self.__population = offspring_pool

            print(f'|Gen{gen}==>{time.time() - loop_time}|')

            if len(self.__evaluator.metrics) > 1:
                self.__pareto_front.clear()
                self.__pareto_front.update(self.__archive)
                self.__bank_pareto_front()

        end = time.time()
        self.__elapsed_time = end - start
        self.__persist_data()

        if len(self.__evaluator.metrics) < 2:
            return self.get_best_ind()
        else:
            return list(self.__pareto_front)

    def __bank_archive(self):

        self.__archive_bank[f'{self.__last_gen}'] = [
            _chromosome_to_key(ind) for ind in self.__archive]

    def __bank__chromosomes(self):

        for ind in self.__population:
            key = _chromosome_to_key(ind)
            if key in self.__population_bank:
                continue
            self.__population_bank[key] = {}
            for i in range(0, len(self.__evaluator.metrics)):
                self.__population_bank[key][self.__evaluator.metrics[i]
                                            ] = ind.fitness.values[i].tolist()
            self.__population_bank[key]['generated'] = self.__last_gen

    def __bank_pareto_front(self):

        self.__pareto_front_bank[f'{self.__last_gen}'] = list(set([
            _chromosome_to_key(ind) for ind in self.__pareto_front]))

    def __persist_data(self):

        if not self.__dict_persist:
            raise ValueError('Persist object not set')

        self.__dict_persist.save(self.__population_bank, 'population_bank')
        self.__dict_persist.save(self.__archive_bank, 'archive_bank')
        self.__dict_persist.save([self.__elapsed_time], 'elapsed_time')

        if len(self.__evaluator.metrics) > 1:
            pareto_front = [_chromosome_to_key(
                ind) for ind in list(self.__pareto_front)]
            self.__dict_persist.save(pareto_front, 'pareto_front')
            self.__dict_persist.save(
                self.__pareto_front_bank, 'pareto_front_bank')
        else:
            best = self.get_best_ind()
            self.__dict_persist.save(best, 'best_ind')

    def get_pareto_front(self):

        if self.__last_gen == 0:
            raise RuntimeError('Evolution was not run for this model.')

        if len(self.__evaluator.metrics) < 2:
            raise RuntimeError(
                'A single objective evaluator is being used. Use get_best_ind() method instead.')

        return list(self.__pareto_front)

    def get_best_ind(self):

        if self.__last_gen == 0:
            raise RuntimeError('Evolution was not run for this model.')

        for i, ind in enumerate(self.__archive):
            if i == 0:
                bigger = i
            else:
                if self.__archive[bigger].fitness.values[0] < ind.fitness.values[0]:
                    bigger = i

        return _chromosome_to_key(self.__archive[bigger])