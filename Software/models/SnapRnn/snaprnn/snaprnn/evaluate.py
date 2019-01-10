import json
import math
import numpy as np
import tensorflow as tf

from multiprocessing import Process
from time import sleep

# importing system utilities
import os.path
from os import listdir

# importing myo communication utilities
from myo_read_multi.pipeline_buffer import launch_myo_comm, reset_pipeline_buff_flags, write_model_prediction, wait_for_start_time

# importing data processing/piepline utilities
from Calibration_Pipeline.Calibration_Pipeline import get_calibration_Pipeline


# function to add zero padding to a sequence
# inputs : 
#   target_seq_length : final length of the sequence we want
#   data : data of shape (n_sequence, n_inputs)
# outputs : zero padded data of shape (seq_length, n_inputs) 
def zero_padd_sequence(data, target_seq_length):
    
    n_current_sequences = data.shape[0]
    n_inputs = data.shape[1]

    # adding the necessary padding
    for i in range(target_seq_length - n_current_sequences): 
        data = np.vstack([data, np.zeros(n_inputs)])

    return data
    

# fetches the latest graph definition from specified directory
# inputs : 
#   model_dir : directory to search in (should contain model information)
# returns : path to graph definition (.meta file)
def fetch_latest_graph(model_dir):
    
    cp_files = []
    for f in listdir(model_dir):
        if os.path.isfile(os.path.join(model_dir, f)) and f.endswith('.meta'):
            cp_files.append(f)
    modif_dates = [os.path.getmtime(os.path.join(model_dir, f)) for f in cp_files]
    
    # getting last modified cp file
    try : cp_i = modif_dates.index(max(modif_dates))
    except : return ""

    return os.path.join(model_dir, cp_files[cp_i])


# restores the specfied model and returns it in a session
# .meta file = graph definition (sould only be one)
# inputs : 
    # model_dir : path to the model is defined (folder contains .meta file)
    # cp_file_in : path to the model meta file (optional)
# returns : the session where the trained model is defined 
def restore_tf_session(model_dir, cp_file_in=None):

    cp_file = ""

    # if specific check-point file is specified
    if cp_file_in is not None : cp_file = cp_file_in

    # no cp file specified
    else : 
        cp_file = tf.train.latest_checkpoint(model_dir)
        if cp_file is None : 
            raise(ValueError("No check point file was found in specified folder"))  

    # recreating the saved graph 
    meta_file = fetch_latest_graph(model_dir)
    saver = tf.train.import_meta_graph(meta_file)

    # restoring the saved model from the proper cp file
    session = tf.Session()
    saver.restore(session, cp_file)

    return session, saver


# Runs an RNN which pulls its input data from a redis server
# The model is ment to be ran along side other rnn models
# The model uses the calibation pipeline to preprocess input data
# Inputs :
#   r_server : redis server connection instance
#   client_index : creation index for the model
#   calibration_file : path to json file containing calibration information
#   model_dir : path to the directory containing the model files
#   check_delay : time between data availability checks (in seconds)
def eval_single_model(r_server, client_index, calibration_file, model_dir, check_delay=0.1):

    # defining the calibration pipeline
    cal_pipeline = get_calibration_Pipeline(calibration_file)

    # fetching the session where the model was defined
    restored_sess, _ = restore_tf_session(model_dir)
    
    # using the restored model session
    with restored_sess as session:

        # fetching the necessary operations and place holders for training
        X = tf.get_collection('X')[0]
        seq_length = tf.get_collection('seq_length')[0]
        training_model = tf.get_collection('training_model')[0]
        predictions_op = tf.get_collection('class_ids')[0]
        prob_op = tf.get_collection('probabilities')[0]

        # pulling model input dimensions
        n_inputs = int(X.shape[2])
        n_steps = int(X.shape[1])

        # defining input container for the model
        movement_data = np.zeros((0, n_inputs))
        movement_len = 0

        # defining activation flag
        model_activated = False

        try :

            # while the incoming buffer is maintained
            while(r_server.get("buffer_maintained") == "1"):
                
                # once the model is activated, reduce resource consumption
                if model_activated : sleep(check_delay)

                # pipeline buffer is ready to be read
                if(r_server.lindex("client_read_data", client_index) == "1"):

                    # check if model activation time is reached
                    if not model_activated :
                        model_activated = wait_for_start_time(r_server, client_index)

                    if model_activated:

                        # adding to the movement length
                        movement_len += 1

                        # adding buffer content to the movement data
                        pipeline_buff = np.array(json.loads(r_server.get("pipeline_buff")))
                        pipeline_buff = cal_pipeline.fit_transform(pipeline_buff)
                        movement_data = np.vstack([movement_data, 
                                        np.reshape(pipeline_buff, n_inputs)])
                        
                        # marking buffer as read (by this client)
                        reset_pipeline_buff_flags(r_server, client_index)

                        # formatting the movement data
                        formatted_mov = zero_padd_sequence(movement_data, n_steps)
                        formatted_mov = np.expand_dims(formatted_mov, axis=0)

                        # formatting the curr movement length
                        formatted_seq_len = np.array([movement_len])

                        # evaluating the model with the movement data
                        predictions = session.run(predictions_op, 
                                    feed_dict={training_model:False, seq_length:formatted_seq_len, X:formatted_mov})
                        probabilities = session.run(prob_op, 
                                    feed_dict={training_model:False, seq_length:formatted_seq_len, X:formatted_mov})

                        # storing the prediction
                        curr_step_pred = str(predictions[0][movement_len-1])
                        pred_probs = list(probabilities[0][movement_len-1])
                        write_model_prediction(r_server, client_index, curr_step_pred, pred_probs, str(movement_len))

                        # managing the size of the movement
                        if movement_len >= n_steps:
                            movement_data = np.zeros((0, n_inputs))
                            movement_len = 0
        
        except:
            # unsetting continuation flag for acquisition process
            r_server.set("incoming_data", "0")
            print("Model with index : ", client_index, " has failed.")


