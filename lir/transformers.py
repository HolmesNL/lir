import numpy as np
import scipy
import sklearn


class VectorNormalizer(sklearn.base.TransformerMixin):
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return (X.T / np.sum(X, axis=1)).T


class GaussianCdfTransformer(sklearn.base.TransformerMixin):
    """
    Takes an array of samples and returns the element-wise order of the sample using a cumulative density function.

    Steps for each feature:
    1. fit a density function from the mean and standard deviation for the whole population, assuming a gaussian distribution;
    2. delete the feature if there is too little data to calculate a standard deviation greater than 0;
    3. replace individual values by the value returned by the cumulative density function

    For example, if a feature value is 10, and this is exactly the mean of this feature in the population, the feature value will be replaced by .5.
    """

    def fit(self, X, y=None):
        self._mean = np.mean(X, axis=0)
        self._std = np.std(X, axis=0)

        self._valid_features = self._std > 0
        self._mean = self._mean[self._valid_features]
        self._std = self._std[self._valid_features]

        return self

    def transform(self, X):
        assert len(X.shape) == 2
        X = X[:,self._valid_features]
        return scipy.stats.norm.cdf(X, self._mean, self._std)


class AbsDiffTransformer(sklearn.base.TransformerMixin):
    """
    Takes an array of sample pairs and returns the element-wise absolute difference.

    Expects:
        - X is of shape (n,f,2) with n=number of pairs; f=number of features; 2=number of samples per pair;
    Returns:
        - X has shape (n, f)
    """
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        assert len(X.shape) == 3
        assert X.shape[2] == 2

        return np.abs(X[:,:,0] - X[:,:,1])


class InstancePairing(sklearn.base.TransformerMixin):
    def __init__(self, same_source_limit=None, different_source_limit=None):
        """
        Parameters:
            - same_source_limit (int or None): the maximum number of same source pairs (None = no limit)
            - different_source_limit (int or None or 'balanced'): the maximum number of different source pairs (None = no limit; 'balanced' = number of same source pairs)
        """
        self._ss_limit = same_source_limit
        self._ds_limit = different_source_limit

    def fit(self, X):
        return self

    def transform(self, X, y):
        """
        Expects:
            - X is of shape (n,f) with n=number of samples; f=number of features
            - y is of shape (n,)
        Returns:
            - X, y; X has shape (m,f,2); y has shape (m,); with m=number of pairs
        Attributes:
            - self.pairing: an array of shape (m,2) with indexes of X input array which contribute to the pairs
        """
        pairing = np.array(np.meshgrid(np.arange(X.shape[0]), np.arange(X.shape[0]))).T.reshape(-1, 2)  # generate all possible pairs
        same_source = y[pairing[:, 0]] == y[pairing[:, 1]]

        rows_same = np.where((pairing[:, 0] < pairing[:, 1]) & same_source)[0]  # pairs with different id and same source
        if self._ss_limit is not None and rows_same.size > self._ss_limit:
            rows_same = np.random.choice(rows_same, self._ss_limit, replace=False)

        rows_diff = np.where((pairing[:, 0] < pairing[:, 1]) & ~same_source)[0]  # pairs with different id and different source
        ds_limit = rows_diff.size if self._ds_limit is None else rows_same.size if self._ds_limit == 'balanced' else self._ds_limit
        if rows_diff.size > ds_limit:
            rows_diff = np.random.choice(rows_diff, ds_limit, replace=False)

        pairing = np.concatenate([pairing[rows_same,:], pairing[rows_diff,:]])
        self.pairing = pairing

        X = np.stack([X[pairing[:, 0]], X[pairing[:, 1]]], axis=2)  # pair instances by adding another dimension
        y = np.concatenate([np.ones(rows_same.size), np.zeros(rows_diff.size)])  # apply the new labels: 1=same_source versus 0=different_source

        return X, y
