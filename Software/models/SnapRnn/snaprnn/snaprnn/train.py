import json
import sklearn
import numpy as np

import tensorflow as tf

import matplotlib.pyplot as plt
from matplotlib.pyplot import savefig

import math
import itertools
from datetime import datetime 

# importting os utilities
from os import listdir
from os.path import isfile, join

# importing shuffling utilities
from random import shuffle

# importing evaluation utilities
from . import evaluate

# various sklearn tools 
from sklearn.metrics import confusion_matrix

# importing model pipeline
from Calibration_Pipeline.Calibration_Pipeline import get_calibration_Pipeline


class InvalidPipelineError(Exception):
    ''' The pipeline held by ModelBatchGenerator has to inherit \
        from sklearn.pipeline.Pipeline'''

    def __init__(self, msg=None):

        if msg is None:
            msg = "ModelBatchGenerator.batch_pipeline has to \
                  inherit from sklearn.pipeline.Pipeline"

        super(InvalidPipelineError, self).__init__(msg)


class ModelBatchGenerator():

    ''' 
    ModelBatchGenerator 

    - If the traning file has more than (n_inputs * n_steps) in it, the exceeding
      part will be ingnored and will not be part of the output data 

    - The data files have to follow the naming convention : "(movement name)_(number)_(number).json" 
    
    - starting_step : 
        Index of the step where the back propagation starts. 
        Number of labels per sequence = n_steps - starting_step
    '''

    # movement_info_f : path to the movement info json file   
    # batch_size : number of labeled movements to include in a batch
    def __init__(self, movement_info_f, batch_size, n_inputs, n_steps, n_emgs=8, starting_step=0):
        
        # loading the training file names
        self.all_files  = get_training_files(movement_info_f) 
        self.data_len = len(self.all_files)
        
        # loading the movement lookup dir
        self.movement_labels = get_movement_labels(movement_info_f)
        self.num_classes = len(self.movement_labels.keys())       
        
        # setting the trainng batch size
        if not batch_size == "all": self.batch_size = batch_size
        else : self.batch_size = self.data_len
        
        # data for output shape
        self.n_inputs = n_inputs
        self.n_steps = n_steps
        self.n_emgs = n_emgs
        self.starting_step = starting_step

        # data management vars
        self.batch_index = 0
        self.data_exhausted = False 
        
        # defining pipeline for batch data pre-processing
        self.batch_pipeline = None

        # defining batch data
        self.batch_data_cached = False
        self.data_seq_container = None
        self.label_container = None
        self.seq_len_container = None


    # assign pipeline to be appliqed to generated batches
    # specified pipeline has to enherit from "TransformerMixin"
    def set_batch_pipeline(self, pipeline):
        
        if not isinstance(pipeline, sklearn.pipeline.Pipeline):
            raise InvalidPipelineError()

        else : self.batch_pipeline = pipeline
        
    
    # get the amount of batches in the training data
    def count_batches(self):
        return math.ceil(self.data_len/self.batch_size)


    # checking if all batch data was served
    def is_exhausted(self):
        return self.data_exhausted


    # resets the data exhausted flag
    def reset_data_exhausted(self):
        self.data_exhausted = False


    # amt of remaining files to be batched
    def ct_remaining_files(self):
        return self.data_len - self.batch_index


    # amt of data to be collected for 1 emg chanel per step
    def emg_chan_p_step(self):
        try : 
            return self.n_inputs / self.n_emgs
        except ZeroDivisionError:
            raise(ValueError("\"n_emgs\" has to be greater than 0."))


    # apply the pipeline transform to the provided data
    def pipeline_transform(self, batch_data):
        return self.batch_pipeline.transform(batch_data)


    # extracs movement name (following naming convention)
    # returns label for extracted movement name 
    def get_label_for_file(self, file_name):
        
        # getting index of first digit
        digit_i = 0
        for i, char in enumerate(file_name):
            if(char.isdigit()):
                digit_i = i
                break
        
        # getting index of last slash
        slash_i = 0
        while(True):
            index = file_name.find("/", slash_i+1)
            if(index != -1): slash_i  = index
            else: break
        
        movement_name = file_name[slash_i+1 : digit_i-1]
        return self.movement_labels[movement_name]  


    # returns : Names of data files for the current batch
    # resets the de batch index when all data is pulled
    def get_batch_file_names(self):

        end_i = 0
        start_i = self.batch_index 
        n_remaining_files = self.ct_remaining_files()
        
        if(n_remaining_files < self.batch_size):
            end_i = self.batch_index + n_remaining_files
            self.batch_index = 0
            self.data_exhausted = True
        
        else : 
            end_i = self.batch_index + self.batch_size
            self.batch_index = end_i
        
        if self.batch_index == self.data_len: 
            self.batch_index = 0
        
        return self.all_files[start_i : end_i]


    # file_name : Specified data file name
    # returns the data in the specified file with shape (n_steps, n_inputs)
    def build_sequence_data(self, file_name):

        # loading data from file with shape : (n_emgs, n_acquisitions)
        json_data = json.loads(open(file_name, 'r').read())
        emg_data = np.swapaxes(np.array(json_data["emg"]["data"], dtype=np.dtype(np.int32)), 0,1)

        # amt of data to be collected for 1 emg chanel per step
        emg_chan_p_step = int(self.emg_chan_p_step())

        # defining the number of steps to be filled with data
        seq_limit = emg_data.shape[1] // emg_chan_p_step
        if (seq_limit > self.n_steps) : seq_limit = self.n_steps

        start_i = 0
        sequence_data = np.zeros((0, self.n_inputs), dtype=np.dtype(np.int32))
        for i in range(seq_limit):

            # stacking the data in slices of shape (1, n_emgs * emg_chan_p_step = n_inputs)
            current_step_data = emg_data[ : , start_i : start_i + emg_chan_p_step].flatten()                
            sequence_data = np.vstack([sequence_data, current_step_data])

            start_i += emg_chan_p_step
        
        # zero padd the sequence if it is to short
        if(seq_limit < self.n_steps):
            sequence_data = evaluate.zero_padd_sequence(sequence_data, self.n_steps)

        # applying pipeline transform, if one is defined
        if self.batch_pipeline is not None: 
            sequence_data = self.batch_pipeline.transform(sequence_data)

        return sequence_data


    # fetches the data necessary for the net training batch
        # data_seq_container : shape = (batch_size, n_steps, n_inputs)
        # label_container    : shape = (batch_size * n_steps)
        # seq_len_container  : shape = (batch_size)
    def next_batch(self):

        # if batch data was cached, return it directly
        if self.batch_data_cached: return self.batch_data()

        # getting the file names for the current batch
        batch_file_names = self.get_batch_file_names()

        # going through all training files for the batch
        data_seq_container = []
        label_container = []
        seq_len_container = []

        for file_name in batch_file_names:        

            # building sequence from movement data and stacking it
            data_seq_container.append(self.build_sequence_data(file_name))
    
            # building the labels for the sequence
            label_array = np.empty((self.n_steps - self.starting_step), dtype=np.dtype(np.int32))
            label_array.fill(self.get_label_for_file(file_name))
            label_container.append(label_array)

            # stacking the sequence length for the sequence
            seq_len_container.append(self.n_steps)

        # setting values for batch data
        self.data_seq_container = np.array(data_seq_container)
        self.label_container = np.array(label_container).flatten()
        self.seq_len_container = np.array(seq_len_container)

        # caching the batch data if we loaded all the data
        if not self.batch_data_cached and self.batch_size == self.data_len:
            self.batch_data_cached = True

        return self.batch_data()

        
    # Returns : the batch data fetched from the training files
    def batch_data(self):
        return self.data_seq_container, self.label_container, self.seq_len_container



