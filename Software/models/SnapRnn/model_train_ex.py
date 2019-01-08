import numpy as np
import tensorflow as tf

import os.path
from datetime import datetime

# importing model utilities
from snaprnn.train import ModelBatchGenerator
from snaprnn.evaluate import restore_tf_session 
from snaprnn.model import generate_blank_model

# importing data processing/piepline utilities
from Calibration_Pipeline.Calibration_Pipeline import get_calibration_Pipeline

# defining model directory
model_dir = "Model/"

# defining log names and directory
now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
logdir = "tf_logs/run-{}/".format(now)

# defining calibration file for pipeline
calibration_file = "Example_calibration_file.json"

# defining training and testing config files
training_data_file = "Training_data.json"
testing_data_file = "Testing_data.json"

# defining training parameters
n_epochs = 300
training_batch_size = 50

# if no previous graph definitions, start from scratch
checkpoint_path = tf.train.latest_checkpoint(model_dir)
if checkpoint_path is None : 
    checkpoint_path = generate_blank_model(model_dir)

# restoring from checkpoint file
restored_sess, saver = restore_tf_session(model_dir)

# creating a logger for training progress
file_writer = tf.summary.FileWriter(logdir, tf.get_default_graph())

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

    # pulling model input dimensions
    n_inputs = int(X.shape[2])
    n_steps = int(X.shape[1])
    starting_step = n_steps - int(target_logits.shape[1])
    
    # creating batch generators for training data and testing data
    train_batch_gen = ModelBatchGenerator(movement_info_f=training_data_file, batch_size="all", 
                                           n_inputs=n_inputs, n_steps=n_steps, starting_step=starting_step)
    test_batch_gen = ModelBatchGenerator(movement_info_f=testing_data_file, batch_size="all", 
                                           n_inputs=n_inputs, n_steps=n_steps, starting_step=starting_step)
    
    # setting a calibration pipeline for the batch generators
    cal_pipeline = get_calibration_Pipeline(calibration_file)
    train_batch_gen.set_batch_pipeline(cal_pipeline)
    test_batch_gen.set_batch_pipeline(cal_pipeline)

    # loading training and testing data
    X_train, y_train, seq_len_train = train_batch_gen.next_batch()
    X_test, y_test, seq_len_test = test_batch_gen.next_batch()
    
    # keeping track of best test accuracy score
    checkpoint_accuracy = 0

    # training the model
    for epoch in range(n_epochs):
                
        session.run(training_op, feed_dict={X:X_train, y:y_train,
                                    training_model:True, seq_length:seq_len_train})

        # logging the costs (training and testing) and accuracy (testing)
        if(epoch % 10 == 0):
            
            # accuracy on training batch
            train_acc_string = train_acc_summary.eval(feed_dict={X: X_train, y: y_train, 
                                            training_model:False, seq_length:seq_len_train})

            # accuracy on testing batch
            test_acc_string = test_acc_summary.eval(feed_dict={X: X_test, y: y_test, 
                                            training_model:False, seq_length:seq_len_test})
            
            # getting the test accuracy value
            acc_val = accuracy.eval(feed_dict={X: X_test, y: y_test, 
                                training_model:False, seq_length:seq_len_test})

            # writting to tensor board
            file_writer.add_summary(train_acc_string, epoch)
            file_writer.add_summary(test_acc_string, epoch)

            # updating the model checkpoint when test accuracy goes up
            if acc_val > checkpoint_accuracy :
                checkpoint_accuracy = acc_val
                saver.save(session, checkpoint_path, write_meta_graph=False)

            # printing progress update
            print("epoch : ", epoch, " / ", n_epochs)
            
    file_writer.close()
    