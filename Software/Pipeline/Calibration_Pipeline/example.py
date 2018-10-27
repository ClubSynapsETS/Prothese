import numpy as np
from Calibration_Pipeline.Calibration_Pipeline import get_calibration_Pipeline

calibration_file = "Example_calibration_file.json"

# defining testnp array7
input_list = [[21,3,4,54,6,78,8,9],[-2,3,4,-55,6,7,8,9],\
             [2,3,14,5,6,73,8,9],[2,-3,4,-5,6,-57,8,9]]
input_data = np.array(input_list)

# getting a pipeline instance
norm_pipeline = get_calibration_Pipeline(calibration_file)

# feeding the data through the pipeline
print("Before pipeline feed : ", input_data)
input_data = norm_pipeline.fit_transform(input_data)
print("After pipeline feed : ", input_data)