# Monitors the predictions of all parallel models via the redis server
# Defines the selected ouput for the whole system
# This function is ment to be ran as a seperate process
# Inputs : 
#   r_server : redis server connection instance
#   n_outputs : number of outputs for the model/client (model is a classifier)
#   n_models : 
#      - number of rnns to activate simultaneously
#      - should match the number of steps in a single model
#   check_delay : time between data availability checks (in seconds)
def eval_model_predictions(r_server, n_outputs, n_models, check_delay=0.1):

    last_data_count = 0
    prev_pred_probs = None

    while(True):  

        # giving time for new data to arrive
        sleep(check_delay)
        
        # waiting for all models to produce predictions
        data_count = int(r_server.get("data_count"))
        if(last_data_count < data_count and data_count > (n_models+1)):

            # pulling prediction data for all models
            predictions = r_server.lrange("model_predictions", 0, n_models-1)
            pred_steps = r_server.lrange("prediction_step", 0, n_models-1)
            
            # pulling the prediction probabilities for all models
            pred_probs = []
            for model_i in range(n_models):
                list_name = "output_probs_" + str(model_i)
                pred_probs.append(r_server.lrange(list_name, 0, n_outputs-1))
        
            if(prev_pred_probs is not None):

                # foreach model compute a score for the current prediction
                prediction_scores = []
                for model_i in range(n_models):

                    # getting prediction data for current model
                    curr_step = int(pred_steps[model_i]) 
                    curr_pred = int(predictions[model_i])
                    curr_probs = pred_probs[model_i]

                    # getting previous probabilities for current model
                    curr_prev_probs = prev_pred_probs[model_i]
                    
                    # getting previous probability for the currently predicted class
                    # at step 0, all classes have the same output probability (1/outputs)
                    if curr_step == 1 : curr_prev_prob = 1/n_outputs
                    else : curr_prev_prob = float(curr_prev_probs[curr_pred])

                    # calculating the score for the current model
                    prob_diff = float(curr_probs[curr_pred]) - curr_prev_prob
                    prediction_scores.append(model_prediction_score(prob_diff, curr_step))

                # fetching the winning prediction
                max_pred_score = max(prediction_scores)
                selected_model_i = prediction_scores.index(max_pred_score)
                selected_label = predictions[selected_model_i]
                
                # ouput selection logic goes here ... (ex)
                print("Selected output : ", selected_label)

            # keeping track of previous prediction probabilities
            prev_pred_probs = pred_probs
            last_data_count = data_count


# Produces score for provided prediction info, score is intended for comparison
# Inputs :
#   prob_diff : the difference in probability, for the last two steps, of the selected class
#   step : the step at which the provided prediction was made    
def model_prediction_score(prob_diff, step): 
    
    # no points for a probability drop
    if prob_diff < 0 : return 0

    # computing score for provided prediction
    score = prob_diff * (-0.028*step**2+0.28*step+0.3)
    if score > 0 : return score
    else : return 0


# Launches multiple RNN models in parallel
# The models get their inputs from a redis server and write to a redis server
# Inputs :
#   pipeline_buffer_size : number of points per chanel for 1 step
#   n_outputs : number of outputs for the model/client (model is a classifier)
#   n_models : 
#      - number of rnns to activate simultaneously
#      - should match the number of steps in a single model
#   calibration_file : path to json file containing calibration information
#   model_dir : path to the directory containing the model files
#   check_delay : time between data availability checks (in seconds)
def launch_model_instances(pipeline_buffer_size, n_outputs, n_models, calibration_file, model_dir, check_delay=0.1):

    # starting the buffer maintenance process
    r_server, buffer_maintenance_p = launch_myo_comm(pipeline_buffer_size, n_outputs=n_outputs, 
                                                     n_clients=n_models, check_delay=check_delay)

    # lauching "n_models" model in "n_models" different processes
    model_processes = []
    for i in range(n_models):
        p = Process(target=eval_single_model, args=(r_server, i, calibration_file, model_dir, check_delay))
        p.start()
        model_processes.append(p)

    # waiting for the models to buid
    model_build_time = n_models//3
    if model_build_time < 5 : model_build_time = 3
    sleep(model_build_time)

    # lauching the process for prediction evaluation
    pred_eval_p = Process(target=eval_model_predictions, args=(r_server, n_outputs, n_models, check_delay))
    pred_eval_p.start()

    # waiting for confirmation that myo is connected (data  is received)
    buffer_maintenance_p.start()
    while(r_server.get("buffer_ready") != "1"): sleep(0.05)

    # waiting for the model processes to finish
    for p in model_processes:
        p.join()
    pred_eval_p.join()
    buffer_maintenance_p.join()