# movement_info_f : .json file name specifying the training data location
# returns shuffled list of all training json files
def get_training_files(movement_info_f):

    # extracting data from the calibration file
    try:
        json_file = open(movement_info_f, 'r').read()
    except: raise(ValueError("Failed to open specified movement info .js file"))

    # getting list of all directories containing traning data
    json_data = json.loads(json_file)["movement_info"]
    training_dirs = [movement_info["directory_path"] for movement_info in json_data]

    # building list of training file names
    all_training_files = []
    for curr_dir in training_dirs: 
        dir_training_files = [curr_dir + "/" + file for file in get_json_file_names(curr_dir)]
        all_training_files += dir_training_files

    # shuffling the list of names
    shuffle(all_training_files)

    return all_training_files


# target_path : directory path to navigate to and explore
# returns all json file names in specified directory
def get_json_file_names(target_path):
    return [f for f in listdir(target_path) 
            if isfile(join(target_path, f)) and f.endswith('.json')]


# movement_info_f : .json file name specifying the movement data location
# returns : dictionary containing (key : movement name) -> (val : label) 
def get_movement_labels(movement_info_f):

    try:
        movement_info = json.loads(open(movement_info_f, 'r').read())["movement_info"]
    except : raise(ValueError("Failed to open specified movement info .js file"))

    movement_labels = {}
    for mov in movement_info:
        movement_labels[mov["name"]] = mov["label"]

    return movement_labels


# outputs .txt file with prediction error count for RNN
# inputs : 
    # predictions : output predictions of the RNN           (shape = [batch_size , n_steps])
    # labels : labels for the predictions in the batch      (shape = [batch_size * n_steps])
    # starting_step : index of the first RNN output to be considered (index starts at zero)
    # file_name : name of the log .txt file
