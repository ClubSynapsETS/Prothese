import numpy as np
import tensorflow as tf

# importing model utilities
from snaprnn.train import ModelBatchGenerator, log_rnn_confusion
from snaprnn.evaluate import restore_tf_session

# importing data processing/piepline utilities
from Calibration_Pipeline.Calibration_Pipeline import get_calibration_Pipeline

# defining model information
model_dir = "Model/"

# defining calibration file for pipeline
calibration_file = "Example_calibration_file.json"

# defining training info file
training_data_file = "Testing_data.json"

# restoring the model from the latest check point
restored_sess, _ = restore_tf_session(model_dir)

# using the restored model session
with restored_sess as session:
    
    # fetching training opps and place holders
    X = tf.get_collection('X')[0]
    seq_length = tf.get_collection('seq_length')[0]
    training_model = tf.get_collection('training_model')[0]
    predictions_op = tf.get_collection('class_ids')[0]

    # pulling model input dimensions
    n_inputs = int(X.shape[2])
    n_steps = int(X.shape[1])

    # defining the step at which to start evaluating the outputs
    starting_step = 19

    # creating batch generator for training data
    train_batch_gen = ModelBatchGenerator(movement_info_f=training_data_file, batch_size="all", 
                                           n_inputs=n_inputs, n_steps=n_steps, starting_step=starting_step)

    # setting a calibration pipeline for the batch generators
    cal_pipeline = get_calibration_Pipeline(calibration_file)
    train_batch_gen.set_batch_pipeline(cal_pipeline)

    # loading training and testing
    X_train, y_train, seq_len_train = train_batch_gen.next_batch()
     
    # getting the predictions for the batch of training data       
    predictions = session.run(predictions_op, feed_dict={X:X_train, training_model:False, 
                                                 seq_length:seq_len_train})

    log_rnn_confusion(predictions, y_train, starting_step=starting_step, mv_info_f=training_data_file)