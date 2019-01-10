# importing model utilities
from snaprnn.evaluate import launch_model_instances

if __name__ == "__main__":

    model_dir = "Model/"
    calibration_file = "Example_calibration_file.json"
    n_outputs = 7
    n_models = 20
    pipeline_buffer_size = 50

    launch_model_instances(pipeline_buffer_size, n_outputs, n_models, calibration_file, model_dir)