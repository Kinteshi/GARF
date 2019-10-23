import l2rCodesSerial
import numpy as np
from sklearn import model_selection


def getEval(individuo, model, NUM_GENES, X_test, y_test, query_id_train, ENSEMBLE, NTREES, SEED,
            DATASET, METRIC, NUM_FOLD, ALGORITHM):
    evaluation = []
    ndcg, queries = getPrecisionAndQueries(individuo, model, NUM_GENES, X_test, y_test, query_id_train,
                                           ENSEMBLE, NTREES, SEED, DATASET,
                                           METRIC)

    evaluation.append(queries)
    # evaluation.append(ndcg)
    evaluation.append(getRisk(queries, DATASET, NUM_FOLD, ALGORITHM))
    evaluation.append(getTotalFeature(individuo))
    evaluation.append(getTRisk(queries, DATASET, NUM_FOLD, ALGORITHM))

    return evaluation


def getWeights(params):
    weights = []
    if 'precision' in params:
        weights.append(1)
    if 'risk' in params:
        weights.append(1)
    if 'feature' in params:
        weights.append(-1)
    if 'trisk' in params:
        weights.append(-1)

    return weights


def getPrecision(individuo, NUM_GENES, X_train, y_train, X_test, y_test, query_id_train, ENSEMBLE, NTREES, SEED,
                 DATASET,
                 METRIC):
    ndcg, queries = getPrecisionAndQueries(individuo, NUM_GENES, X_train, y_train, X_test, y_test, query_id_train,
                                           ENSEMBLE, NTREES, SEED, DATASET,
                                           METRIC)
    return ndcg


def getTotalFeature(individuo):
    return sum([int(i) for i in individuo])


# PRECISA SER CORRIGIDA SE HOUVER MAIS DE UM BASEINE
def getRisk(queries, DATASET, NUM_FOLD, ALGORITHM):
    base = []

    arq = open(r'./baselines/' + DATASET + '/Fold' +
               NUM_FOLD + '/' + ALGORITHM + '.txt')
    for line in arq:
        base.append([float(line.split()[0])])
    basey = base.copy()

    for k in range(len(basey)):
        basey[k].append(queries[k])

    r = (l2rCodesSerial.getGeoRisk(np.array(basey), 5))[1]
    return r


def getTRisk(queries, DATASET, NUM_FOLD, ALGORITHM):
    base = []

    arq = open(r'./baselines/' + DATASET + '/Fold' +
               NUM_FOLD + '/' + ALGORITHM + '.txt')
    for line in arq:
        base.append(float(line.split()[0]))

    r, vetorRisk = (l2rCodesSerial.getTRisk(queries, base, 5))
    return vetorRisk


def getPrecisionAndQueries(individuo, model, NUM_GENES, X_vali, y_vali, query_id_train, ENSEMBLE, NTREES,
                           SEED, DATASET,
                           METRIC):

    list_mask = list(individuo)

    queriesList = l2rCodesSerial.getQueries(query_id_train)
    resScore = model.predict(X_vali, list_mask)

    ndcg, queries = l2rCodesSerial.getEvaluation(
        resScore, query_id_train, y_vali, DATASET, METRIC, "test")
    return ndcg, queries