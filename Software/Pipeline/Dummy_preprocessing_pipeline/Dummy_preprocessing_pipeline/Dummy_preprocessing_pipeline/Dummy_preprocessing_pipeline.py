import numpy as np

# pipe line stuff 
from sklearn.pipeline import Pipeline
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import StandardScaler

# defining transformer for emg data
# elevates each value in the input matrix to the power of two
# expects a numpy array, or throws exception
class DummyTransformer(BaseEstimator, TransformerMixin):

    def fit(self, X, y=None):
        return self

    def transform(self, X, y=None):

        # raising every value to the power of 2
        for x in range(X.shape[0]):
            for y in range(X.shape[1]):
                X[x][y] = X[x][y] * X[x][y]  

        return X



# defining processing pipe line
def get_Dummy_Pipeline(): 
    return Pipeline([
        ('dummyTransformer', DummyTransformer()),
        ('std_scaler', StandardScaler())
    ])