def log_rnn_confusion(predictions, labels, starting_step=0, file_name=None, mv_info_f=None):

    # defining the output file name
    if file_name is not None : file_name = file_name
    else: 
        now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        file_name = "confusion-{}.png".format(now)

    # getting the predictions for wanted steps
    predictions = predictions[ : , starting_step : predictions.shape[1]].flatten()

    # creating a confusion matrix
    cnf_matrix = sklearn.metrics.confusion_matrix(labels, predictions)
    plt.imshow(cnf_matrix, interpolation='nearest', cmap=plt.cm.Blues)

    # defining the titles
    plt.title("Confusion Matrix")
    plt.ylabel('True label')
    plt.xlabel('Predicted label')
    plt.tight_layout()
    plt.colorbar()

    # putting the class names along the axis
    classes = []
    if mv_info_f is not None:
        try: 
            classes_dict = get_movement_labels(mv_info_f)
            classes = sorted(classes_dict, key=classes_dict.get)
        except : pass
    tick_marks = np.arange(len(classes))
    plt.xticks(tick_marks, classes, rotation=90)
    plt.yticks(tick_marks, classes)

    # placing a count on every matrix slot
    thresh = cnf_matrix.max() / 2.
    for i, j in itertools.product(range(cnf_matrix.shape[0]), range(cnf_matrix.shape[1])):
        plt.text(j, i, format(cnf_matrix[i, j], 'd'),
                 horizontalalignment="center",
                 color="white" if cnf_matrix[i, j] > thresh else "black")

    # saving the confusion matrix
    savefig(file_name, bbox_inches='tight')


# generates n_sets of random parameter values for parameter searching
# inputs :
#   anchor_values : distionary object to define the parameters spaces 
#       - keys : parameter name 
#       - value : center value of the parameter space
#       * parameter space : [anchor - variation*anchor, anchor + anchor*variation]
#   n_sets : number of config sets to produce
#   variation : defines how much the parameter space stretches out
#   static_params : (dicionary) static parameters to be added to all the output config dictonaries
# returns : list of configuration dictionaries for the model building function
def generate_random_params(anchor_values, n_sets, variation=0.5, static_params=None):

    # generating the random values foreach param
    parameter_vals = {}
    for key, value in anchor_values.items():
        if key == "learning_rate":
            exponents = list(np.random.random_integers(-4, -1, n_sets))
            parameter_vals[key] = [10**int(expo) for expo in exponents]
        elif key == "keep_prob":
            parameter_vals[key] = list(np.random.uniform(0.4, 0.70, n_sets))
        else : 
            max_val = value + math.fabs(variation) * value 
            min_val = value - math.fabs(variation) * value
            parameter_vals[key] = list(np.random.random_integers(min_val , max_val, n_sets))
            parameter_vals[key] = [int(val) for val in parameter_vals[key]]

    # creating the list of config dictionaries
    config_dicts = []
    for _ in range(n_sets):
        config = {}
        # adding randomly generated parameters 
        for param_name in anchor_values.keys():
            config[param_name] = parameter_vals[param_name].pop()
        # adding the static parameters
        if static_params is not None:
            config.update(static_params)
        # config dict is complete
        config_dicts.append(config)

    return config_dicts


# details the provided model configurations along with their performance
# creates a log file in the current directory
# inputs : 
#   model_perf : "model performances", list of configurations dictionaries with an appended "max_accuracy" entry
#   log_name : name for the output log .txt file
def log_config_performances(model_perfs, log_name=None):

    # grabbing info
    current_time_str = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    n_configurations = len(model_perfs)

    # defining de log file name
    f_name = None
    if log_name is not None : f_name = log_name
    else : f_name = "search_log_" + current_time_str + ".txt"  

    # sorting the configurations by performance
    model_perfs.sort(key=lambda x: x["max_accuracy"], reverse=True)

    # opening file + header
    f = open(f_name, "w")
    f.write("Total of : " + str(n_configurations) + " evaluated during the parameter search.\n")
    f.write("Log date : " + current_time_str + ".\n\n")
    
    # first place config
    f.write("Best configuration : \n\n")
    f.write(config_performance_to_string(model_perfs[0]))
    f.write("\nOther Configurations : \n\n")
    
    # remaining configs
    config_i = 1
    for i in range(1, len(model_perfs)):
        f.write("Config #" + str(config_i) + " : \n\n")
        f.write(config_performance_to_string(model_perfs[i]))
        config_i += 1


# details a a model configuration and its performance
# inputs : 
#   model_config : configuration dictionary containing the added performance entries : 
#       - max_accuracy
#       - epoch_at_max
# returns string to be written in global search log file
def config_performance_to_string(model_config):

    log_str = "Performance : \n"
    log_str += "max_accuracy : " + str(model_config["max_accuracy"]) + "\n"
    log_str += "epoch_at_max : " + str(model_config["epoch_at_max"]) + "\n"
    log_str += "Configuration : \n"
    for key, value in model_config.items():
        if not (key == "max_accuracy" or key == "epoch_at_max"):
            log_str += key + " : " + str(value) + "\n"
    log_str += "\n"

    return log_str