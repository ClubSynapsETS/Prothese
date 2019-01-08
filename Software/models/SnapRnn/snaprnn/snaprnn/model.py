import numpy as np
import tensorflow as tf

# importing RNN utilities
from . import evaluate

# importing os navigation utilities
import os.path

# importing RNN utilities
from tensorflow.contrib.layers import fully_connected, dropout, variance_scaling_initializer


# defining default model parameters for the model generation 
model_params = {
    "n_inputs" : 400,
    "n_outputs" : 7,
    "n_state_neurons" : 50,
    "n_steps" : 20,
    "starting_step" : 15,
    "n_hidden1" : 200,
    "n_hidden2" : 50,
    "keep_prob" : 0.5,
    "learning_rate" : 0.001
}


# generates RNN model graph with newly initialized values
# inputs : 
#   m_params : model parameters specifying graph shape and characteristics
#   model_dir : directory where model information shoukd be stored  
#   checkpoint_out : the checkpoint file name for the genarated graph (default if not specified)
def generate_blank_model(model_dir, m_params=None, checkpoint_out=None):

    # defining name of ouput checkpoint file
    checkpoint_path = ""
    if checkpoint_out is None:
        # trying to get the latest cp file
        checkpoint_path = tf.train.latest_checkpoint(model_dir)
        # defining a new cp file
        if checkpoint_path is None:
            checkpoint_path = os.path.join(model_dir, "cortex_rnn")
            
    # using the cp file defined by the user
    else : checkpoint_path = checkpoint_out

    # defining the model parameters
    if m_params is None : m_params = model_params

    # resetting the global default graph
    tf.reset_default_graph()

    # placeholders for input data
    X = tf.placeholder(tf.float32, [None, m_params["n_steps"], m_params["n_inputs"]], name='X')
    seq_length = tf.placeholder(tf.int32, [None], name='seq_length')
    y = tf.placeholder(tf.int32, [None], name='y')
    training_model = tf.placeholder(tf.bool, shape=(), name='training_model')

    # defining the RNN with GRU cells
    with tf.name_scope("RNN"):
        with tf.variable_scope("rnn", initializer=variance_scaling_initializer()):
            gru_cell = tf.contrib.rnn.GRUCell(num_units=m_params["n_state_neurons"])
            rnn_outputs, states = tf.nn.dynamic_rnn(gru_cell, X, dtype=tf.float32, sequence_length=seq_length) 

    # defining fully connected layers after GRU cell
    with tf.name_scope("Output_FC"):
        with tf.contrib.framework.arg_scope([fully_connected]):
            stacked_rnn_outputs = tf.reshape(rnn_outputs, [-1, m_params["n_state_neurons"]])
            input_drop = dropout(stacked_rnn_outputs, m_params["keep_prob"], is_training=training_model)
            hidden1 = fully_connected(input_drop, m_params["n_hidden1"], scope="hidden1_out")
            hidden1_drop = dropout(hidden1, m_params["keep_prob"], is_training=training_model)
            hidden2 = fully_connected(hidden1_drop, m_params["n_hidden2"], scope="hidden2_out")
            hidden2_drop = dropout(hidden2, m_params["keep_prob"], is_training=training_model)
            stacked_outputs = fully_connected(hidden2_drop, m_params["n_outputs"], scope="stacked_out", activation_fn=None)
            stacked_predictions = tf.argmax(stacked_outputs, 1)
            # logits and prediction outputs
            logits_op = tf.reshape(stacked_outputs, [-1, m_params["n_steps"], m_params["n_outputs"]], name="logits_op")
            labels_op = tf.reshape(stacked_predictions, [-1, m_params["n_steps"]], name="labels_op")

    with tf.name_scope("Train"):
        # back prop done for outputs "Y(t)" [starting_step : n_steps]
        target_logits = logits_op[ : , m_params["starting_step"] : m_params["n_steps"] , : ]
        logits_reshaped = tf.manip.reshape(target_logits, [tf.shape(target_logits)[0]*tf.shape(target_logits)[1], tf.shape(target_logits)[2]])
        xentropy = tf.nn.sparse_softmax_cross_entropy_with_logits(labels=y, logits=logits_reshaped, name="xentropy")
        loss = tf.reduce_mean(xentropy, name="loss")
        optimizer = tf.train.AdamOptimizer(learning_rate=m_params["learning_rate"])
        training_op = optimizer.minimize(loss, name="training_op")

    # defining nodes for performance evaluation
    with tf.name_scope("Eval"):
        correct = tf.nn.in_top_k(logits_reshaped, y, 1)
        accuracy = tf.reduce_mean(tf.cast(correct, tf.float32))

    # making data available to tensorboard
    with tf.name_scope("Logging"):
        test_acc_summary = tf.summary.scalar('Test accuracy', accuracy)
        train_acc_summary = tf.summary.scalar('Train accuracy', accuracy)

    # making input nodes fetchable
    tf.add_to_collection('X', X)
    tf.add_to_collection('y', y)
    tf.add_to_collection('seq_length', seq_length)
    tf.add_to_collection('training_model', training_model)
    
    # making prediction nodes fetchable
    tf.add_to_collection('class_ids', labels_op)
    tf.add_to_collection('probabilities', tf.nn.softmax(logits_op))
    tf.add_to_collection('logits_op', logits_op)

    # making training nodes fetchable
    tf.add_to_collection('target_logits', target_logits)
    tf.add_to_collection('training_op', training_op)

    # making logging nodes fetchable
    tf.add_to_collection('accuracy', accuracy)
    tf.add_to_collection('test_acc_summary', test_acc_summary)
    tf.add_to_collection('train_acc_summary', train_acc_summary)

    # initializer to initialize variables at zero
    init = tf.global_variables_initializer()
    saver_op = tf.train.Saver()

    # generating the graph
    with tf.Session() as sess: 
        init.run()
        save_path = saver_op.save(sess, checkpoint_path)

    return checkpoint_path