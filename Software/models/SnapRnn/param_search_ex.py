import numpy as np
import tensorflow as tf

import os.path
from datetime import datetime

# importing model utilities
from snaprnn.train import ModelBatchGenerator, generate_random_params, log_config_performances
from snaprnn.evaluate import restore_tf_session
from snaprnn.model import generate_blank_model

# importing data processing/piepline utilities
from Calibration_Pipeline.Calibration_Pipeline import get_calibration_Pipeline

# defining model directory
model_dir = "Model/"

# defining calibration file for pipeline
calibration_file = "Example_calibration_file.json"

# defining training and testing config files
training_data_file = "Training_data.json"
testing_data_file = "Testing_data.json"

# defining random search parameters
n_epochs = 300
n_configs = 30

# randomly generating model params
static_params = {
    "n_inputs" : 400,
    "n_outputs" : 7,
    "n_steps" : 20,
    "starting_step" : 15,
}
variable_params = {
    "n_state_neurons" : 50,
    "n_hidden1" : 200,
    "n_hidden2" : 50,
    "learning_rate" : 0.001,
    "keep_prob" : 0.5
}
random_model_params = generate_random_params(variable_params, n_configs, variation=0.5, 
                                            static_params=static_params)

# creating batch generators for training data and testing data
train_batch_gen = ModelBatchGenerator(movement_info_f=training_data_file, batch_size="all", 
                                        n_inputs=static_params["n_inputs"], n_steps=static_params["n_steps"], 
                                        starting_step=static_params["starting_step"])
test_batch_gen = ModelBatchGenerator(movement_info_f=testing_data_file, batch_size="all", 
                                        n_inputs=static_params["n_inputs"], n_steps=static_params["n_steps"], 
                                        starting_step=static_params["starting_step"])

# setting a calibration pipeline for the batch generators
cal_pipeline = get_calibration_Pipeline(calibration_file)
train_batch_gen.set_batch_pipeline(cal_pipeline)
test_batch_gen.set_batch_pipeline(cal_pipeline)

# loading training and testing data
X_train, y_train, seq_len_train = train_batch_gen.next_batch()
X_test, y_test, seq_len_test = test_batch_gen.next_batch()

# defining logging parameters
config_i = 1
config_performances = []

for model_param in random_model_params:

    print("Training with configuration #", config_i)
    config_i += 1

    # creating the model with the new params and restoring
    try : 
        generate_blank_model(model_dir, m_params=model_param)
        restored_sess, saver = restore_tf_session(model_dir)
    except : 
        print("Configuration #", config_i, " failed to build.")    
        continue

    max_accuracy = 0
    epoch_at_max = 0

    with restored_sess as session:

        # fetching place holders
        X = tf.get_collection('X')[0]
        y = tf.get_collection('y')[0]
        seq_length = tf.get_collection('seq_length')[0]
        training_model = tf.get_collection('training_model')[0]
        
        # fetching training ops
        target_logits = tf.get_collection('target_logits')[0]
        training_op = tf.get_collection('training_op')[0]

        # fetching logging ops
        accuracy = tf.get_collection('accuracy')[0]
        test_acc_summary = tf.get_collection('test_acc_summary')[0]
        train_acc_summary = tf.get_collection('train_acc_summary')[0]

        # training the model
        for epoch in range(n_epochs):
                   
            session.run(training_op, feed_dict={X:X_train, y:y_train,
                                     training_model:True, seq_length:seq_len_train})

            # keeping track of peak accuracy
            if(epoch % 10 == 0):
                
                acc_val = accuracy.eval(feed_dict={X: X_test, y: y_test, training_model:False, seq_length:seq_len_test})
                if acc_val > max_accuracy : 
                    max_accuracy = acc_val
                    epoch_at_max = epoch
                
                print("epoch : ", epoch, " / ", n_epochs)

        # saving the model performance
        model_param["max_accuracy"] = max_accuracy
        model_param["epoch_at_max"] = epoch_at_max
        config_performances.append(model_param)

log_config_performances(config_performances)