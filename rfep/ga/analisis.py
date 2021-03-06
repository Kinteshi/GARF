from pathlib import Path
from .misc import DatasetHandler
from .evaluation import Evaluator
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import json
from rpy2 import robjects


class Analyst():

    def __init__(self, objectives, weights, mp, dp, baselines_path, dataset_name, n_trees, seed):

        self.__dict_persist = dp
        self.__model_persist = mp
        self.__model = None
        self.__evaluator = None
        self.__dataset_handler = None
        self.__dataset_name = dataset_name
        self.baselines_path = baselines_path
        self.__n_trees = n_trees
        self.__seed = seed
        self.__objectives = objectives
        self.__weights = weights

    def __load_model(self, fold):

        self.__model = self.__model_persist.load(
            f'Fold{fold}/{self.__n_trees}{self.__seed}')

    def __process_fold(self, fold):

        self.__load_model(fold)

        self.__population_bank = self.__dict_persist.load(
            f'Fold{fold}/population_bank')

        if len(self.__evaluator.metrics) == 2:
            pareto_front = self.__dict_persist.load(f'Fold{fold}/pareto_front')
            best = 0
            for i, ind in enumerate(pareto_front):
                if i == 0:
                    best = i
                else:
                    if np.mean(self.__population_bank[pareto_front[best]]['ndcg']) < np.mean(self.__population_bank[ind]['ndcg']):
                        best = i
            self.__best = pareto_front[best]
        else:
            self.__best = self.__dict_persist.load(f'Fold{fold}/best_ind')

        evaluations = self.__fold_comparison(fold)

        report = {}

        for ind, fitness in zip(['initial', 'final'], evaluations):
            report[ind] = {}
            for fit, value in zip(['ndcg', 'georisk'], fitness):
                report[ind][fit] = value.tolist()

        report['initial']['n_trees'] = len(self.__best)
        report['final']['n_trees'] = self.__best.count('1')
        report['initial']['ndcg_mean'] = np.mean(report['initial']['ndcg'])
        report['final']['ndcg_mean'] = np.mean(report['final']['ndcg'])

        self.__dict_persist.save(report, f'Fold{fold}/fold_comparison')

        return evaluations

    def __fold_comparison(self, fold):

        matrix = []

        path = Path(self.baselines_path) / f'Fold{fold}'

        for file_name in path.glob('*.txt'):
            with open(file_name, 'r') as file:
                matrix.append([float(line.rstrip('\n')) for line in file])
                file.close()

        new_matrix = np.zeros((len(matrix) + 2, len(matrix[0])))

        for i in range(len(matrix)):
            new_matrix[i, :] = np.array(matrix[i])

        evaluations = self.__evaluator.evaluate_compare(
            ['1'*len(self.__best), self.__best], new_matrix)

        return evaluations

    def __plot_evolution(self, fold):

        archive_bank = self.__dict_persist.load(f'Fold{fold}/archive_bank')
        population_bank = self.__dict_persist.load(
            f'Fold{fold}/population_bank')

        for metric in self.__evaluator.metrics:
            maximum, mean, minimum, std, var = [], [], [], [], []

            for n_gen, generation in archive_bank.items():
                if len(generation) == 0:
                    continue
                maximum.append(
                    np.max([np.mean(population_bank[ind][metric]) for ind in generation]))
                mean.append(np.mean([np.mean(population_bank[ind][metric])
                                     for ind in generation]))
                minimum.append(
                    np.min([np.mean(population_bank[ind][metric]) for ind in generation]))
                std.append(np.std([np.std(population_bank[ind][metric])
                                   for ind in generation]))
                var.append(np.var([np.mean(population_bank[ind][metric])
                                   for ind in generation]))

            gens = range(0, len(maximum))

            sns.set()
            sns.set_style('darkgrid')
            sns.set_context('talk')
            sns.set_palette('deep')

            fig = plt.figure(figsize=(15, 10))
            ax = fig.add_subplot()

            ax.plot(gens, maximum, label='Max')
            ax.plot(gens, mean, label='Mean')
            ax.plot(gens, minimum, label='Minimum')

            ax.grid(True)
            ax.legend(loc='upper left')
            ax.set_xlabel('Generations')
            ax.set_ylabel(metric.upper())
            ax.set_title(f'{metric.upper()} by generation')

            plt.savefig(self.__dict_persist.path /
                        f'Fold{fold}/{metric}basic.png')

            ax.cla()

            ax.plot(gens, std, label='std')

            ax.grid(True)
            ax.legend(loc='upper left')
            ax.set_xlabel('Generations')
            ax.set_ylabel(f'{metric.upper()}_std')
            ax.set_title(f'{metric.upper()} std by generation')

            plt.savefig(self.__dict_persist.path /
                        f'Fold{fold}/{metric}std.png')

            ax.cla()

            ax.plot(gens, var, label='var')

            ax.grid(True)
            ax.legend(loc='upper left')
            ax.set_xlabel(f'Generations')
            ax.set_ylabel(f'{metric.upper()}_var')
            ax.set_title(f'{metric.upper()} var by generation')

            plt.savefig(self.__dict_persist.path /
                        f'Fold{fold}/{metric}var.png')

    def report(self, folds):

        comparisons = []

        for fold in folds:
            test = DatasetHandler(
                f'data/dataset/{self.__dataset_name}/Fold{fold}/Norm.test.txt')
            test.load()
            self.__evaluator = Evaluator(self.__objectives, self.__weights,
                                         self.__dataset_name, test.X, test.y, test.query_id)
            comparisons.append(self.__process_fold(fold))
            self.__plot_evolution(fold)
            del self.__evaluator

    def final_report(self):

        folds = []

        for file_name in self.__dict_persist.path.rglob('fold_comparison.json'):
            with open(file_name, 'r') as file:
                folds.append(json.load(file))
                file.close()

        ndcg = {'initial': [], 'final': []}
        georisk = {'initial': [], 'final': []}
        n_trees = {'initial': [], 'final': []}

        for fold in folds:
            for ind in ['initial', 'final']:
                ndcg[ind].append(fold[ind]['ndcg'])
                georisk[ind].append(fold[ind]['georisk'])
                n_trees[ind].append(fold[ind]['n_trees'])

        for ind in ['initial', 'final']:
            ndcg[ind] = np.array(ndcg[ind]).flatten()

        comparison = {}

        comparison['ndcg_equal'] = compare(ndcg['initial'], ndcg['final'])

        # comparison['georisk_equal'] = compare(
        #    georisk['initial'], georisk['final'])

        ndcg['initial'] = np.mean(ndcg['initial'])
        ndcg['final'] = np.mean(ndcg['final'])
        georisk['initial'] = np.mean(georisk['initial'])
        georisk['final'] = np.mean(georisk['final'])
        n_trees['initial'] = np.mean(n_trees['initial'])
        n_trees['final'] = np.mean(n_trees['final'])

        comparison['ndcg'] = ndcg
        comparison['georisk'] = georisk
        comparison['n_trees'] = n_trees

        self.__dict_persist.save(comparison, 'final_report')


def compare(x_vet, y_vet, min_p_value=0.05):
    # USANDO o R para calcular t-test
    rd1 = (robjects.FloatVector(x_vet))
    rd2 = (robjects.FloatVector(y_vet))
    rvtest = robjects.r['t.test']
    pvalue = rvtest(rd1, rd2, paired=True)[2][0]

    return pvalue < min_p_value
