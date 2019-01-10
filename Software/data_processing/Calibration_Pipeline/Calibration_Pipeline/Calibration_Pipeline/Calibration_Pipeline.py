import numpy as np
import json

# pipeline utilities 
from sklearn.pipeline import Pipeline
from sklearn.base import BaseEstimator, TransformerMixin


# Defining transformer for emg data
# Normalizes the data to a value in interval [-1, 1]
# The normalization is done sing the max value measured during calibration
class CalibrationTransformer(BaseEstimator, TransformerMixin):

    def __init__(self, cal_file_path):
        
        # extracting data from the calibration file
        try:
            cal_file = open(cal_file_path, 'r').read()
        except: raise(ValueError("Failed to open specified calibration file."))
        cal_data = json.loads(cal_file)
        self.rest_mean = cal_data["Rest_value_mean"]
        self.max_mean = cal_data["Max_effort_mean"]

        # defining the normalization operation
        def normalize_funct(x): 
            x = (x + self.rest_mean*-1)/(self.max_mean + self.rest_mean*-1)
            if(x > 1): x = 1
            elif(x < -1): x = -1
            return x
        
        # vectorizing the main operation
        self.normalize_vect = np.vectorize(normalize_funct)


    def fit(self, X, y=None):
        return self


    def transform(self, X, y=None):
        return self.normalize_vect(X)



# defining processing pipe line
def get_calibration_Pipeline(cal_file_path): 
    return Pipeline([
        ('calibration_transformer', CalibrationTransformer(cal_file_path))
    ])